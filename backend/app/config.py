from pydantic_settings import BaseSettings
import os
from typing import List, Literal
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Study Buddy API"
    
    # File settings
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")
    VECTOR_STORE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "vector_store")
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20MB
    
    # Model configuration
    DEFAULT_MODEL_PROVIDER: Literal["ollama", "gemini"] = "ollama"
    MODEL_TEMPERATURE: float = 0.7
    
    # Ollama settings
    OLLAMA_MODEL: str = "gemma"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # Gemini settings
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")  
    GEMINI_MODEL: str = "gemini-1.5-flash"  
    
    # Vector store settings
    EMBEDDINGS_MODEL: str = "all-MiniLM-L6-v2"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    class Config:
        case_sensitive = True
        env_file = ".env"

# Create instance
settings = Settings()

# Initialize directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)