"""
Database-related API endpoints for Study Buddy application.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from app.database.connection import get_db_session
from app.database.services import DocumentService, ChatService
from app.database.models import ProcessingStatus, ModelProvider
from app.models.schemas import DocumentResponse, ChatSessionResponse, ChatMessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Document endpoints
@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all documents with pagination"""
    try:
        documents = await DocumentService.get_all_documents(db, limit=limit, offset=offset)
        return [
            DocumentResponse(
                id=doc.id,
                original_filename=doc.original_filename,
                uuid_filename=doc.uuid_filename,
                file_type=doc.file_type,
                processing_status=doc.processing_status,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                file_size=doc.file_size,
                chunk_count=doc.chunk_count,
                document_metadata=doc.document_metadata
            )
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch documents")

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific document by ID"""
    try:
        document = await DocumentService.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentResponse(
            id=document.id,
            original_filename=document.original_filename,
            uuid_filename=document.uuid_filename,
            file_type=document.file_type,
            processing_status=document.processing_status,
            created_at=document.created_at,
            updated_at=document.updated_at,
            file_size=document.file_size,
            chunk_count=document.chunk_count,
            document_metadata=document.document_metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch document")

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a document"""
    try:
        success = await DocumentService.delete_document(db, document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete document")

# Chat session endpoints
@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db_session)
):
    """Get recent chat sessions"""
    try:
        sessions = await ChatService.get_recent_sessions(db, limit=limit)
        return [
            ChatSessionResponse(
                id=session.id,
                session_uuid=session.session_uuid,
                created_at=session.created_at,
                last_activity=session.last_activity,
                model_provider_used=session.model_provider_used,
                total_messages=session.total_messages
            )
            for session in sessions
        ]
    except Exception as e:
        logger.error(f"Error fetching chat sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat sessions")

@router.get("/chat/sessions/{session_uuid}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_uuid: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific chat session"""
    try:
        session = await ChatService.get_session_by_uuid(db, session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return ChatSessionResponse(
            id=session.id,
            session_uuid=session.session_uuid,
            created_at=session.created_at,
            last_activity=session.last_activity,
            model_provider_used=session.model_provider_used,
            total_messages=session.total_messages
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat session {session_uuid}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat session")

@router.get("/chat/sessions/{session_uuid}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_uuid: str,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Get messages for a chat session"""
    try:
        # First get the session to verify it exists
        session = await ChatService.get_session_by_uuid(db, session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        messages = await ChatService.get_session_messages(db, session.id, limit=limit, offset=offset)
        return [
            ChatMessageResponse(
                id=message.id,
                session_id=message.session_id,
                message_content=message.message_content,
                response_content=message.response_content,
                timestamp=message.timestamp,
                model_provider=message.model_provider,
                token_count=message.token_count,
                processing_time_ms=message.processing_time_ms
            )
            for message in messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching messages for session {session_uuid}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch messages")

@router.delete("/chat/sessions/{session_uuid}")
async def delete_chat_session(
    session_uuid: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a chat session and all its messages"""
    try:
        success = await ChatService.delete_session(db, session_uuid)
        if not success:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {"message": "Chat session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat session {session_uuid}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete chat session")

@router.post("/chat/sessions")
async def create_chat_session(
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat session"""
    try:
        session = await ChatService.create_session(db)
        return {
            "session_uuid": session.session_uuid,
            "message": "Chat session created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")
