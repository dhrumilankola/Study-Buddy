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
from app.routes import database, chat_management
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
rag_service = EnhancedRAGService()

# Include database routes
router.include_router(database.router, prefix="/db", tags=["database"])

# Include chat management routes
router.include_router(chat_management.router, prefix="/chat", tags=["chat-management"])

async def process_document_background(db_document: DBDocument, file_path: str):
    """Background task to process document after upload with database status updates"""
    from app.database.connection import get_db_session_context

    try:
        # Update status to processing
        async with get_db_session_context() as db:
            await DocumentService.update_document_status(
                db, db_document.id, DBProcessingStatus.PROCESSING
            )
            await db.commit()

        # Create schema document for RAG service
        schema_document = Document(
            id=str(db_document.id),  # Use database ID as string
            filename=db_document.original_filename,
            uuid_filename=db_document.uuid_filename,  # Include uuid_filename for metadata
            file_type=db_document.file_type,
            file_size=db_document.file_size,
            upload_date=db_document.created_at,
            processed=False
        )

        # Process document
        success = await rag_service.process_document(schema_document, file_path)

        # Update database status
        async with get_db_session_context() as db:
            new_status = DBProcessingStatus.INDEXED if success else DBProcessingStatus.ERROR
            await DocumentService.update_document_status(db, db_document.id, new_status)

            # Update chunk count if successful
            if success:
                # Get chunk count from vector store
                chunk_count = await rag_service.vector_store_service.get_document_chunk_count(
                    db_document.uuid_filename
                )
                await DocumentService.update_document_chunks(db, db_document.id, chunk_count)

            await db.commit()

        logger.info(f"Background processing complete for {db_document.original_filename}: {'Success' if success else 'Failed'}")

    except Exception as e:
        logger.error(f"Error in background processing for {db_document.original_filename}: {str(e)}")

        # Update status to error
        try:
            async with get_db_session_context() as db:
                await DocumentService.update_document_status(
                    db, db_document.id, DBProcessingStatus.ERROR
                )
                await db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status to error: {str(db_error)}")

@router.post("/documents/")
async def upload_documents(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """Upload and process a document with database integration and background processing"""
    try:
        # Validate file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        # Read file content first to get size
        content = await file.read()

        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE/(1024*1024)}MB"
            )

        # Generate UUID for file storage
        uuid_filename = str(uuid.uuid4())

        # Create document record in database
        db_document = await DocumentService.create_document(
            db,
            original_filename=file.filename,
            file_type=file_extension[1:],  # Remove the dot
            file_size=len(content),
            uuid_filename=uuid_filename,
            metadata={"upload_source": "api"}
        )

        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # Save file with UUID name
        file_path = os.path.join(settings.UPLOAD_DIR, f"{uuid_filename}{file_extension}")
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(content)
            logger.info(f"File saved: {file_path}")

        # Commit the database transaction
        await db.commit()

        # Schedule background processing
        background_tasks.add_task(process_document_background, db_document, file_path)

        return {
            "status": "success",
            "message": "File uploaded successfully. Processing in background.",
            "document": {
                "id": db_document.id,
                "uuid_filename": db_document.uuid_filename,
                "original_filename": db_document.original_filename,
                "file_type": db_document.file_type,
                "file_size": db_document.file_size,
                "processing_status": db_document.processing_status.value,
                "created_at": db_document.created_at.isoformat()
            }
        }

    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )

@router.get("/documents/")
async def list_documents(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """List all documents from database with enhanced metadata"""
    try:
        # Get documents from database
        documents = await DocumentService.get_all_documents(db, limit=limit, offset=offset)

        # Convert to response format
        document_list = []
        for doc in documents:
            document_list.append({
                "id": doc.id,
                "uuid_filename": doc.uuid_filename,
                "original_filename": doc.original_filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "processing_status": doc.processing_status.value,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
                "chunk_count": doc.chunk_count,
                "document_metadata": doc.document_metadata,
                # Legacy fields for frontend compatibility
                "filename": f"{doc.uuid_filename}.{doc.file_type}",
                "size": doc.file_size,
                "upload_date": doc.created_at.isoformat(),
                "processed": doc.processing_status == DBProcessingStatus.INDEXED
            })

        return document_list

    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )

@router.get("/documents/{document_id}")
async def get_document(document_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get a specific document by ID"""
    try:
        document = await DocumentService.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {document_id} not found"
            )

        return {
            "id": document.id,
            "uuid_filename": document.uuid_filename,
            "original_filename": document.original_filename,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "processing_status": document.processing_status.value,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
            "chunk_count": document.chunk_count,
            "document_metadata": document.document_metadata
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting document: {str(e)}"
        )

@router.get("/documents/{document_id}/status")
async def get_document_status(document_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get the processing status of a specific document"""
    try:
        document = await DocumentService.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {document_id} not found"
            )

        return {
            "id": document.id,
            "original_filename": document.original_filename,
            "processing_status": document.processing_status.value,
            "chunk_count": document.chunk_count,
            "updated_at": document.updated_at.isoformat()
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting document status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting document status: {str(e)}"
        )

@router.post("/query/")
async def query_documents(
    query: QueryRequest,
    session_uuid: Optional[str] = Query(None, description="Chat session UUID for document context filtering")
):
    """Query processed documents and get AI response with enhanced parameters and optional session context"""
    try:
        # Validate context window size
        if query.context_window is not None:
            if query.context_window < 1:
                query.context_window = 1
            elif query.context_window > settings.MAX_CONTEXT_WINDOW:
                query.context_window = settings.MAX_CONTEXT_WINDOW

        # Log query details
        logger.info(f"Received query: '{query.question}' with context window: {query.context_window}")
        if session_uuid:
            logger.info(f"Using session context: {session_uuid}")

        # Generate response stream
        async def response_generator():
            async for chunk in rag_service.generate_response(query, session_uuid=session_uuid):
                yield chunk

        return StreamingResponse(
            response_generator(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Check if the API and services are healthy"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
    
@router.get("/status")
async def check_status():
    """Check system status and document count with enhanced information"""
    try:
        # Get vector store statistics
        doc_count = 0
        try:
            doc_count = await rag_service.vector_store_service.get_document_count()
        except Exception as e:
            logger.error(f"Error getting vector store document count: {str(e)}")
        
        # Get embedding model info
        embedding_model = settings.EMBEDDINGS_MODEL
        
        # Check uploaded files
        upload_dir = settings.UPLOAD_DIR
        uploaded_files = []
        if os.path.exists(upload_dir):
            uploaded_files = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))]
            
        # Check available providers
        providers_available = {
            "ollama": rag_service.ollama_model is not None,
            "gemini": rag_service.gemini_model is not None and settings.GOOGLE_API_KEY is not None
        }
        
        # Get model information
        model_info = {
            "name": settings.GEMINI_MODEL if rag_service.current_provider == "gemini" else settings.OLLAMA_MODEL,
            "provider": rag_service.current_provider,
            "temperature": settings.MODEL_TEMPERATURE,
            "max_tokens": settings.MODEL_MAX_TOKENS
        }

        return {
            "status": "healthy",
            "documents_in_vector_store": doc_count,
            "documents_indexed": doc_count,  # Add alias for frontend compatibility
            "uploaded_files_count": len(uploaded_files),
            "embedding_model": embedding_model,
            "llm_model": model_info,
            "current_provider": rag_service.current_provider,
            "providers_available": providers_available,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking status: {str(e)}"
        )

@router.post("/test/gemini")
async def test_gemini():
    """Test Gemini API with minimal request"""
    try:
        if not rag_service.gemini_model:
            raise HTTPException(
                status_code=400,
                detail="Gemini model not available"
            )

        # Simple test without context
        from langchain_core.messages import HumanMessage

        # Very simple message
        messages = [HumanMessage(content="Hello")]

        # Test the model
        response = await rag_service.gemini_model.ainvoke(messages)

        return {
            "status": "success",
            "message": "Gemini API is working",
            "response": response.content[:100] + "..." if len(response.content) > 100 else response.content
        }

    except Exception as e:
        logger.error(f"Gemini test failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@router.post("/model/switch")
async def switch_model(model_config: LLMConfig):
    """Switch between different model providers (Ollama/Gemini)"""
    try:
        # Validate provider
        if model_config.provider.value not in ["ollama", "gemini"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid model provider. Must be either 'ollama' or 'gemini'"
            )
        
        # Check if the requested provider is available
        if model_config.provider.value == "gemini":
            if not rag_service.gemini_model or not settings.GOOGLE_API_KEY:
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
            
        # Update the current provider in the RAG service
        rag_service.current_provider = model_config.provider.value
        
        # Log the switch
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
        # Get document from database
        document = await DocumentService.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {document_id} not found"
            )

        # Construct file path using UUID filename
        file_path = os.path.join(settings.UPLOAD_DIR, f"{document.uuid_filename}.{document.file_type}")

        # Delete the physical file if it exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
            except OSError as e:
                logger.error(f"Error deleting file: {str(e)}")
                # Continue with database deletion even if file deletion fails
        else:
            logger.warning(f"Physical file not found: {file_path}")

        # Delete from vector store
        try:
            await rag_service.vector_store_service.delete_by_metadata({
                "uuid_filename": document.uuid_filename
            })
            logger.info(f"Removed document from vector store: {document.uuid_filename}")
        except Exception as e:
            logger.error(f"Error cleaning up vector store: {str(e)}")
            # Continue with database deletion even if vector store cleanup fails

        # Delete from database
        await DocumentService.delete_document(db, document_id)
        await db.commit()

        return {
            "status": "success",
            "message": f"Document '{document.original_filename}' deleted successfully"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error processing delete request: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing delete request: {str(e)}"
        )

# Legacy endpoint for backward compatibility
@router.delete("/documents/by-filename/{filename}")
async def delete_document_by_filename(filename: str, db: AsyncSession = Depends(get_db_session)):
    """Delete a document by filename (legacy endpoint for backward compatibility)"""
    try:
        # Extract UUID from filename (assuming format: uuid.extension)
        uuid_filename = os.path.splitext(filename)[0]

        # Find document by UUID filename
        document = await DocumentService.get_document_by_uuid_filename(db, uuid_filename)
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document {filename} not found"
            )

        # Use the main delete endpoint
        return await delete_document(document.id, db)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error processing legacy delete request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing delete request: {str(e)}"
        )

@router.get("/documents/{filename}/text")
async def get_document_text(filename: str):
    """Get the processed text of a document for debugging"""
    try:
        # Only allow in development mode
        if os.environ.get("ENVIRONMENT", "dev") != "dev":
            raise HTTPException(
                status_code=403,
                detail="This endpoint is only available in development mode"
            )
            
        # Check if file exists
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Document {filename} not found"
            )
            
        # Get document text
        file_extension = os.path.splitext(filename)[1].lower()
        
        # Process the document to extract text
        dummy_doc = Document(
            id="debug",
            filename=filename,
            file_type=file_extension[1:],
            file_size=0,
            upload_date=datetime.now(),
            processed=False
        )
        
        chunks = await rag_service.document_processor.process_document(dummy_doc, file_path)
        
        return {
            "filename": filename,
            "chunk_count": len(chunks),
            "chunks": [
                {
                    "chunk_index": chunk["metadata"]["chunk_index"],
                    "text": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"]
                }
                for chunk in chunks
            ]
        }
    except Exception as e:
        logger.error(f"Error getting document text: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting document text: {str(e)}"
        )