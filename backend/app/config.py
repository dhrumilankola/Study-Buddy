# --- Standard library imports ---
import os
import logging
from typing import List, Optional

# Third-party imports
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# -----------------------------------------------------------------------------
# Settings model
# -----------------------------------------------------------------------------

class Settings(BaseSettings):
    # Pydantic V2 model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra='ignore',
        env_file_encoding="utf-8"
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
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

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

    # Hume AI settings
    HUME_API_KEY: Optional[str] = Field(None, env="HUME_API_KEY")
    HUME_SECRET_KEY: Optional[str] = Field(None, env="HUME_SECRET_KEY")
    HUME_EVI_CONFIG_ID: Optional[str] = None  # Will be set after creating custom config

    # Database settings
    DATABASE_URL: str
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
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

    # --- Field Validators ---

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def split_cors_origins(cls, v):
        if isinstance(v, str):
            # split on commas, strip whitespace, drop empties
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    def split_allowed_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",") if ext.strip()]
        return v
    
    @field_validator("DEFAULT_MODEL_PROVIDER")
    def validate_model_provider(cls, v):
        if v not in ["ollama", "gemini"]:
            raise ValueError("DEFAULT_MODEL_PROVIDER must be either 'ollama' or 'gemini'")
        return v

    @field_validator("MODEL_TEMPERATURE")
    def validate_temperature(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("MODEL_TEMPERATURE must be between 0 and 1")
        return v

    @field_validator("MODEL_TOP_P")
    def validate_top_p(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("MODEL_TOP_P must be between 0 and 1")
        return v

    @field_validator("MODEL_TOP_K")
    def validate_top_k(cls, v):
        if not 1 <= v <= 100:
            raise ValueError("MODEL_TOP_K must be between 1 and 100")
        return v

    # --- Model-level Validator ---

    @model_validator(mode='after')
    def validate_gemini_api_key(self):
        if self.DEFAULT_MODEL_PROVIDER == "gemini" and not self.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required when using the Gemini provider")
        return self

try:
    # Create instance
    settings = Settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    # Log successful configuration
    logging.info("Configuration loaded successfully")
    logging.info(f"Using model provider: {settings.DEFAULT_MODEL_PROVIDER}")
    model_in_use = settings.GEMINI_MODEL if settings.DEFAULT_MODEL_PROVIDER == 'gemini' else settings.OLLAMA_MODEL
    logging.info(f"Model: {model_in_use}")

    # Ensure required directories exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)

except Exception as e:
    logging.error(f"Error loading configuration: {str(e)}")
    raise