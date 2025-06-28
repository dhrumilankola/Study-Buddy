from typing import List, Dict, AsyncGenerator, Optional, Any, Tuple, Union
from app.models.schemas import Document as SchemaDocument, QueryRequest, LLMConfig
from app.database.models import Document as DBDocument
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
from langchain_core.callbacks import BaseCallbackHandler
import google.generativeai as genai
import asyncio
import logging
import json
import re
from app.config import settings
from app.utils.rate_limiter import async_rate_limited, gemini_limiter
import time

logger = logging.getLogger(__name__)

class EnhancedTokenDebugHandler(BaseCallbackHandler):
    """Enhanced callback handler for tracking token usage and rate limits."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens_per_minute = 0
        self.last_reset = time.time()
        # Reduced limits for free tier - Gemini free tier has much lower limits
        self.max_tokens_per_minute = 32000  # Conservative limit for free tier
        self.max_requests_per_minute = 15   # Conservative request limit
        self.request_count = 0

        # Initialize Google AI SDK properly
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)

    def _check_rate_limit(self):
        """Reset token counter if a minute has passed"""
        current_time = time.time()
        if current_time - self.last_reset > 60:
            self.total_tokens_per_minute = 0
            self.request_count = 0
            self.last_reset = current_time

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Log token count when LLM starts processing."""
        try:
            self._check_rate_limit()
            self.request_count += 1

            # Check request rate limit
            if self.request_count > self.max_requests_per_minute * 0.8:
                logger.warning(f"Approaching request rate limit: {self.request_count}/{self.max_requests_per_minute}")

            if isinstance(prompts[0], str) and settings.GOOGLE_API_KEY:
                try:
                    model = genai.GenerativeModel(settings.GEMINI_MODEL)
                    token_count = model.count_tokens(prompts[0]).total_tokens
                    self.input_tokens = token_count
                    self.total_tokens_per_minute += token_count
                    logger.info(f"Input tokens: {token_count} (Total this minute: {self.total_tokens_per_minute})")

                    # Check if approaching limit
                    if self.total_tokens_per_minute > self.max_tokens_per_minute * 0.8:
                        logger.warning(f"Approaching token rate limit: {self.total_tokens_per_minute}/{self.max_tokens_per_minute}")
                except Exception as token_error:
                    logger.debug(f"Could not count input tokens: {str(token_error)}")
                    # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
                    estimated_tokens = len(prompts[0]) // 4
                    self.input_tokens = estimated_tokens
                    self.total_tokens_per_minute += estimated_tokens
                    logger.info(f"Estimated input tokens: {estimated_tokens}")
        except Exception as e:
            logger.error(f"Error in token tracking: {str(e)}")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Log token count when LLM completes."""
        try:
            self._check_rate_limit()
            if hasattr(response, 'generations') and response.generations and settings.GOOGLE_API_KEY:
                try:
                    text = response.generations[0][0].text
                    model = genai.GenerativeModel(settings.GEMINI_MODEL)
                    token_count = model.count_tokens(text).total_tokens
                    self.output_tokens = token_count
                    self.total_tokens_per_minute += token_count
                    logger.info(f"Output tokens: {token_count} (Total this minute: {self.total_tokens_per_minute})")
                    logger.info(f"Total tokens for this request: {self.input_tokens + self.output_tokens}")
                except Exception as token_error:
                    logger.debug(f"Could not count output tokens: {str(token_error)}")
                    # Estimate tokens
                    if hasattr(response, 'generations') and response.generations:
                        text = response.generations[0][0].text
                        estimated_tokens = len(text) // 4
                        self.output_tokens = estimated_tokens
                        self.total_tokens_per_minute += estimated_tokens
                        logger.info(f"Estimated output tokens: {estimated_tokens}")
        except Exception as e:
            logger.error(f"Error in output token tracking: {str(e)}")

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
            # Initialize Ollama for Gemma3:12b
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
                # Initialize enhanced token debug handler
                token_handler = EnhancedTokenDebugHandler()

                self.gemini_model = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    temperature=settings.MODEL_TEMPERATURE,
                    top_p=settings.MODEL_TOP_P,
                    top_k=settings.MODEL_TOP_K,
                    max_output_tokens=settings.MODEL_MAX_TOKENS,
                    google_api_key=settings.GOOGLE_API_KEY,
                    streaming=True,
                    callbacks=[token_handler]
                )
                logger.info(f"Gemini model initialized with: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {str(e)}", exc_info=True)
            self.gemini_model = None

    async def process_document(self, document: DBDocument, file_path: str) -> bool:
        """Process a document and add it to vector store"""
        try:
            # Create a Pydantic schema object from the database model object
            # to pass to the downstream processing services.
            schema_document = SchemaDocument(
                id=str(document.id),
                filename=document.original_filename,
                uuid_filename=document.uuid_filename,
                file_type=document.file_type,
                file_size=document.file_size,
                upload_date=document.created_at,
                processed=False  # This field isn't critical for processing
            )
            
            logger.info(f"Processing document: {schema_document.filename}")
            processed_chunks = await self.document_processor.process_document(schema_document, file_path)
            
            if not processed_chunks:
                logger.warning(f"No chunks extracted from document: {schema_document.filename}")
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
        """Format the data dictionary as a Server-Sent Events message."""
        return f"data: {json.dumps(data)}\\n\\n"
    
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
            
    @async_rate_limited
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
                {{
                    "filename": "filename to filter on (or null if not specified)",
                    "file_type": "file type to filter on (or null if not specified)"
                }}
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
    
    async def _perform_hybrid_search(self, query: str, k: int = 5, session_document_filter: Optional[List[str]] = None) -> List[Dict]:
        """Perform a hybrid search combining semantic search with metadata filtering"""
        try:
            metadata_filters = None

            # If session filtering is active, prioritize it and skip query metadata extraction
            if session_document_filter:
                logger.info(f"Using session document filter: {session_document_filter}")
                metadata_filters = {}
                # Filter by document UUIDs associated with the session
                # Use uuid_filename which is the correct metadata field
                if len(session_document_filter) == 1:
                    metadata_filters["uuid_filename"] = session_document_filter[0]
                else:
                    # For multiple documents, we need to use $in operator if supported
                    # For now, we'll handle this in the vector store service
                    metadata_filters["uuid_filename"] = {"$in": session_document_filter}

                logger.info(f"Applied session filter: {metadata_filters}")
            else:
                # Only extract query metadata if no session filter is provided
                try:
                    metadata_filters = await self._extract_query_metadata(query)
                    if metadata_filters:
                        logger.info(f"Extracted query metadata filters: {metadata_filters}")
                except Exception as e:
                    logger.warning(f"Failed to extract query metadata, proceeding without: {str(e)}")
                    metadata_filters = None

            # Get semantic search results
            start_time = time.time()
            search_results = await self.vector_store_service.similarity_search(
                query=query,
                k=k,
                filter_dict=metadata_filters if metadata_filters else None
            )
            logger.info(f"Semantic search completed in {time.time() - start_time:.2f}s with {len(search_results)} results")

            # Log which documents were found for debugging
            if search_results:
                found_docs = set()
                for result in search_results:
                    metadata = result.get("metadata", {})
                    uuid_filename = metadata.get("uuid_filename", "Unknown")
                    filename = metadata.get("filename", "Unknown")
                    found_docs.add(f"{filename} ({uuid_filename})")
                logger.info(f"Search found documents: {list(found_docs)}")

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

    async def _get_session_document_filter(self, session_uuid: str) -> Optional[List[str]]:
        """Get document UUIDs associated with a chat session"""
        try:
            from app.database.connection import AsyncSessionLocal
            from app.database.services import ChatService

            async with AsyncSessionLocal() as db_session:
                # Get the chat session
                chat_session = await ChatService.get_session_by_uuid(db_session, session_uuid)
                if not chat_session:
                    logger.warning(f"Chat session {session_uuid} not found")
                    return None

                # Get associated documents
                documents = await ChatService.get_session_documents(db_session, chat_session.id)

                if not documents:
                    logger.info(f"No documents associated with session {session_uuid}")
                    return None

                # Return list of document UUIDs
                document_uuids = [doc.uuid_filename for doc in documents]
                logger.info(f"Session {session_uuid} has {len(document_uuids)} associated documents")
                return document_uuids

        except Exception as e:
            logger.error(f"Error getting session document filter: {str(e)}")
            return None

    async def generate_response(self, query: QueryRequest, session_uuid: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Generate streaming response for the query using advanced RAG techniques"""
        try:
            # Force Gemini provider since that's what the user has configured
            provider = query.model_provider or "gemini"
            if provider != "gemini":
                logger.warning(f"Requested provider {provider} not available, using Gemini")
                provider = "gemini"

            # Update current provider to ensure consistency
            self.current_provider = provider
            logger.info(f"Starting generate_response with provider: {provider}")

            # Apply custom model parameters if provided
            if query.llm_config:
                logger.info(f"Custom LLM config applied: {query.llm_config}")

            # Check if we're approaching rate limits for Gemini
            if provider == "gemini":
                # Check rate limiter status
                if not gemini_limiter.can_make_call():
                    wait_time = gemini_limiter.time_until_available()
                    logger.warning(f"Gemini rate limit reached, waiting {wait_time:.2f}s")
                    yield self.format_sse({
                        "type": "warning",
                        "content": f"Gemini API rate limit reached. Please wait {wait_time:.1f} seconds before trying again."
                    })
                    # Wait for rate limit to reset instead of switching providers
                    await asyncio.sleep(wait_time)

                # Record the API call for rate limiting
                gemini_limiter.add_call()

                # Also check token handler if available
                if hasattr(self.gemini_model, "callbacks"):
                    for callback in self.gemini_model.callbacks:
                        if isinstance(callback, EnhancedTokenDebugHandler):
                            if (callback.total_tokens_per_minute > callback.max_tokens_per_minute * 0.8 or
                                callback.request_count > callback.max_requests_per_minute * 0.8):
                                logger.warning("Approaching Gemini token/request limits, waiting before proceeding")
                                yield self.format_sse({
                                    "type": "warning",
                                    "content": "Approaching Gemini API limits. Slowing down requests."
                                })
                                await asyncio.sleep(2)  # Brief pause to avoid hitting limits
                                break
                        
            # Get session-specific document filter if session_uuid is provided
            session_document_filter = None
            if session_uuid:
                session_document_filter = await self._get_session_document_filter(session_uuid)

            # Perform hybrid search with retry logic
            try:
                search_results = await self._perform_hybrid_search(
                    query.question,
                    k=query.context_window or settings.DEFAULT_CONTEXT_WINDOW,
                    session_document_filter=session_document_filter
                )
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    logger.warning("Rate limit hit during search, waiting and retrying")
                    yield self.format_sse({
                        "type": "warning",
                        "content": "Rate limit reached during search. Waiting and retrying..."
                    })
                    # Wait and retry once
                    await asyncio.sleep(5)
                    search_results = await self._perform_hybrid_search(
                        query.question,
                        k=query.context_window or settings.DEFAULT_CONTEXT_WINDOW,
                        session_document_filter=session_document_filter
                    )
                else:
                    raise
            
            # Apply re-ranking
            search_results = self._re_rank_results(search_results, query.question)
            
            logger.info(f"Found {len(search_results)} relevant documents")
            
            if not search_results:
                yield self.format_sse({
                    "type": "error",
                    "content": "No relevant documents found in the knowledge base."
                })
                return

            # Format context with relevance scores and token management
            context_parts = []
            total_context_length = 0
            max_context_length = 2000  # Very small limit for free tier

            for i, result in enumerate(search_results, 1):
                content = result["content"]
                score = result.get("score", "N/A")
                metadata = result.get("metadata", {})
                filename = metadata.get("filename", "Unknown")
                logger.debug(f"Document {i} '{filename}' relevance score: {score}")

                # Truncate content if too long
                if len(content) > 500:  # Much smaller chunks
                    content = content[:500] + "..."

                # Add source information to each chunk
                chunk_text = f"[Source: {filename} | Relevance: {score:.2f}]\n{content}"

                # Check if adding this chunk would exceed our limit
                if total_context_length + len(chunk_text) > max_context_length:
                    logger.info(f"Context limit reached, using {len(context_parts)} out of {len(search_results)} documents")
                    break

                context_parts.append(chunk_text)
                total_context_length += len(chunk_text)

            context = "\n\n---\n\n".join(context_parts)
            logger.info(f"Final context length: {len(context)} characters")
            
            try:
                model = self.get_current_model()
                logger.info(f"Model initialized: {type(model)}")

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
                
                try:
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
                except Exception as stream_error:
                    error_str = str(stream_error).lower()
                    if ("429" in error_str or "rate limit" in error_str or
                        "quota" in error_str or "resourceexhausted" in error_str):
                        logger.warning(f"Rate limit error during streaming: {stream_error}")
                        yield self.format_sse({
                            "type": "error",
                            "content": "Gemini API rate limit reached. Please wait a moment and try again."
                        })
                        return
                    else:
                        raise stream_error
                
                # Send any remaining text in the buffer
                if buffer.strip():
                    yield self.format_sse({
                        "type": "response",
                        "content": buffer.strip(),
                        "provider": provider
                    })

                # After the main response, send the list of source documents so that
                # downstream consumers (e.g. voice WebSocket) can mention them.
                try:
                    source_list = [
                        {
                            "filename": res.get("metadata", {}).get("filename", "Unknown"),
                            "document_id": res.get("metadata", {}).get("document_id")
                        }
                        for res in search_results[:5]
                    ]
                except Exception:
                    source_list = []

                yield self.format_sse({
                    "type": "sources",
                    "sources": source_list,
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

    def set_provider(self, provider: str):
        """Set the model provider ('ollama' or 'gemini')"""
        if provider not in ["ollama", "gemini"]:
            logger.error(f"Invalid provider: {provider}")
            raise ValueError("Invalid provider")
        self.current_provider = provider




