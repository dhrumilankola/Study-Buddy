from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

class ModelProvider(str, Enum):
    """Enum for supported model providers"""
    OLLAMA = "ollama"
    GEMINI = "gemini"

class Document(BaseModel):
    """Document model with enhanced metadata"""
    id: str
    filename: str
    file_type: str
    file_size: int
    upload_date: datetime
    processed: bool = False
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class LLMConfig(BaseModel):
    """Configuration for the language model"""
    provider: ModelProvider = Field(default=ModelProvider.OLLAMA)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)
    top_p: Optional[float] = Field(default=0.95, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=40, ge=0, le=100)
    max_tokens: Optional[int] = Field(default=1024, ge=16, le=4096)

class QueryRequest(BaseModel):
    """Enhanced query request model"""
    question: str = Field(..., min_length=1)
    context_window: Optional[int] = Field(default=5, ge=1, le=10)
    model_provider: Optional[ModelProvider] = None
    llm_config: Optional[LLMConfig] = None  # Changed from model_config to llm_config
    filter_metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True

class Response(BaseModel):
    """Response model for streaming responses"""
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    """Enhanced error response with more detail"""
    detail: str
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
class StatusResponse(BaseModel):
    """System status response"""
    status: str
    documents_in_vector_store: int
    uploaded_files_count: int
    embedding_model: str
    llm_model: Dict[str, Any]
    timestamp: datetime

class DocumentTextResponse(BaseModel):
    """Response containing document text chunks"""
    filename: str
    chunk_count: int
    chunks: List[Dict[str, Any]]