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
    uuid_filename: Optional[str] = None  # Add uuid_filename for proper vector store metadata
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

# Database response models
class ProcessingStatus(str, Enum):
    """Document processing status enumeration"""
    PROCESSING = "processing"
    INDEXED = "indexed"
    ERROR = "error"
    FAILED = "failed"

class DocumentResponse(BaseModel):
    """Database document response model"""
    id: int
    original_filename: str
    uuid_filename: str
    file_type: str
    processing_status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
    file_size: int
    chunk_count: int
    document_metadata: Dict[str, Any]  # Renamed from 'metadata'

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    """Chat session response model"""
    id: int
    session_uuid: str
    title: Optional[str]
    created_at: datetime
    last_activity: datetime
    model_provider_used: Optional[ModelProvider]
    total_messages: int
    documents: Optional[List[DocumentResponse]] = None  # Include associated documents

    class Config:
        from_attributes = True

class ChatMessageResponse(BaseModel):
    """Chat message response model"""
    id: int
    session_id: int
    message_content: str
    response_content: Optional[str]
    timestamp: datetime
    model_provider: Optional[ModelProvider]
    token_count: Optional[int]
    processing_time_ms: Optional[int]

    class Config:
        from_attributes = True

# Request models for chat session management
class CreateChatSessionRequest(BaseModel):
    """Request model for creating a new chat session"""
    title: Optional[str] = None
    document_ids: Optional[List[int]] = []
    model_provider: Optional[ModelProvider] = None

class UpdateChatSessionRequest(BaseModel):
    """Request model for updating a chat session"""
    title: Optional[str] = None
    document_ids: Optional[List[int]] = None

class ChatSessionWithDocumentsResponse(BaseModel):
    """Extended chat session response with full document details"""
    id: int
    session_uuid: str
    title: Optional[str]
    created_at: datetime
    last_activity: datetime
    model_provider_used: Optional[ModelProvider]
    total_messages: int
    documents: List[DocumentResponse]

    class Config:
        from_attributes = True