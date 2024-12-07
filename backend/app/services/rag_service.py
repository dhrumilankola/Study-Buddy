from typing import List, Dict, AsyncGenerator
from app.models.schemas import Document, Query
from app.services.vector_store import VectorStoreService
from app.services.document_processor import DocumentProcessor
from langchain_community.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import asyncio
import logging
import json

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.vector_store_service = VectorStoreService()
        self.document_processor = DocumentProcessor()
        self.ollama_model = None
        self._initialize_llm()

    def _initialize_llm(self):
        try:
            self.ollama_model = ChatOllama(
                model="gemma",
                temperature=0.7,
                base_url="http://localhost:11434",
                streaming=True
            )
        except Exception as e:
            logger.error(f"Error initializing Gemma model: {str(e)}")
            raise

    async def process_document(self, document: Document, file_path: str) -> bool:
        """Process a document and add it to the vector store"""
        try:
            # Process document
            processed_chunks = await self.document_processor.process_document(document, file_path)
            
            # Extract texts and metadatas
            texts = [chunk["text"] for chunk in processed_chunks]
            metadatas = [chunk["metadata"] for chunk in processed_chunks]
            
            # Add to vector store
            await self.vector_store_service.add_documents(texts, metadatas)
            return True
            
        except Exception as e:
            logger.error(f"Error in process_document: {str(e)}")
            raise

    def format_sse(self, data: dict) -> str:
        """Format the data dictionary as a Server-Sent Events message"""
        return f"data: {json.dumps(data)}\n\n"

    async def generate_response(self, query: Query) -> AsyncGenerator[str, None]:
        try:
            # Get relevant documents
            search_results = await self.vector_store_service.similarity_search(
                query.question,
                k=query.context_window
            )
            
            if not search_results:
                yield self.format_sse({
                    "type": "error",
                    "content": "No relevant documents found in the knowledge base."
                })
                return

            # Prepare context
            context = "\n\n".join([result["content"] for result in search_results])
            
            prompt = ChatPromptTemplate.from_template("""
            Based on the following context, provide a clear and helpful answer to the question.
            If you cannot find relevant information in the context, clearly state that you don't have enough information.

            Context:
            {context}

            Question:
            {question}

            Answer:
            """)
            
            try:
                # Create chain
                chain = (
                    {"context": lambda x: context, "question": RunnablePassthrough()}
                    | prompt
                    | self.ollama_model
                    | StrOutputParser()
                )
                
                # Get response
                response = await chain.ainvoke(query.question)
                
                # Process response sentence by sentence
                buffer = ""
                for char in response:
                    buffer += char
                    if char in ['.', '!', '?'] and len(buffer.strip()) > 0:
                        yield self.format_sse({
                            "type": "response",
                            "content": buffer.strip()
                        })
                        buffer = ""
                        await asyncio.sleep(0.1)
                
                # Send any remaining content
                if buffer.strip():
                    yield self.format_sse({
                        "type": "response",
                        "content": buffer.strip()
                    })
                
                # Send completion message
                yield self.format_sse({
                    "type": "done",
                    "content": ""
                })
                
            except Exception as e:
                yield self.format_sse({
                    "type": "error",
                    "content": f"Error generating response: {str(e)}"
                })
                
        except Exception as e:
            yield self.format_sse({
                "type": "error",
                "content": f"Error in RAG pipeline: {str(e)}"
            })