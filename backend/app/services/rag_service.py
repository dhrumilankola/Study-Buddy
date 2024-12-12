from typing import List, Dict, AsyncGenerator, Optional
from app.models.schemas import Document, Query, ModelConfig
from app.services.vector_store import VectorStoreService
from app.services.document_processor import DocumentProcessor
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleVectorStore
from langchain.embeddings.base import Embeddings
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import asyncio
import logging
import json
from app.config import settings

logger = logging.getLogger(__name__)

class ServerSideEmbedding(Embeddings):
    """Placeholder embedding model for Google's server-side embeddings"""
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async embed documents - not used for server-side embeddings"""
        return [[0.0] for _ in texts]
        
    async def aembed_query(self, text: str) -> List[float]:
        """Async embed query - not used for server-side embeddings"""
        return [0.0]
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Sync embed documents - not used for server-side embeddings"""
        return [[0.0] for _ in texts]
        
    def embed_query(self, text: str) -> List[float]:
        """Sync embed query - not used for server-side embeddings"""
        return [0.0]


class RAGService:
    def __init__(self):
        self.vector_store_service = VectorStoreService()
        self.document_processor = DocumentProcessor()
        self.current_provider = settings.DEFAULT_MODEL_PROVIDER
        self.ollama_model = None
        self.gemini_model = None
        self.google_store = None
        self._initialize_models()
        self._initialize_google_store()

    def _initialize_google_store(self):
        """Initialize Google Vector Store if credentials are available"""
        try:
            if settings.GOOGLE_API_KEY and settings.GOOGLE_PROJECT_ID:
                self.google_store = GoogleVectorStore(
                    project_id=settings.GOOGLE_PROJECT_ID,
                    credentials=settings.GOOGLE_API_KEY,
                    embedding=ServerSideEmbedding()
                )
                logger.info("Google Vector Store initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Google Vector Store: {str(e)}", exc_info=True)

    def _initialize_models(self):
        """Initialize both Ollama and Gemini models"""
        try:
            # Initialize Ollama
            self.ollama_model = ChatOllama(
                model="gemma",
                temperature=settings.MODEL_TEMPERATURE,
                base_url=settings.OLLAMA_BASE_URL,
                streaming=True
            )
            logger.info("Ollama model initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Ollama model: {str(e)}", exc_info=True)

        try:
            # Initialize Gemini if API key is available
            if settings.GOOGLE_API_KEY:
                self.gemini_model = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    temperature=settings.MODEL_TEMPERATURE,
                    google_api_key=settings.GOOGLE_API_KEY,
                    streaming=True
                )
                logger.info("Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {str(e)}", exc_info=True)

    async def process_document(self, document: Document, file_path: str) -> bool:
        """Process a document and add it to vector stores"""
        try:
            logger.info(f"Processing document: {document.filename}")
            processed_chunks = await self.document_processor.process_document(document, file_path)
            
            texts = [chunk["text"] for chunk in processed_chunks]
            metadatas = [chunk["metadata"] for chunk in processed_chunks]
            
            # Add to ChromaDB
            await self.vector_store_service.add_documents(texts, metadatas)
            
            # Add to Google Vector Store if available
            if self.google_store and self.current_provider == "gemini":
                try:
                    for text, metadata in zip(texts, metadatas):
                        self.google_store.add_texts(
                            texts=[text],
                            metadatas=[metadata]
                        )
                    logger.info(f"Added document to Google Vector Store: {document.filename}")
                except Exception as e:
                    logger.error(f"Error adding to Google Vector Store: {str(e)}", exc_info=True)
            
            return True
        except Exception as e:
            logger.error(f"Error in process_document: {str(e)}", exc_info=True)
            raise

    def switch_provider(self, provider: str) -> bool:
        """Switch between model providers"""
        if provider not in ["ollama", "gemini"]:
            logger.warning(f"Invalid provider requested: {provider}")
            return False
        
        if provider == "gemini" and not settings.GOOGLE_API_KEY:
            logger.warning("Attempted to switch to Gemini but no API key available")
            return False
            
        self.current_provider = provider
        logger.info(f"Switched to provider: {provider}")
        return True

    def get_current_model(self):
        """Get the currently active model based on provider"""
        if self.current_provider == "gemini":
            if not self.gemini_model:
                logger.error("Gemini model not initialized but requested")
                raise ValueError("Gemini model not initialized")
            return self.gemini_model
        else:
            if not self.ollama_model:
                logger.error("Ollama model not initialized but requested")
                raise ValueError("Ollama model not initialized")
            return self.ollama_model

    def format_sse(self, data: dict) -> str:
        """Format the data dictionary as a Server-Sent Events message"""
        return f"data: {json.dumps(data)}\n\n"

    async def generate_response(self, query: Query) -> AsyncGenerator[str, None]:
        """Generate streaming response for the query"""
        try:
            provider = query.model_provider or self.current_provider
            logger.info(f"Starting generate_response with provider: {provider}")
            
            # Get relevant documents from appropriate store
            if provider == "gemini" and self.google_store:
                try:
                    # Use Google's semantic search
                    raw_results = self.google_store.similarity_search(
                        query.question,
                        k=query.context_window or 3
                    )
                    search_results = [
                        {
                            "content": doc.page_content,
                            "metadata": doc.metadata,
                            "score": getattr(doc, "score", None)
                        }
                        for doc in raw_results
                    ]
                    logger.info("Retrieved results from Google Vector Store")
                except Exception as e:
                    logger.error(f"Error with Google Vector Store: {str(e)}")
                    # Fallback to ChromaDB
                    search_results = await self.vector_store_service.similarity_search(
                        query.question,
                        k=query.context_window or 3
                    )
                    logger.info("Falling back to ChromaDB results")
            else:
                # Use ChromaDB
                search_results = await self.vector_store_service.similarity_search(
                    query.question,
                    k=query.context_window or 3
                )
                logger.info("Retrieved results from ChromaDB")
            
            logger.info(f"Found {len(search_results)} relevant documents")
            
            if not search_results:
                yield self.format_sse({
                    "type": "error",
                    "content": "No relevant documents found in the knowledge base."
                })
                return

            # Format context with relevance scores if available
            context_parts = []
            for i, result in enumerate(search_results, 1):
                content = result["content"]
                score = result.get("score", "N/A")
                logger.debug(f"Document {i} relevance score: {score}")
                context_parts.append(f"[Relevance: {score}]\n{content}")
            
            context = "\n\n---\n\n".join(context_parts)
            logger.debug(f"Complete context being sent to model: {context[:500]}...")
            
            try:
                model = self.get_current_model()
                logger.info(f"Model initialized: {type(model)}")

                # Create provider-specific prompt template
                if provider == "gemini":
                    prompt_template = """I will provide you with some context from documents and a question. 
                    Please answer the question based ONLY on the provided context. If the context doesn't 
                    contain relevant information, say so.

                    Context from documents:
                    {context}

                    Question: {question}

                    Based strictly on the context provided above, here is my answer:"""
                    
                    prompt = ChatPromptTemplate.from_messages([
                        ("human", prompt_template)
                    ])
                else:
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", """You are a helpful AI assistant. Answer questions based STRICTLY on 
                        the provided context. If the context doesn't contain enough information, say so."""),
                        ("human", "Context:\n{context}\n\nQuestion: {question}")
                    ])

                # Create chain with explicit context mapping
                chain = (
                    {
                        "context": lambda x: context,
                        "question": RunnablePassthrough()
                    }
                    | prompt
                    | model
                    | StrOutputParser()
                )

                logger.debug(f"Query being sent to model: {query.question}")

                buffer = ""
                async for chunk in chain.astream(query.question):
                    buffer += chunk
                    if any(char in chunk for char in ['.', '!', '?']) and len(buffer.strip()) > 30:
                        formatted_response = buffer.strip().replace('\n\n', ' ').replace('  ', ' ')
                        yield self.format_sse({
                            "type": "response",
                            "content": formatted_response,
                            "provider": provider
                        })
                        buffer = ""
                        await asyncio.sleep(0.1)
                
                if buffer.strip():
                    formatted_response = buffer.strip().replace('\n\n', ' ').replace('  ', ' ')
                    yield self.format_sse({
                        "type": "response",
                        "content": formatted_response,
                        "provider": provider
                    })

                yield self.format_sse({
                    "type": "done",
                    "content": "",
                    "provider": provider
                })

            except Exception as e:
                logger.error(f"Error in chain execution: {str(e)}", exc_info=True)
                yield self.format_sse({
                    "type": "error",
                    "content": f"Error generating response: {str(e)}",
                    "provider": provider
                })
                
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}", exc_info=True)
            yield self.format_sse({
                "type": "error",
                "content": f"Error in RAG pipeline: {str(e)}"
            })