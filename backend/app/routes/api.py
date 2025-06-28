# --- Standard Library Imports ---
import os
import uuid
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Annotated

# --- Third-Party Imports ---
import aiofiles
from fastapi import (
    APIRouter, UploadFile, File, HTTPException, Depends, 
    BackgroundTasks, Query, WebSocket, WebSocketDisconnect
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

# --- Application-Specific Imports ---
from app.config import settings
from app.database.connection import get_db_session, get_db_session_context
from app.database.models import Document as DBDocument, ProcessingStatus as DBProcessingStatus
from app.database.services import DocumentService
from app.models.schemas import QueryRequest, LLMConfig
from app.routes import database, chat_management
from app.services.evi_config import get_or_create_study_buddy_config
from app.services.rag_service import EnhancedRAGService
from app.utils.auth import create_hume_client_token

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

router = APIRouter()
rag_service = EnhancedRAGService()

# Include database and chat management routes from the 'main' branch logic
router.include_router(database.router, prefix="/db", tags=["database"])
router.include_router(chat_management.router, prefix="/chat", tags=["chat-management"])


# -----------------------------------------------------------------------------
# Background Document Processing
# -----------------------------------------------------------------------------

async def process_document_background(db_document: DBDocument, file_path: str):
    """Background task to process a document after upload, with database status updates."""
    try:
        # Update status to PROCESSING
        async with get_db_session_context() as db:
            await DocumentService.update_document_status(
                db, db_document.id, DBProcessingStatus.PROCESSING
            )
            await db.commit()

        # Process the document using the RAG service
        success = await rag_service.process_document(db_document, file_path)

        # Update final status in the database
        async with get_db_session_context() as db:
            new_status = DBProcessingStatus.INDEXED if success else DBProcessingStatus.ERROR
            await DocumentService.update_document_status(db, db_document.id, new_status)

            if success:
                chunk_count = await rag_service.vector_store_service.get_document_chunk_count(
                    db_document.uuid_filename
                )
                await DocumentService.update_document_chunks(db, db_document.id, chunk_count)

            await db.commit()
        logger.info(f"Background processing complete for {db_document.original_filename}: {'Success' if success else 'Failed'}")

    except Exception as e:
        logger.error(f"Error in background processing for {db_document.original_filename}: {str(e)}")
        try:
            async with get_db_session_context() as db:
                await DocumentService.update_document_status(
                    db, db_document.id, DBProcessingStatus.ERROR
                )
                await db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status to ERROR: {str(db_error)}")


# -----------------------------------------------------------------------------
# Document Management Endpoints
# -----------------------------------------------------------------------------

@router.post("/documents/")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """Upload and process a document with database integration."""
    try:
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Unsupported file type. Allowed: {settings.ALLOWED_EXTENSIONS}")

        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(400, f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024*1024)}MB")

        uuid_filename = str(uuid.uuid4())
        db_document = await DocumentService.create_document(
            db,
            original_filename=file.filename,
            file_type=file_extension[1:],
            file_size=len(content),
            uuid_filename=uuid_filename,
            metadata={"upload_source": "api"}
        )

        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, f"{uuid_filename}{file_extension}")
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(content)
        
        await db.commit()
        background_tasks.add_task(process_document_background, db_document, file_path)

        return {
            "status": "success",
            "message": "File uploaded. Processing in background.",
            "document": {
                "id": db_document.id,
                "uuid_filename": db_document.uuid_filename,
                "original_filename": db_document.original_filename,
                "processing_status": db_document.processing_status.value,
            }
        }
    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        await db.rollback()
        raise HTTPException(500, f"Error uploading document: {str(e)}")


@router.get("/documents/")
async def list_documents(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """List all documents from the database."""
    try:
        documents = await DocumentService.get_all_documents(db, limit=limit, offset=offset)
        return [{
            "id": doc.id,
            "original_filename": doc.original_filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "processing_status": doc.processing_status.value,
            "created_at": doc.created_at.isoformat(),
            "chunk_count": doc.chunk_count,
            # Legacy fields for frontend compatibility
            "filename": f"{doc.uuid_filename}.{doc.file_type}",
            "processed": doc.processing_status == DBProcessingStatus.INDEXED
        } for doc in documents]
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(500, "Error listing documents")


@router.get("/documents/{document_id}")
async def get_document(document_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get a specific document by its database ID."""
    document = await DocumentService.get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(404, f"Document with ID {document_id} not found")
    return document


@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db_session)):
    """Delete a document, its file, and its vector store entries."""
    try:
        document = await DocumentService.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(404, f"Document with ID {document_id} not found")

        # Delete physical file
        file_path = os.path.join(settings.UPLOAD_DIR, f"{document.uuid_filename}.{document.file_type}")
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete from vector store
        await rag_service.vector_store_service.delete_by_metadata({"document_id": str(document.id)})
        
        # Delete from database
        await DocumentService.delete_document(db, document_id)
        await db.commit()

        return {"status": "success", "message": f"Document '{document.original_filename}' deleted."}
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(500, "Error processing delete request")


# -----------------------------------------------------------------------------
# RAG Query and System Status Endpoints
# -----------------------------------------------------------------------------

@router.post("/query/")
async def query_documents(
    query: QueryRequest,
    session_uuid: Optional[str] = Query(None, description="Chat session UUID for document context")
):
    """Query documents and get an AI response, with optional session context."""
    try:
        if query.context_window is not None:
            query.context_window = max(1, min(query.context_window, settings.MAX_CONTEXT_WINDOW))

        logger.info(f"Query for session '{session_uuid}': '{query.question}'")
        
        async def response_generator():
            async for chunk in rag_service.generate_response(query, session_uuid=session_uuid):
                yield chunk
        
        return StreamingResponse(response_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}")
        raise HTTPException(500, "Error querying documents")


@router.get("/status", response_model=Dict[str, Any])
async def get_status(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get system status, including database and model info.
    """
    try:
        doc_count = await DocumentService.get_documents_count(db)
        providers_available = {
            "ollama": rag_service.ollama_model is not None,
            "gemini": rag_service.gemini_model is not None and settings.GOOGLE_API_KEY is not None
        }
        model_info = {
            "name": settings.GEMINI_MODEL if rag_service.current_provider == "gemini" else settings.OLLAMA_MODEL,
            "provider": rag_service.current_provider,
        }
        return {
            "status": "healthy",
            "documents_in_db": doc_count,
            "embedding_model": settings.EMBEDDINGS_MODEL,
            "llm_model": model_info,
            "providers_available": providers_available,
            "hume_configured": bool(settings.HUME_API_KEY and settings.HUME_SECRET_KEY),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(500, "Error checking status")


@router.post("/model/switch")
async def switch_model(model_config: LLMConfig):
    """Switch between available model providers (Ollama/Gemini)."""
    try:
        rag_service.set_provider(model_config.provider.value)
        logger.info(f"Switched model provider to: {model_config.provider.value}")
        return {
            "status": "success",
            "message": f"Successfully switched to {model_config.provider.value}",
            "current_provider": rag_service.current_provider
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error switching model: {str(e)}")
        raise HTTPException(500, "Error switching model")


# -----------------------------------------------------------------------------
# Hume EVI and Voice RAG Endpoints
# -----------------------------------------------------------------------------

@router.get("/auth/hume-token", response_model=Dict[str, Any])
async def get_hume_token(db: AsyncSession = Depends(get_db_session)):
    """
    Get a short-lived Hume client token and EVI configuration
    """
    token_data = await create_hume_client_token()
    return token_data


def format_response_for_voice(response: str, sources: List[Dict]) -> str:
    """Formats a RAG response for natural-sounding voice delivery."""
    if not response:
        return "I couldn't find relevant information in your documents for that question."
    if sources:
        source_names = [s.get("filename", "your document") for s in sources[:1]]
        source_mention = f"Based on {source_names[0]}, "
        return source_mention + response
    return response


@router.websocket("/ws/voice-rag")
async def websocket_voice_rag(
    websocket: WebSocket,
    session_uuid: Optional[str] = Query(None)
):
    """WebSocket for real-time voice RAG, aware of the chat session."""
    await websocket.accept()
    logger.info(f"Voice RAG WebSocket connected for session: {session_uuid}")
    try:
        last_transcription = None  # Track the last processed transcript to avoid duplicates
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "transcription" and message.get("text", "").strip():
                transcription = message["text"].strip()

                # Skip if identical to the last transcription received (helps with repeated interim duplicates)
                if transcription == last_transcription:
                    continue
                last_transcription = transcription

                logger.info(f"Processing transcription '{transcription}' for session '{session_uuid}'")
                
                await websocket.send_text(json.dumps({"type": "processing"}))
                
                try:
                    query = QueryRequest(question=transcription)
                    full_response, sources = "", []
                    
                    async for chunk in rag_service.generate_response(query, session_uuid):
                        # The RAG generator yields SSE-formatted strings ("data: {...}\n\n").
                        # Convert them to dicts for easier handling.
                        if isinstance(chunk, str):
                            if chunk.startswith("data:"):
                                try:
                                    chunk_json = json.loads(chunk[5:].strip())
                                except json.JSONDecodeError:
                                    continue  # skip malformed chunk
                            else:
                                continue  # Not an SSE data line
                        elif isinstance(chunk, dict):
                            chunk_json = chunk
                        else:
                            continue

                        if chunk_json.get("type") in {"response", "content"}:
                            # Older versions used "content"; newer uses "response"
                            full_response += chunk_json.get("content", "") or chunk_json.get("response", "")
                        elif chunk_json.get("type") == "sources":
                            sources = chunk_json.get("sources", [])

                    formatted_response = format_response_for_voice(full_response, sources)
                    
                    await websocket.send_text(json.dumps({
                        "type": "rag_response",
                        "response": formatted_response,
                    }))
                except Exception as e:
                    logger.error(f"Error in RAG processing for WebSocket: {e}")
                    await websocket.send_text(json.dumps({"type": "error"}))
            
    except WebSocketDisconnect:
        logger.info(f"Voice RAG WebSocket disconnected for session: {session_uuid}")
    except Exception as e:
        logger.error(f"Voice RAG WebSocket error for session {session_uuid}: {e}")
        await websocket.close(code=1011)
