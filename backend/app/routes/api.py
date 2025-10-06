from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import os
import uuid
from datetime import datetime
import aiofiles
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import Document, QueryRequest, LLMConfig, DocumentResponse, ProcessingStatus
from app.database.models import Document as DBDocument, ProcessingStatus as DBProcessingStatus
from app.database.services import DocumentService
from app.database.connection import get_db_session
from app.services.rag_service import EnhancedRAGService
from app.config import settings
from app.routes import database, chat_management, voice_chat
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
rag_service = EnhancedRAGService()

router.include_router(database.router, prefix="/db", tags=["database"])
router.include_router(chat_management.router, prefix="/chat", tags=["chat-management"])
router.include_router(voice_chat.router, prefix="/voice-chat", tags=["voice-chat"])

async def process_document_background(db_document: DBDocument, file_path: str):
    """Background task to process document after upload with database status updates"""
    from app.database.connection import get_db_session_context

    try:
        async with get_db_session_context() as db:
            await DocumentService.update_document_status(
                db, db_document.id, DBProcessingStatus.PROCESSING
            )
            await db.commit()

        schema_document = Document(
            id=str(db_document.id),
            filename=db_document.original_filename,
            uuid_filename=db_document.uuid_filename,
            file_type=db_document.file_type,
            file_size=db_document.file_size,
            upload_date=db_document.created_at,
            processed=False
        )

        success = await rag_service.process_document(schema_document, file_path)

        async with get_db_session_context() as db:
            new_status = DBProcessingStatus.INDEXED if success else DBProcessingStatus.ERROR
            await DocumentService.update_document_status(db, db_document.id, new_status)

            if success:
                chunk_count = await rag_service.vector_store_service.get_document_chunk_count(
                    db_document.uuid_filename
                )
                await DocumentService.update_document_status(
                    db, db_document.id, DBProcessingStatus.INDEXED, chunk_count
                )

            await db.commit()

    except Exception as e:
        logger.error(f"Error processing document {db_document.id}: {str(e)}")
        async with get_db_session_context() as db:
            await DocumentService.update_document_status(
                db, db_document.id, DBProcessingStatus.ERROR
            )
            await db.commit()

@router.post("/documents/", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """Upload and process a document with database integration"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}"
        )

    try:
        uuid_filename_base = str(uuid.uuid4())
        uuid_filename = f"{uuid_filename_base}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, uuid_filename)

        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            if len(content) > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes"
                )
            await f.write(content)

        db_document = await DocumentService.create_document(
            db,
            original_filename=file.filename,
            uuid_filename=uuid_filename,
            file_type=file_extension[1:],
            file_size=len(content)
        )

        await db.commit()

        background_tasks.add_task(process_document_background, db_document, file_path)

        return DocumentResponse(
            id=db_document.id,
            original_filename=db_document.original_filename,
            uuid_filename=db_document.uuid_filename,
            file_type=db_document.file_type,
            processing_status=db_document.processing_status,
            created_at=db_document.created_at,
            updated_at=db_document.updated_at,
            file_size=db_document.file_size,
            chunk_count=db_document.chunk_count,
            document_metadata=db_document.document_metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail="Error uploading document")

@router.get("/documents/", response_model=List[DocumentResponse])
async def list_documents(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """List all documents with pagination"""
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
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Error listing documents")

@router.post("/query/")
async def query_documents_endpoint(
    request: QueryRequest,
    session_uuid: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    """Query documents with session-based filtering"""
    try:
        return StreamingResponse(
            rag_service.query_documents_streaming(
                question=request.query,
                context_window=request.context_window,
                model_provider=request.model_provider,
                session_uuid=session_uuid,
                db=db
            ),
            media_type="text/plain"
        )
    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing query")

@router.post("/model/switch")
async def switch_model_provider(model_config: LLMConfig):
    """Switch the active model provider"""
    try:
        if model_config.provider.value == "gemini":
            if not rag_service.gemini_model:
                raise HTTPException(
                    status_code=400,
                    detail="Gemini model is not available. Please check your API key configuration."
                )
        elif model_config.provider.value == "ollama":
            if not rag_service.ollama_model:
                raise HTTPException(
                    status_code=400,
                    detail="Ollama model is not available. Please check your Ollama installation."
                )
            
        rag_service.current_provider = model_config.provider.value
        
        logger.info(f"Switched model provider to: {model_config.provider.value}")
        
        return {
            "status": "success",
            "message": f"Successfully switched to {model_config.provider.value}",
            "current_provider": rag_service.current_provider
        }
    except Exception as e:
        logger.error(f"Error switching model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error switching model: {str(e)}"
        )
        
@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db_session)):
    """Delete a document and its vector store entries with database integration"""
    try:
        document = await DocumentService.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {document_id} not found"
            )

        file_path = os.path.join(settings.UPLOAD_DIR, document.uuid_filename)

        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Removed file {file_path}")
        else:
            logger.warning(f"File not found: {file_path}")

        await rag_service.vector_store_service.delete_document(document.uuid_filename)

        success = await DocumentService.delete_document(db, document_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete document from database")

        await db.commit()

        return {"message": f"Document {document.original_filename} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting document")

@router.get("/status")
async def get_status():
    """Get application status"""
    return {
        "status": "running",
        "model_provider": rag_service.current_provider,
        "timestamp": datetime.utcnow().isoformat()    }