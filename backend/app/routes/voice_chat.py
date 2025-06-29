from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging
import os

from app.database.connection import get_db_session
from app.database.services import DocumentService, ChatService
from app.database.models import ProcessingStatus
from app.services.elevenlabs_service import elevenlabs_service
from app.models.schemas import (
    CreateChatSessionRequest,
    ChatSessionResponse,
    VoiceChatConfigResponse
)
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/start-session", response_model=ChatSessionResponse)
async def start_voice_chat_session(
    request: CreateChatSessionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Create voice chat session and configure ElevenLabs agent"""
    try:
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

        session = await ChatService.create_session(
            db,
            title=request.title or "Voice Chat",
            document_ids=request.document_ids,
            session_type='voice'
        )

        await db.commit()

        if request.document_ids:
            docs = await ChatService.get_session_documents(db, session.id)
            file_paths = [doc.uuid_filename for doc in docs]

            doc_ids = await elevenlabs_service.upload_documents_to_kb(file_paths)
            
            success = await elevenlabs_service.attach_documents_to_agent(doc_ids)
            if not success:
                logger.warning("Failed to attach documents to ElevenLabs agent")

            session.session_metadata = {'elevenlabs_doc_ids': doc_ids}
            await db.commit()

        await db.refresh(session)
        return ChatSessionResponse.from_orm(session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting voice chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to start voice session")

@router.post("/end-session/{session_uuid}")
async def end_voice_chat_session(
    session_uuid: str,
    db: AsyncSession = Depends(get_db_session)
):
    """End voice chat session and cleanup ElevenLabs resources"""
    try:
        session = await ChatService.get_session_by_uuid(db, session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await elevenlabs_service.clear_agent_knowledge_base()

        if session.session_metadata and 'elevenlabs_doc_ids' in session.session_metadata:
            doc_ids = session.session_metadata['elevenlabs_doc_ids']
            await elevenlabs_service.delete_documents_from_kb(doc_ids)

        return {"status": "success", "message": "Voice session ended successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending voice chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to end voice session")

@router.get("/config", response_model=VoiceChatConfigResponse)
async def get_voice_chat_config():
    """Get ElevenLabs configuration for frontend"""
    try:
        if not settings.ELEVENLABS_API_KEY or not settings.AGENT_ID:
            raise HTTPException(
                status_code=503, 
                detail="Voice chat service not configured"
            )
        
        return VoiceChatConfigResponse(
            api_key=settings.ELEVENLABS_API_KEY,
            agent_id=settings.AGENT_ID
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice chat config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get voice chat configuration")