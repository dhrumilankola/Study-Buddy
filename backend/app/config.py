# --- Standard library imports ---
import os
import json
import logging
from typing import List, Optional

# Third-party imports
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

# Safe JSON loader that gracefully falls back to the raw string when the value
# is not valid JSON. This allows environment variables such as
# `ALLOWED_EXTENSIONS=.pdf,.txt` to be parsed later by validators instead of
# raising an exception during Pydantic's initial JSON decoding step.

def _safe_json_loads(value):
    """Attempt to load *value* as JSON, but return the original value on
    failure so that downstream validators can handle alternative formats.
    """
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value

# -----------------------------------------------------------------------------
# Settings model
# -----------------------------------------------------------------------------

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra='ignore'
    )
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Study Buddy API"
    
    # Environment
    ENVIRONMENT: str = Field(default="dev", env="ENVIRONMENT")
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="BACKEND_CORS_ORIGINS"
    )
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    
    # Security
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Short-lived tokens for EVI
    
    # File upload settings
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")
    VECTOR_STORE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "vector_store")
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20MB
    ALLOWED_EXTENSIONS: List[str] = ['.pdf', '.txt', '.pptx', '.ipynb']
    
    # Model settings
    OLLAMA_MODEL: str = "gemma3:12b"
    DEFAULT_MODEL_PROVIDER: str = "ollama"  # Options: "ollama", "gemini"
    
    # Embeddings settings
    EMBEDDINGS_MODEL_TYPE: str = "sentence_transformer"
    EMBEDDINGS_MODEL: str = "all-mpnet-base-v2"
    EMBEDDINGS_DEVICE: str = "cpu"
    
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
    HUME_EVI_CONFIG_ID: Optional[str] = None  # Will be set after creating custom config
    
    # Document processing settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # RAG settings
    DEFAULT_CONTEXT_WINDOW: int = 5
    MAX_CONTEXT_WINDOW: int = 10
    
    # Performance settings
    REQUEST_TIMEOUT: int = 60  # seconds
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def split_cors_origins(cls, v):
        if isinstance(v, str):
            # split on commas, strip whitespace, drop empties
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    def split_allowed_extensions(cls, v):
        """Allow ALLOWED_EXTENSIONS to be provided as a simple comma-separated
        string (e.g. ".pdf,.txt") instead of strict JSON to make local
        configuration easier.
        """
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",") if ext.strip()]
        return v

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