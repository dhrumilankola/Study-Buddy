import os
import logging
from typing import List, Optional

from pydantic import validator, Extra, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ─── Pydantic-Settings configuration ─────────────────────────────────────
    model_config = SettingsConfigDict(
        extra=Extra.ignore,              # skip any undeclared .env entries
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ─── API & CORS ───────────────────────────────────────────────────────────
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Study Buddy API"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # ─── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ─── File upload ─────────────────────────────────────────────────────────
    UPLOAD_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data", "uploads"
    )
    VECTOR_STORE_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data", "vector_store"
    )
    MAX_FILE_SIZE: int = 20 * 1024 * 1024
    ALLOWED_EXTENSIONS: List[str] = ['.pdf', '.txt', '.pptx', '.ipynb']

    # ─── Model & Embeddings ─────────────────────────────────────────────────
    OLLAMA_MODEL: str
    DEFAULT_MODEL_PROVIDER: str
    EMBEDDINGS_MODEL_TYPE: str = "sentence_transformer"
    EMBEDDINGS_MODEL: str = "all-mpnet-base-v2"
    EMBEDDINGS_DEVICE: str = "cpu"

    # ─── Ollama tuning ────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str
    MODEL_TEMPERATURE: float
    MODEL_TOP_P: float
    MODEL_TOP_K: int
    MODEL_MAX_TOKENS: int

    # ─── Vector store ────────────────────────────────────────────────────────
    VECTOR_STORE_COLLECTION_NAME: str = "study_buddy_docs"
    VECTOR_STORE_BATCH_SIZE: int = 10

    # ─── Gemini settings ─────────────────────────────────────────────────────
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_PROJECT_ID: Optional[str] = None
    GEMINI_MODEL: str

    # ─── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://study_buddy:study_buddy_password@localhost:5432/study_buddy_db"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "study_buddy_db"
    DATABASE_USER: str = "study_buddy"
    DATABASE_PASSWORD: str = "study_buddy_password"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ─── Processing & RAG ────────────────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    DEFAULT_CONTEXT_WINDOW: int = 1
    MAX_CONTEXT_WINDOW: int = 2
    REQUEST_TIMEOUT: int = 60

    # ─── ElevenLabs Conversational AI ────────────────────────────────────────
    ELEVENLABS_API_KEY: Optional[str] = None
    AGENT_ID: Optional[str] = None

    # ─── Validators ──────────────────────────────────────────────────────────
    @field_validator("DEFAULT_MODEL_PROVIDER")
    @classmethod
    def validate_model_provider(cls, v):
        if v not in ["ollama", "gemini"]:
            raise ValueError("DEFAULT_MODEL_PROVIDER must be 'ollama' or 'gemini'")
        return v

    @field_validator("GOOGLE_API_KEY")
    @classmethod
    def validate_api_key(cls, v, info):
        if info.data.get("DEFAULT_MODEL_PROVIDER") == "gemini" and not v:
            raise ValueError("GOOGLE_API_KEY is required when using Gemini provider")
        return v

    @field_validator("ELEVENLABS_API_KEY", "AGENT_ID")
    @classmethod
    def validate_elevenlabs_settings(cls, v, info):
        if info.field_name == "ELEVENLABS_API_KEY" and v and not v.startswith("sk_"):
            raise ValueError("ELEVENLABS_API_KEY should start with 'sk_'")
        if info.field_name == "AGENT_ID" and v and not v.startswith("agent_"):
            raise ValueError("AGENT_ID should start with 'agent_'")
        return v

    @field_validator("MODEL_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError("MODEL_TEMPERATURE must be between 0.0 and 2.0")
        return v

    @field_validator("MODEL_TOP_P")
    @classmethod
    def validate_top_p(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("MODEL_TOP_P must be between 0.0 and 1.0")
        return v

    @field_validator("MODEL_TOP_K")
    @classmethod
    def validate_top_k(cls, v):
        if v < 1:
            raise ValueError("MODEL_TOP_K must be at least 1")
        return v

    @field_validator("MAX_FILE_SIZE")
    @classmethod
    def validate_file_size(cls, v):
        if v < 1024:
            raise ValueError("MAX_FILE_SIZE must be at least 1KB")
        return v

# ─── Instantiate & configure logging ─────────────────────────────────────────
settings = Settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.info("Configuration loaded successfully")
logging.info(f"Using model provider: {settings.DEFAULT_MODEL_PROVIDER}")
logging.info(
    f"Model: {settings.GEMINI_MODEL if settings.DEFAULT_MODEL_PROVIDER == 'gemini' else settings.OLLAMA_MODEL}"
)

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
