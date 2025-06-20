from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings, HuggingFaceEmbeddings
from typing import List, Dict, Optional, Union, Any
import os
import asyncio
from app.config import settings
import logging
import numpy as np

logger = logging.getLogger(__name__)

class EnhancedVectorStoreService:
    def __init__(self):
        self.vector_store_path = settings.VECTOR_STORE_PATH
        self._vector_store = None
        self._initialize_embeddings()
        
    def _initialize_embeddings(self):
        """Initialize the embedding model"""
        try:
            # Use a more powerful embedding model
            if settings.EMBEDDINGS_MODEL_TYPE == "sentence_transformer":
                # For general purpose, all-mpnet-base-v2 is excellent for semantic search
                self.embeddings = SentenceTransformerEmbeddings(model_name=settings.EMBEDDINGS_MODEL)
                logger.info(f"Initialized SentenceTransformer embeddings with model: {settings.EMBEDDINGS_MODEL}")
            elif settings.EMBEDDINGS_MODEL_TYPE == "huggingface":
                # HuggingFace embeddings with more options and control
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=settings.EMBEDDINGS_MODEL,
                    model_kwargs={"device": settings.EMBEDDINGS_DEVICE},
                    encode_kwargs={"normalize_embeddings": True}
                )
                logger.info(f"Initialized HuggingFace embeddings with model: {settings.EMBEDDINGS_MODEL}")
            else:
                # Default fallback
                self.embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
                logger.warning(f"Unknown embeddings type: {settings.EMBEDDINGS_MODEL_TYPE}, using default")
        except Exception as e:
            logger.error(f"Error initializing embeddings: {str(e)}")
            # Fallback to a smaller model that's more likely to work
            self.embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
            logger.info("Falling back to default embeddings model: all-MiniLM-L6-v2")

    @property
    def vector_store(self):
        if self._vector_store is None:
            self._initialize_vector_store()
        return self._vector_store

    def _initialize_vector_store(self):
        """Initialize or load existing vector store with enhanced settings"""
        try:
            # Create the directory if it doesn't exist
            os.makedirs(self.vector_store_path, exist_ok=True)
            
            # Configure Chroma with more robust settings
            self._vector_store = Chroma(
                persist_directory=self.vector_store_path,
                embedding_function=self.embeddings,
                collection_name=settings.VECTOR_STORE_COLLECTION_NAME,
                collection_metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            logger.info(f"Vector store initialized at {self.vector_store_path}")
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise

    async def add_documents(self, texts: List[str], metadatas: List[Dict] = None) -> bool:
        """Add documents to vector store with error handling and retries"""
        if not texts:
            logger.warning("No texts provided to add to vector store")
            return False
            
        # Handle empty metadata case
        if metadatas is None:
            metadatas = [{} for _ in texts]
            
        # Ensure vector store is initialized
        if self._vector_store is None:
            self._initialize_vector_store()
            
        try:
            # Add texts in batches to prevent memory issues with large documents
            batch_size = settings.VECTOR_STORE_BATCH_SIZE
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_metadatas = metadatas[i:i+batch_size]
                
                # Filter out any empty texts
                valid_indices = [j for j, text in enumerate(batch_texts) if text.strip()]
                if not valid_indices:
                    continue
                    
                filtered_texts = [batch_texts[j] for j in valid_indices]
                filtered_metadatas = [batch_metadatas[j] for j in valid_indices]
                
                # Add to vector store with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self._vector_store.add_texts(
                            texts=filtered_texts, 
                            metadatas=filtered_metadatas
                        )
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Retry {attempt+1}/{max_retries} after error: {str(e)}")
                            await asyncio.sleep(1)  # Wait before retry
                        else:
                            raise
                            
                logger.info(f"Added batch of {len(filtered_texts)} documents to vector store")
                
            # Explicitly persist after adding documents
            if hasattr(self._vector_store, "_persist"):
                self._vector_store._persist()
                
            return True
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise

    async def similarity_search(self, query: str, k: int = 3, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        Enhanced similarity search with filtering capabilities
        
        Args:
            query: The search query
            k: Number of results to return
            filter_dict: Optional metadata filter dictionary
            
        Returns:
            List of documents with content, metadata, and score
        """
        try:
            # Ensure vector store is initialized
            if self._vector_store is None:
                self._initialize_vector_store()
                
            collection = self._vector_store._collection
            total_docs = collection.count()
            
            if total_docs == 0:
                logger.warning("No documents in vector store")
                return []
                
            # Adjust k if needed
            k = min(k, total_docs)
            
            # Perform search with optional filtering
            if filter_dict:
                # Handle special case for multiple uuid_filename filtering
                if "uuid_filename" in filter_dict and isinstance(filter_dict["uuid_filename"], dict):
                    if "$in" in filter_dict["uuid_filename"]:
                        # Handle multiple document filtering
                        uuid_list = filter_dict["uuid_filename"]["$in"]
                        all_results = []

                        # Search for each document separately and combine results
                        for uuid_filename in uuid_list:
                            single_filter = {k: v for k, v in filter_dict.items() if k != "uuid_filename"}
                            single_filter["uuid_filename"] = uuid_filename

                            try:
                                single_results = self._vector_store.similarity_search_with_score(
                                    query, k=k, filter=single_filter
                                )
                                all_results.extend(single_results)
                            except Exception as e:
                                logger.warning(f"Error searching with filter {single_filter}: {e}")
                                continue

                        # Sort by score and take top k
                        all_results.sort(key=lambda x: x[1])  # Sort by score (lower is better for distance)
                        results = all_results[:k]
                    else:
                        results = self._vector_store.similarity_search_with_score(
                            query, k=k, filter=filter_dict
                        )
                else:
                    results = self._vector_store.similarity_search_with_score(
                        query, k=k, filter=filter_dict
                    )
            else:
                results = self._vector_store.similarity_search_with_score(
                    query, k=k
                )
                
            # Process and normalize scores
            search_results = []
            for doc, score in results:
                # Handle different score formats
                if isinstance(score, np.ndarray):
                    score = float(score[0])
                else:
                    score = float(score)
                    
                # Convert distance to similarity score (if using L2 distance)
                if score > 1.0:  # Likely a distance metric
                    similarity = 1.0 / (1.0 + score)
                else:
                    similarity = score
                    
                search_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": similarity
                })
                
            return search_results
            
        except Exception as e:
            logger.error(f"Error performing similarity search: {str(e)}")
            raise
            
    async def delete_by_metadata(self, filter_dict: Dict[str, Any]) -> bool:
        """Delete documents matching the filter criteria"""
        try:
            if self._vector_store is None:
                self._initialize_vector_store()
                
            self._vector_store.delete(
                filter=filter_dict
            )
            
            # Explicitly persist after deletion
            if hasattr(self._vector_store, "_persist"):
                self._vector_store._persist()
                
            logger.info(f"Deleted documents with filter: {filter_dict}")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            raise
            
    async def get_document_count(self) -> int:
        """Get the total number of documents in the vector store"""
        try:
            if self._vector_store is None:
                self._initialize_vector_store()

            collection = self._vector_store._collection
            return collection.count()
        except Exception as e:
            logger.error(f"Error getting document count: {str(e)}")
            return 0

    async def get_document_chunk_count(self, uuid_filename: str) -> int:
        """Get the number of chunks for a specific document by UUID filename"""
        try:
            if self._vector_store is None:
                self._initialize_vector_store()

            # Query the collection with metadata filter
            collection = self._vector_store._collection
            results = collection.get(
                where={"uuid_filename": uuid_filename}
            )

            # Return the count of chunks for this document
            return len(results['ids']) if results and 'ids' in results else 0

        except Exception as e:
            logger.error(f"Error getting document chunk count for {uuid_filename}: {str(e)}")
            return 0