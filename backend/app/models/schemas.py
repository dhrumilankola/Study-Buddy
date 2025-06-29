from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PROCESSING = "processing"
    INDEXED = "indexed"
    ERROR = "error"
    FAILED = "failed"

class ModelProvider(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"

class SessionType(str, Enum):
    TEXT = "text"
    VOICE = "voice"

class Document(BaseModel):
    id: str
    filename: str
    uuid_filename: Optional[str] = None
    file_type: str
    file_size: int
    upload_date: datetime
    processed: bool = False

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: int
    original_filename: str
    uuid_filename: str
    file_type: str
    processing_status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
    file_size: int
    chunk_count: int
    document_metadata: Optional[Dict[str, Any]] = {}

    class Config:
        from_attributes = True

class QueryRequest(BaseModel):
    query: str
    context_window: Optional[int] = Field(default=3, ge=1, le=10)
    model_provider: Optional[ModelProvider] = ModelProvider.OLLAMA
    session_uuid: Optional[str] = None

class LLMConfig(BaseModel):
    provider: ModelProvider

class ChatSessionResponse(BaseModel):
    id: int
    session_uuid: str
    title: Optional[str]
    session_type: SessionType
    created_at: datetime
    last_activity: datetime
    model_provider_used: Optional[ModelProvider]
    total_messages: int

    class Config:
        from_attributes = True

class ChatSessionWithDocumentsResponse(BaseModel):
    id: int
    session_uuid: str
    title: Optional[str]
    session_type: SessionType
    created_at: datetime
    last_activity: datetime
    model_provider_used: Optional[ModelProvider]
    total_messages: int
    documents: Optional[List[DocumentResponse]] = None

    class Config:
        from_attributes = True

class ChatMessageResponse(BaseModel):
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

class CreateChatSessionRequest(BaseModel):
    title: Optional[str] = None
    document_ids: Optional[List[int]] = []
    model_provider: Optional[ModelProvider] = None
    session_type: Optional[SessionType] = SessionType.TEXT

class UpdateChatSessionRequest(BaseModel):
    title: Optional[str] = None
    document_ids: Optional[List[int]] = None

class VoiceChatConfigResponse(BaseModel):
    api_key: str
    agent_id: str