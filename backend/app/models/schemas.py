from pydantic import BaseModel, Field
from typing import List, Optional
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

class Response(BaseModel):
    question: str
    answer: str
    sources: List[str]
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    detail: str
    timestamp: datetime = Field(default_factory=datetime.now)