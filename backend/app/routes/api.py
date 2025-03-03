from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import os
import uuid
from datetime import datetime
import aiofiles
import asyncio
from app.models.schemas import Document, QueryRequest, LLMConfig
from app.services.rag_service import EnhancedRAGService
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
rag_service = EnhancedRAGService()

async def process_document_background(document: Document, file_path: str):
    """Background task to process document after upload"""
    try:
        success = await rag_service.process_document(document, file_path)
        logger.info(f"Background processing complete for {document.filename}: {'Success' if success else 'Failed'}")
    except Exception as e:
        logger.error(f"Error in background processing for {document.filename}: {str(e)}")

@router.post("/documents/")
async def upload_documents(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload and process a document with background processing"""
    try:
        # Validate file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        # Create document record
        doc_id = str(uuid.uuid4())
        document = Document(
            id=doc_id,
            filename=file.filename,
            file_type=file_extension[1:],
            file_size=0,
            upload_date=datetime.now(),
            processed=False
        )

        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # Save file
        file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}{file_extension}")
        content = await file.read()
        
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE/(1024*1024)}MB"
            )
        
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(content)
            document.file_size = len(content)
            logger.info(f"File saved: {file_path}")

        # Schedule background processing to avoid blocking
        background_tasks.add_task(process_document_background, document, file_path)

        return {
            "status": "success",
            "message": "File uploaded successfully. Processing in background.",
            "document": {
                "id": document.id,
                "filename": document.filename,
                "size": document.file_size,
                "processed": False
            }
        }

    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )

@router.get("/documents/")
async def list_documents():
    """List all documents with enhanced metadata"""
    try:
        # Get list of files in upload directory
        files = []
        for filename in os.listdir(settings.UPLOAD_DIR):
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                # Get file stats
                file_stats = os.stat(file_path)
                
                # Determine if processed by checking vector store
                is_processed = False
                try:
                    # Extract the document ID from the filename
                    doc_id = os.path.splitext(filename)[0]
                    # Check if document exists in vector store using metadata filter
                    doc_count = await rag_service.vector_store_service.get_document_count()
                    is_processed = doc_count > 0
                except Exception:
                    # If checking vector store fails, assume not processed
                    is_processed = False
                
                files.append({
                    "id": os.path.splitext(filename)[0],
                    "filename": filename,
                    "size": file_stats.st_size,
                    "upload_date": datetime.fromtimestamp(file_stats.st_ctime),
                    "processed": is_processed,
                    "file_type": os.path.splitext(filename)[1][1:] if os.path.splitext(filename)[1] else ""
                })
        return sorted(files, key=lambda x: x['upload_date'], reverse=True)
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )

@router.post("/query/")
async def query_documents(query: QueryRequest):
    """Query processed documents and get AI response with enhanced parameters"""
    try:
        # Validate context window size
        if query.context_window is not None:
            if query.context_window < 1:
                query.context_window = 1
            elif query.context_window > settings.MAX_CONTEXT_WINDOW:
                query.context_window = settings.MAX_CONTEXT_WINDOW
        
        # Log query details
        logger.info(f"Received query: '{query.question}' with context window: {query.context_window}")
        
        # Generate response stream
        response_generator = rag_service.generate_response(query)
        
        return StreamingResponse(
            response_generator,
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
            
        # Get model information
        model_info = {
            "name": settings.OLLAMA_MODEL,
            "provider": rag_service.current_provider,
            "temperature": settings.MODEL_TEMPERATURE,
            "max_tokens": settings.MODEL_MAX_TOKENS
        }

        return {
            "status": "healthy",
            "documents_in_vector_store": doc_count,
            "uploaded_files_count": len(uploaded_files),
            "embedding_model": embedding_model,
            "llm_model": model_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking status: {str(e)}"
        )
        
@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a document and its vector store entries with enhanced cleaning"""
    try:
        # Construct file path
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Document {filename} not found"
            )
            
        # Delete the file
        try:
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
        except OSError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting file: {str(e)}"
            )
            
        # Delete from vector store
        try:
            # Filter documents with matching filename in metadata
            await rag_service.vector_store_service.delete_by_metadata({"filename": filename})
            logger.info(f"Removed document from vector store: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up vector store: {str(e)}")
            # Don't raise error here as file is already deleted
            
        return {
            "status": "success",
            "message": f"Document {filename} deleted successfully"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error processing delete request: {str(e)}")
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