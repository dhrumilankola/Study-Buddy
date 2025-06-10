from pydantic_settings import BaseSettings
from pydantic import Field
import os
from typing import List, Optional
import logging

class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Study Buddy API"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    
    # File upload settings
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")
    VECTOR_STORE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "vector_store")
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20MB
    ALLOWED_EXTENSIONS: List[str] = ['.pdf', '.txt', '.pptx', '.ipynb']
    
    # Model settings
    OLLAMA_MODEL: str = "gemma2:9b"  # Updated to use Gemma2:9b
    DEFAULT_MODEL_PROVIDER: str = "ollama"  # Options: "ollama", "gemini"
    
    # Embeddings settings
    EMBEDDINGS_MODEL_TYPE: str = "sentence_transformer"  # Options: "sentence_transformer", "huggingface"
    EMBEDDINGS_MODEL: str = "all-mpnet-base-v2"  # Stronger model than the previous one
    EMBEDDINGS_DEVICE: str = "cpu"  # Options: "cpu", "cuda", "mps"
    
    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_TEMPERATURE: float = 0.7
    MODEL_TOP_P: float = 0.95
    MODEL_TOP_K: int = 40
    MODEL_MAX_TOKENS: int = 1024
    
    # Vector store settings
    VECTOR_STORE_COLLECTION_NAME: str = "study_buddy_docs"
    VECTOR_STORE_BATCH_SIZE: int = 10
    
    # Google AI settings (for Gemini)
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_PROJECT_ID: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # Hume AI settings
    HUME_API_KEY: Optional[str] = Field(None, env="HUME_API_KEY")
    HUME_SECRET_KEY: Optional[str] = Field(None, env="HUME_SECRET_KEY")
    
    # Document processing settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # RAG settings
    DEFAULT_CONTEXT_WINDOW: int = 5
    MAX_CONTEXT_WINDOW: int = 10
    
    # Performance settings
    REQUEST_TIMEOUT: int = 60  # seconds
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# Create instance
settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)