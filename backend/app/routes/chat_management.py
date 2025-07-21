"""
Chat session management API endpoints for Study Buddy application.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
import uuid
from app.database.connection import get_db_session
from app.database.services import DocumentService, ChatService
from app.database.models import ProcessingStatus, ModelProvider, ChatSession
from app.models.schemas import (
    CreateChatSessionRequest,
    UpdateChatSessionRequest,
    ChatSessionResponse,
    ChatSessionWithDocumentsResponse,
    DocumentResponse,
    QueryRequest,
    ChatMessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    request: CreateChatSessionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat session with optional document associations"""
    try:
        # Validate document IDs if provided
        if request.document_ids:
            for doc_id in request.document_ids:
                document = await DocumentService.get_document_by_id(db, doc_id)
                if not document:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Document with ID {doc_id} not found"
                    )
                if document.processing_status != ProcessingStatus.INDEXED:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Document '{document.original_filename}' is not ready (status: {document.processing_status})"
                    )
        
        # Create the session
        session = await ChatService.create_session(
            db,
            title=request.title,
            document_ids=request.document_ids
        )

        # Commit the transaction to save the session and document associations
        await db.commit()

        return ChatSessionResponse(
            id=session.id,
            session_uuid=session.session_uuid,
            title=session.title,
            session_type=session.session_type,
            created_at=session.created_at,
            last_activity=session.last_activity,
            model_provider_used=session.model_provider_used,
            total_messages=session.total_messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all chat sessions with pagination"""
    try:
        sessions = await ChatService.get_recent_sessions(db, limit=limit)
        
        return [
            ChatSessionResponse(
                id=session.id,
                session_uuid=session.session_uuid,
                title=session.title,
                session_type=session.session_type,
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

@router.get("/sessions/{session_uuid}", response_model=ChatSessionWithDocumentsResponse)
async def get_chat_session_with_documents(
    session_uuid: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific chat session with its associated documents"""
    try:
        session = await ChatService.get_session_by_uuid(db, session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Get associated documents
        documents = await ChatService.get_session_documents(db, session.id)
        
        document_responses = [
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
        
        return ChatSessionWithDocumentsResponse(
            id=session.id,
            session_uuid=session.session_uuid,
            title=session.title,
            session_type=session.session_type,
            created_at=session.created_at,
            last_activity=session.last_activity,
            model_provider_used=session.model_provider_used,
            total_messages=session.total_messages,
            documents=document_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat session {session_uuid}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat session")

@router.put("/sessions/{session_uuid}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_uuid: str,
    request: UpdateChatSessionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a chat session (title and/or document associations)"""
    try:
        # Get the session
        session = await ChatService.get_session_by_uuid(db, session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Update title if provided
        if request.title is not None:
            await ChatService.update_session_title(db, session_uuid, request.title)
        
        # Update document associations if provided
        if request.document_ids is not None:
            # Validate document IDs
            for doc_id in request.document_ids:
                document = await DocumentService.get_document_by_id(db, doc_id)
                if not document:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Document with ID {doc_id} not found"
                    )
            
            # Get current documents
            current_documents = await ChatService.get_session_documents(db, session.id)
            current_doc_ids = {doc.id for doc in current_documents}
            new_doc_ids = set(request.document_ids)
            
            # Add new documents
            docs_to_add = new_doc_ids - current_doc_ids
            if docs_to_add:
                await ChatService.add_documents_to_session(db, session.id, list(docs_to_add))
            
            # Remove documents no longer needed
            docs_to_remove = current_doc_ids - new_doc_ids
            if docs_to_remove:
                await ChatService.remove_documents_from_session(db, session.id, list(docs_to_remove))

        # Commit the changes
        await db.commit()

        # Get updated session
        updated_session = await ChatService.get_session_by_uuid(db, session_uuid)
        
        return ChatSessionResponse(
            id=updated_session.id,
            session_uuid=updated_session.session_uuid,
            title=updated_session.title,
            session_type=updated_session.session_type,
            created_at=updated_session.created_at,
            last_activity=updated_session.last_activity,
            model_provider_used=updated_session.model_provider_used,
            total_messages=updated_session.total_messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chat session {session_uuid}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update chat session")

@router.delete("/sessions/{session_uuid}")
async def delete_chat_session(
    session_uuid: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a chat session and all its related data"""
    try:
        # Get the session with relationships loaded
        result = await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.session_uuid == session_uuid)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Delete the session - cascades will handle related records
        await db.delete(session)
        await db.commit()
        
        return {"message": f"Chat session {session_uuid} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting chat session {session_uuid}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete chat session")
    
# Below API was not able to delete the Last Chat Session because of foreign key constraint.   
    
# /// async def delete_chat_session(
#     session_uuid: str,
#     db: AsyncSession = Depends(get_db_session)
# ):
#     """Delete a chat session and all its messages"""
#     try:
#         success = await ChatService.delete_session(db, session_uuid)
#         if not success:
#             raise HTTPException(status_code=404, detail="Chat session not found")
        
#         return {"message": "Chat session deleted successfully"}
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error deleting chat session {session_uuid}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Failed to delete chat session")
# ///



@router.get("/sessions/{session_uuid}/documents", response_model=List[DocumentResponse])
async def get_session_documents(
    session_uuid: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get all documents associated with a chat session"""
    try:
        session = await ChatService.get_session_by_uuid(db, session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        documents = await ChatService.get_session_documents(db, session.id)
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching documents for session {session_uuid}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch session documents")

@router.get("/available-documents", response_model=List[DocumentResponse])
async def get_available_documents(
    db: AsyncSession = Depends(get_db_session)
):
    """Get all available documents that can be added to chat sessions"""
    try:
        documents = await DocumentService.get_all_documents(db, limit=100)
        
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
        logger.error(f"Error fetching available documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch available documents")

from pydantic import BaseModel
from typing import Optional

class SaveMessageRequest(BaseModel):
    message_content: str
    response_content: Optional[str] = None
    model_provider: Optional[str] = None
    token_count: Optional[int] = None
    processing_time_ms: Optional[int] = None

@router.post("/sessions/{session_uuid}/messages")
async def save_chat_message(
    session_uuid: str,
    request: SaveMessageRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Save a chat message to the database"""
    try:
        # Get the session
        session = await ChatService.get_session_by_uuid(db, session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Convert model_provider string to enum if provided
        provider_enum = None
        if request.model_provider:
            try:
                from app.database.models import ModelProvider
                provider_enum = ModelProvider(request.model_provider.lower())
            except ValueError:
                logger.warning(f"Invalid model provider: {request.model_provider}")

        # Save the message
        message = await ChatService.add_message(
            db,
            session_id=session.id,
            message_content=request.message_content,
            response_content=request.response_content,
            model_provider=provider_enum,
            token_count=request.token_count,
            processing_time_ms=request.processing_time_ms
        )

        await db.commit()

        return {
            "id": message.id,
            "session_id": message.session_id,
            "message_content": message.message_content,
            "response_content": message.response_content,
            "timestamp": message.timestamp,
            "model_provider": message.model_provider.value if message.model_provider else None,
            "token_count": message.token_count,
            "processing_time_ms": message.processing_time_ms
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving chat message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save chat message")

@router.get("/sessions/{session_uuid}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_uuid: str,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Get chat messages for a session"""
    try:
        # Get the session
        session = await ChatService.get_session_by_uuid(db, session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Get messages
        messages = await ChatService.get_session_messages(db, session.id, limit=limit, offset=offset)

        return [
            ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                message_content=msg.message_content,
                response_content=msg.response_content,
                timestamp=msg.timestamp,
                model_provider=msg.model_provider,
                token_count=msg.token_count,
                processing_time_ms=msg.processing_time_ms
            )
            for msg in messages
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get chat messages")
