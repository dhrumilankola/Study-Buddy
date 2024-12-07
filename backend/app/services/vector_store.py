from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from typing import List, Dict, Optional
import os
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self):
        self.embeddings = SentenceTransformerEmbeddings(model_name=settings.EMBEDDINGS_MODEL)
        self.vector_store_path = settings.VECTOR_STORE_PATH
        self._vector_store = None

    @property
    def vector_store(self):
        if self._vector_store is None:
            self._initialize_vector_store()
        return self._vector_store

    def _initialize_vector_store(self):
        """Initialize or load existing vector store"""
        try:
            self._vector_store = Chroma(
                persist_directory=self.vector_store_path,
                embedding_function=self.embeddings
            )
            self._vector_store.persist()
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise

    async def add_documents(self, texts: List[str], metadatas: List[Dict] = None):
        """Add documents to vector store"""
        try:
            if not texts:
                logger.warning("No texts provided to add to vector store")
                return False
            
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
            self.vector_store.persist()
            return True
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise

    async def similarity_search(self, query: str, k: int = 3) -> List[Dict]:
        """Perform similarity search"""
        try:
            # Get the total number of documents in the store
            collection = self.vector_store._collection
            total_docs = collection.count()
            
            # Adjust k if it's greater than available documents
            k = min(k, total_docs) if total_docs > 0 else k

            if total_docs == 0:
                logger.warning("No documents in vector store")
                return []

            results = self.vector_store.similarity_search_with_score(query, k=k)
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)  # Convert to float for JSON serialization
                }
                for doc, score in results
            ]
        except Exception as e:
            logger.error(f"Error performing similarity search: {str(e)}")
            raise