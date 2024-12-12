from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List
import os
import uuid
from datetime import datetime
import aiofiles
from app.models.schemas import Document, Query, ModelConfig, ModelStatus
from app.services.rag_service import RAGService
from app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()
rag_service = RAGService()

@router.post("/documents/")
async def upload_documents(file: UploadFile = File(...)):
    """Upload and process a document"""
    try:
        logger.info(f"Processing upload for file: {file.filename}")
        # Validate file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.pdf', '.txt', '.pptx', '.ipynb']:
            logger.warning(f"Unsupported file type attempted: {file_extension}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}"
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

        # Save file
        file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}{file_extension}")
        content = await file.read()
        
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(content)
            document.file_size = len(content)
            logger.info(f"File saved successfully: {file_path}")

        try:
            # Process document
            logger.info(f"Starting document processing for {document.filename}")
            success = await rag_service.process_document(document, file_path)
            if success:
                document.processed = True
                logger.info(f"Document processed successfully: {document.filename}")
            else:
                logger.error(f"Document processing failed: {document.filename}")

            return {
                "status": "success" if document.processed else "error",
                "message": "File uploaded and processed successfully" if document.processed else "File uploaded but processing failed",
                "document": {
                    "id": document.id,
                    "filename": document.filename,
                    "size": document.file_size,
                    "processed": document.processed
                }
            }

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}", exc_info=True)
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file: {str(e)}"
            )

    except Exception as e:
        logger.error(f"Error in upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )

@router.get("/documents/")
async def list_documents():
    """List all processed documents"""
    try:
        # Get list of files in upload directory
        files = []
        for filename in os.listdir(settings.UPLOAD_DIR):
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                files.append({
                    "filename": filename,
                    "size": os.path.getsize(file_path),
                    "upload_date": datetime.fromtimestamp(os.path.getctime(file_path))
                })
        return files
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )

@router.post("/model/switch")
async def switch_model(config: ModelConfig):
    """Switch between model providers"""
    try:
        success = rag_service.switch_provider(config.provider)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to switch to provider: {config.provider}"
            )
            
        return {
            "status": "success",
            "message": f"Switched to {config.provider} provider",
            "config": config
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error switching model provider: {str(e)}"
        )

@router.post("/query/")
async def query_documents(query: Query):
    """Query processed documents and get AI response"""
    try:
        logger.info(f"Received query: {query.question}")
        logger.debug(f"Context window size: {query.context_window}")
        
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
        logger.error(f"Error in query_documents: {str(e)}", exc_info=True)
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
    """Check system status including current model configuration"""
    try:
        # Get vector store statistics
        doc_count = 0
        if rag_service.vector_store_service._vector_store:
            doc_count = len(rag_service.vector_store_service._vector_store.get())
        
        # Get current model info
        current_provider = rag_service.current_provider
        model_name = (
            settings.GEMINI_MODEL 
            if current_provider == "gemini" 
            else settings.OLLAMA_MODEL
        )
        
        # Check if Gemini is available
        gemini_available = bool(settings.GOOGLE_API_KEY)
        
        return {
            "status": "healthy",
            "current_provider": current_provider,
            "model_name": model_name,
            "temperature": settings.MODEL_TEMPERATURE,
            "documents_indexed": doc_count,
            "providers_available": {
                "ollama": True,  # Assuming Ollama is always available locally
                "gemini": gemini_available
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking status: {str(e)}"
        )
        
@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a document and its vector store entries"""
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
        except OSError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting file: {str(e)}"
            )
            
        # Delete from vector store if it exists
        try:
            if rag_service.vector_store_service._vector_store:
                # Filter documents with matching filename in metadata
                docs = rag_service.vector_store_service._vector_store.get(
                    where={"filename": filename}
                )
                if docs:
                    # Delete matching documents from vector store
                    rag_service.vector_store_service._vector_store.delete(
                        where={"filename": filename}
                    )
        except Exception as e:
            print(f"Error cleaning up vector store: {str(e)}")
            # Don't raise error here as file is already deleted
            
        return {
            "status": "success",
            "message": f"Document {filename} deleted successfully"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing delete request: {str(e)}"
        )