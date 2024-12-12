from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

class Document(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    upload_date: datetime
    processed: bool = False

    class Config:
        from_attributes = True

class Query(BaseModel):
    question: str = Field(..., min_length=1)
    context_window: Optional[int] = Field(default=3, ge=1, le=10)
    model_provider: Optional[Literal["ollama", "gemini"]] = None

class Response(BaseModel):
    question: str
    answer: str
    sources: List[str]
    model_provider: Literal["ollama", "gemini"]
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    detail: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ModelConfig(BaseModel):
    provider: Literal["ollama", "gemini"]
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_output_tokens: Optional[int] = None

class ModelStatus(BaseModel):
    current_provider: Literal["ollama", "gemini"]
    model_name: str
    temperature: float
    is_operational: bool
    documents_indexed: int = 0
    additional_info: Dict[str, Any] = Field(default_factory=dict)