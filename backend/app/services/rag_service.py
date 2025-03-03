from typing import List, Dict, AsyncGenerator, Optional, Any, Tuple, Union
from app.models.schemas import Document, QueryRequest, LLMConfig
from app.services.vector_store import EnhancedVectorStoreService
from app.services.document_processor import EnhancedDocumentProcessor
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.retrievers import BaseRetriever
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.chains.query_constructor.base import AttributeInfo
from langchain.retrievers import SelfQueryRetriever
import asyncio
import logging
import json
import re
from app.config import settings
import time

logger = logging.getLogger(__name__)

class EnhancedRAGService:
    def __init__(self):
        self.vector_store_service = EnhancedVectorStoreService()
        self.document_processor = EnhancedDocumentProcessor()
        self.current_provider = settings.DEFAULT_MODEL_PROVIDER
        self.ollama_model = None
        self.gemini_model = None
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize language models with enhanced parameters"""
        try:
            # Initialize Ollama for Gemma2
            self.ollama_model = ChatOllama(
                model=settings.OLLAMA_MODEL,
                temperature=settings.MODEL_TEMPERATURE,
                top_p=settings.MODEL_TOP_P,
                top_k=settings.MODEL_TOP_K,
                num_predict=settings.MODEL_MAX_TOKENS,
                base_url=settings.OLLAMA_BASE_URL,
                streaming=True,
                # Additional parameters for better performance
                repeat_penalty=1.1,
                num_ctx=4096  # Larger context window
            )
            logger.info(f"Ollama model initialized with: {settings.OLLAMA_MODEL}")
        except Exception as e:
            logger.error(f"Error initializing Ollama model: {str(e)}", exc_info=True)

        try:
            # Initialize Gemini if API key is available
            if settings.GOOGLE_API_KEY:
                self.gemini_model = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    temperature=settings.MODEL_TEMPERATURE,
                    top_p=settings.MODEL_TOP_P,
                    top_k=settings.MODEL_TOP_K,
                    max_output_tokens=settings.MODEL_MAX_TOKENS,
                    google_api_key=settings.GOOGLE_API_KEY,
                    streaming=True
                )
                logger.info(f"Gemini model initialized with: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {str(e)}", exc_info=True)

    async def process_document(self, document: Document, file_path: str) -> bool:
        """Process a document and add it to vector store"""
        try:
            logger.info(f"Processing document: {document.filename}")
            processed_chunks = await self.document_processor.process_document(document, file_path)
            
            if not processed_chunks:
                logger.warning(f"No chunks extracted from document: {document.filename}")
                return False
                
            texts = [chunk["text"] for chunk in processed_chunks]
            metadatas = [chunk["metadata"] for chunk in processed_chunks]
            
            # Add to vector store
            success = await self.vector_store_service.add_documents(texts, metadatas)
            
            return success
        except Exception as e:
            logger.error(f"Error in process_document: {str(e)}", exc_info=True)
            raise

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
    
    def _create_self_query_retriever(self, query: str) -> Optional[BaseRetriever]:
        """Create a self-query retriever for metadata filtering"""
        try:
            # Define the metadata fields that can be queried
            metadata_field_info = [
                AttributeInfo(
                    name="filename",
                    description="The name of the file",
                    type="string",
                ),
                AttributeInfo(
                    name="file_type",
                    description="The type of the file (pdf, txt, pptx, ipynb)",
                    type="string",
                ),
                AttributeInfo(
                    name="document_id",
                    description="The unique ID of the document",
                    type="string",
                ),
                AttributeInfo(
                    name="processed_date",
                    description="The date when the document was processed",
                    type="string",
                ),
            ]
            
            # Get the current model for the query constructor
            model = self.get_current_model()
            
            # Create the self query retriever
            retriever = SelfQueryRetriever.from_llm(
                llm=model,
                vectorstore=self.vector_store_service.vector_store,
                document_contents="Educational materials including documents, PDFs, PowerPoints, and code",
                metadata_field_info=metadata_field_info,
                verbose=True
            )
            
            return retriever
        except Exception as e:
            logger.error(f"Error creating self-query retriever: {str(e)}")
            return None
    
    def _create_compression_retriever(self, query: str) -> Optional[BaseRetriever]:
        """Create a compression retriever for more focused context retrieval"""
        try:
            # Get base retriever from vector store
            base_retriever = self.vector_store_service.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": settings.DEFAULT_CONTEXT_WINDOW}
            )
            
            # Get the current model
            model = self.get_current_model()
            
            # Create the extractor
            extractor = LLMChainExtractor.from_llm(model)
            
            # Create the compression retriever
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=extractor,
                base_retriever=base_retriever
            )
            
            return compression_retriever
        except Exception as e:
            logger.error(f"Error creating compression retriever: {str(e)}")
            return None
            
    async def _extract_query_metadata(self, query: str) -> Dict[str, Any]:
        """Extract any file filters from the query"""
        try:
            # Only attempt to extract metadata if query seems to contain filters
            filter_keywords = ["file", "document", "pdf", "presentation", "notebook", "code"]
            if not any(keyword in query.lower() for keyword in filter_keywords):
                return {}
                
            # Get the current model
            model = self.get_current_model()
            
            # Create a special prompt for metadata extraction
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful assistant that extracts file filtering information from queries.
                Extract any filters for filenames or file types that the user might be looking for.
                Return a JSON with the following format:
                {
                    "filename": "filename to filter on (or null if not specified)",
                    "file_type": "file type to filter on (or null if not specified)"
                }
                Only include filters that are explicitly mentioned."""),
                ("human", "{query}")
            ])
            
            # Create chain
            chain = prompt | model | StrOutputParser()
            
            # Execute chain
            result = await chain.ainvoke({"query": query})
            
            # Extract JSON
            pattern = r'\{.*\}'
            match = re.search(pattern, result, re.DOTALL)
            
            if match:
                extracted_json = match.group(0)
                try:
                    metadata = json.loads(extracted_json)
                    # Clean up metadata
                    return {k: v for k, v in metadata.items() if v and v.lower() != "null"}
                except json.JSONDecodeError:
                    return {}
            
            return {}
        except Exception as e:
            logger.error(f"Error extracting metadata from query: {str(e)}")
            return {}
    
    async def _perform_hybrid_search(self, query: str, k: int = 5) -> List[Dict]:
        """Perform a hybrid search combining semantic search with metadata filtering"""
        try:
            # Extract metadata filters from query
            metadata_filters = await self._extract_query_metadata(query)
            
            # Get semantic search results
            start_time = time.time()
            search_results = await self.vector_store_service.similarity_search(
                query=query,
                k=k,
                filter_dict=metadata_filters if metadata_filters else None
            )
            logger.info(f"Semantic search completed in {time.time() - start_time:.2f}s")
            
            return search_results
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            raise
            
    def _re_rank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Re-rank results based on relevance to query"""
        if not results:
            return []
            
        # Simple re-ranking based on keyword matching and position
        query_terms = set(query.lower().split())
        
        for result in results:
            # Count keyword matches
            content = result["content"].lower()
            keyword_matches = sum(1 for term in query_terms if term in content)
            
            # Check for query terms in the first paragraph
            first_para = content.split("\n\n")[0] if "\n\n" in content else content
            first_para_matches = sum(1 for term in query_terms if term in first_para)
            
            # Calculate combined score
            # Original relevance score (0-1) + keyword boost + first paragraph boost
            adjusted_score = (
                result["score"] + 
                (keyword_matches * 0.05) + 
                (first_para_matches * 0.1)
            )
            
            # Cap at 1.0
            result["score"] = min(adjusted_score, 1.0)
            
        # Sort by adjusted score
        return sorted(results, key=lambda x: x["score"], reverse=True)

    async def generate_response(self, query: QueryRequest) -> AsyncGenerator[str, None]:
        """Generate streaming response for the query using advanced RAG techniques"""
        try:
            provider = query.model_provider or self.current_provider
            logger.info(f"Starting generate_response with provider: {provider}")
            
            # Apply custom model parameters if provided
            if query.llm_config:  # Changed from model_config to llm_config
                logger.info(f"Custom LLM config applied: {query.llm_config}")
                # Would apply custom parameters here
                
            # Perform hybrid search
            search_results = await self._perform_hybrid_search(
                query.question,
                k=query.context_window or settings.DEFAULT_CONTEXT_WINDOW
            )
            
            # Apply re-ranking
            search_results = self._re_rank_results(search_results, query.question)
            
            logger.info(f"Found {len(search_results)} relevant documents")
            
            if not search_results:
                yield self.format_sse({
                    "type": "error",
                    "content": "No relevant documents found in the knowledge base."
                })
                return

            # Format context with relevance scores
            context_parts = []
            for i, result in enumerate(search_results, 1):
                content = result["content"]
                score = result.get("score", "N/A")
                metadata = result.get("metadata", {})
                filename = metadata.get("filename", "Unknown")
                logger.debug(f"Document {i} '{filename}' relevance score: {score}")
                
                # Add source information to each chunk
                context_parts.append(f"[Source: {filename} | Relevance: {score:.2f}]\n{content}")
            
            context = "\n\n---\n\n".join(context_parts)
            
            try:
                model = self.get_current_model()
                logger.info(f"Model initialized: {type(model)}")

                # Create an enhanced system prompt for Gemma2:9b
                system_prompt = """You are a helpful AI Study Buddy assistant. Your goal is to answer questions about the user's documents. 
                
                IMPORTANT INSTRUCTIONS:
                1. Base your answer STRICTLY on the provided context. Do not use any other knowledge.
                2. If the context doesn't contain relevant information, state clearly that you cannot find the answer in the provided documents.
                3. Cite sources when appropriate by referring to the document names mentioned in the context.
                4. Format your responses for clarity using markdown when helpful.
                5. Be concise and focused in your responses.
                6. When answering technical questions, be precise and accurate.
                
                Remember, your goal is to help the user understand their own documents better."""
                
                # Create a standardized human prompt
                human_prompt = """Here is the context from your documents:

                {context}
                
                Question: {question}
                
                Please provide a clear answer based only on the information in the context above."""
                
                # Create the prompt template
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", human_prompt)
                ])

                # Create chain with context and question
                chain = (
                    {
                        "context": lambda x: context, 
                        "question": lambda x: x
                    }
                    | prompt
                    | model
                    | StrOutputParser()
                )

                logger.debug(f"Query being sent to model: {query.question}")

                # Stream the results with sentence-level chunking
                current_sentence = ""
                buffer = ""
                
                async for chunk in chain.astream(query.question):
                    buffer += chunk
                    
                    # Process complete sentences
                    sentences = re.split(r'(?<=[.!?])\s+', buffer)
                    
                    if len(sentences) > 1:  # We have at least one complete sentence
                        complete_sentences = sentences[:-1]  # All but the last (possibly incomplete) sentence
                        buffer = sentences[-1]  # Keep the last incomplete sentence in buffer
                        
                        for sentence in complete_sentences:
                            if sentence.strip():
                                yield self.format_sse({
                                    "type": "response",
                                    "content": sentence.strip() + " ",
                                    "provider": provider
                                })
                                await asyncio.sleep(0.05)  # Small delay for smoother streaming
                
                # Send any remaining text in the buffer
                if buffer.strip():
                    yield self.format_sse({
                        "type": "response",
                        "content": buffer.strip(),
                        "provider": provider
                    })

                # Signal completion
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