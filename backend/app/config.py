from pydantic_settings import BaseSettings
import os
from typing import List, Optional
import logging
from pydantic import validator

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
    OLLAMA_MODEL: str
    DEFAULT_MODEL_PROVIDER: str
    
    # Embeddings settings
    EMBEDDINGS_MODEL_TYPE: str = "sentence_transformer"
    EMBEDDINGS_MODEL: str = "all-mpnet-base-v2"
    EMBEDDINGS_DEVICE: str = "cpu"
    
    # Ollama settings
    OLLAMA_BASE_URL: str
    MODEL_TEMPERATURE: float
    MODEL_TOP_P: float
    MODEL_TOP_K: int
    MODEL_MAX_TOKENS: int
    
    # Vector store settings
    VECTOR_STORE_COLLECTION_NAME: str = "study_buddy_docs"
    VECTOR_STORE_BATCH_SIZE: int = 10
    
    # Google AI settings (for Gemini)
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_PROJECT_ID: Optional[str] = None
    GEMINI_MODEL: str

    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://study_buddy:study_buddy_password@localhost:5432/study_buddy_db"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "study_buddy_db"
    DATABASE_USER: str = "study_buddy"
    DATABASE_PASSWORD: str = "study_buddy_password"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Document processing settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # RAG settings
    DEFAULT_CONTEXT_WINDOW: int = 1
    MAX_CONTEXT_WINDOW: int = 2
    
    # Performance settings
    REQUEST_TIMEOUT: int = 60  # seconds

    @validator("DEFAULT_MODEL_PROVIDER")
    def validate_model_provider(cls, v):
        if v not in ["ollama", "gemini"]:
            raise ValueError("DEFAULT_MODEL_PROVIDER must be either 'ollama' or 'gemini'")
        return v

    @validator("GOOGLE_API_KEY")
    def validate_api_key(cls, v, values):
        if values.get("DEFAULT_MODEL_PROVIDER") == "gemini" and not v:
            raise ValueError("GOOGLE_API_KEY is required when using Gemini provider")
        return v

    @validator("MODEL_TEMPERATURE")
    def validate_temperature(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("MODEL_TEMPERATURE must be between 0 and 1")
        return v

    @validator("MODEL_TOP_P")
    def validate_top_p(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("MODEL_TOP_P must be between 0 and 1")
        return v

    @validator("MODEL_TOP_K")
    def validate_top_k(cls, v):
        if not 1 <= v <= 100:
            raise ValueError("MODEL_TOP_K must be between 1 and 100")
        return v
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

try:
    # Create instance
    settings = Settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    # Log successful configuration
    logging.info(f"Configuration loaded successfully")
    logging.info(f"Using model provider: {settings.DEFAULT_MODEL_PROVIDER}")
    logging.info(f"Model: {settings.GEMINI_MODEL if settings.DEFAULT_MODEL_PROVIDER == 'gemini' else settings.OLLAMA_MODEL}")

    # Ensure required directories exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)

except Exception as e:
    logging.error(f"Error loading configuration: {str(e)}")
    raise