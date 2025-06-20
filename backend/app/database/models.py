"""
Database models for Study Buddy application.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Float, Enum as SQLEnum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid

from app.database.connection import Base

# Association table for many-to-many relationship between chat sessions and documents
chat_session_documents = Table(
    'chat_session_documents',
    Base.metadata,
    Column('chat_session_id', Integer, ForeignKey('chat_sessions.id'), primary_key=True),
    Column('document_id', Integer, ForeignKey('documents.id'), primary_key=True),
    Column('added_at', DateTime(timezone=True), server_default=func.now())
)

class ProcessingStatus(str, Enum):
    """Document processing status enumeration"""
    PROCESSING = "processing"
    INDEXED = "indexed"
    ERROR = "error"
    FAILED = "failed"

class ModelProvider(str, Enum):
    """Model provider enumeration"""
    OLLAMA = "ollama"
    GEMINI = "gemini"

class Document(Base):
    """Document metadata table"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    uuid_filename = Column(String(255), unique=True, nullable=False, index=True)
    file_type = Column(String(50), nullable=False)
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PROCESSING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    chunk_count = Column(Integer, default=0, nullable=False)
    vector_store_ids = Column(JSON, default=list, nullable=False)  # Array of vector store IDs
    document_metadata = Column(JSON, default=dict, nullable=False)  # Additional metadata (renamed from 'metadata')

    # Many-to-many relationship with chat sessions
    chat_sessions = relationship("ChatSession", secondary=chat_session_documents, back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.original_filename}', status='{self.processing_status}')>"

class ChatSession(Base):
    """Chat session table"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=True)  # Session title (auto-generated or user-defined)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    model_provider_used = Column(SQLEnum(ModelProvider), nullable=True)
    total_messages = Column(Integer, default=0, nullable=False)

    # Relationship to chat messages
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    # Many-to-many relationship with documents
    documents = relationship("Document", secondary=chat_session_documents, back_populates="chat_sessions")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, uuid='{self.session_uuid}', title='{self.title}', messages={self.total_messages})>"

class ChatMessage(Base):
    """Chat message table"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    message_content = Column(Text, nullable=False)
    response_content = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    model_provider = Column(SQLEnum(ModelProvider), nullable=True)
    token_count = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)  # Processing time in milliseconds
    
    # Relationship to chat session
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, provider='{self.model_provider}')>"
