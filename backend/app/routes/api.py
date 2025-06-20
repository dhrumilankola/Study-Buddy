from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import os
import uuid
from datetime import datetime
import aiofiles
import asyncio
import json
from app.models.schemas import Document, QueryRequest, LLMConfig
from app.services.rag_service import EnhancedRAGService
from app.config import settings
from app.utils.auth import create_hume_client_token, verify_hume_access_token
from app.services.evi_config import get_or_create_study_buddy_config
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
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # Update file size
        document.file_size = len(content)

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # Add to background processing
        background_tasks.add_task(process_document_background, document, file_path)

        return {
            "id": document.id,
            "filename": document.filename,
            "status": "uploaded",
            "message": "Document uploaded and queued for processing"
        }
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )

@router.get("/documents/")
async def list_documents():
    """Get list of uploaded documents"""
    try:
        documents_info = rag_service.get_documents_info()
        return {
            "documents": documents_info,
            "total": len(documents_info)
        }
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )

@router.post("/query/")
async def query_documents(request: QueryRequest):
    """Query documents using RAG"""
    try:
        # Use streaming response for real-time results
        async def generate_response():
            try:
                async for chunk in rag_service.query_documents_stream(
                    question=request.question,
                    context_window=request.context_window or settings.DEFAULT_CONTEXT_WINDOW,
                    model_provider=request.model_provider or settings.DEFAULT_MODEL_PROVIDER,
                    llm_config=request.llm_config
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                error_chunk = {
                    "type": "error",
                    "content": str(e)
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"

        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error querying documents: {str(e)}"
        )

@router.get("/status")
async def get_status():
    """Get system status"""
    try:
        documents_info = rag_service.get_documents_info()
        return {
            "status": "healthy",
            "documents_in_vector_store": len(documents_info),
            "uploaded_files_count": len([f for f in os.listdir(settings.UPLOAD_DIR) if os.path.isfile(os.path.join(settings.UPLOAD_DIR, f))]) if os.path.exists(settings.UPLOAD_DIR) else 0,
            "embedding_model": settings.EMBEDDINGS_MODEL,
            "llm_model": {
                "default_provider": settings.DEFAULT_MODEL_PROVIDER,
                "ollama_model": settings.OLLAMA_MODEL,
                "gemini_model": settings.GEMINI_MODEL
            },
            "timestamp": datetime.now(),
            "hume_configured": bool(settings.HUME_API_KEY)
        }
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting status: {str(e)}"
        )

# Hume EVI Authentication Endpoints

@router.get("/auth/hume-token")
async def get_hume_token():
    """Generate access token for Hume EVI authentication"""
    if not settings.HUME_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Hume AI is not configured. Please contact administrator."
        )
    
    try:
        # Create secure client token for frontend
        token_data = create_hume_client_token()
        
        # Get or create Study Buddy EVI configuration
        config_id = await get_or_create_study_buddy_config()
        
        return {
            **token_data,
            "config_id": config_id,
            "hostname": "api.hume.ai"
        }
    except Exception as e:
        logger.error(f"Error generating Hume token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Hume authentication token: {str(e)}"
        )

# Voice Chat RAG Integration

@router.post("/voice/query")
async def voice_rag_query(request: Dict[str, Any]):
    """
    Process voice transcription through RAG system
    This endpoint receives transcriptions from voice chat and returns RAG responses
    """
    try:
        transcription = request.get("transcription", "").strip()
        if not transcription:
            raise HTTPException(status_code=400, detail="No transcription provided")
        
        # Create QueryRequest from voice input
        query_request = QueryRequest(
            question=transcription,
            context_window=5,  # Optimal for voice responses
            model_provider=settings.DEFAULT_MODEL_PROVIDER
        )
        
        # Get RAG response
        response_chunks = []
        async for chunk in rag_service.query_documents_stream(
            question=query_request.question,
            context_window=query_request.context_window,
            model_provider=query_request.model_provider
        ):
            response_chunks.append(chunk)
        
        # Combine chunks into final response
        full_response = ""
        sources = []
        
        for chunk in response_chunks:
            if chunk.get("type") == "content":
                full_response += chunk.get("content", "")
            elif chunk.get("type") == "sources":
                sources = chunk.get("sources", [])
        
        # Format response for voice (concise but informative)
        formatted_response = format_response_for_voice(full_response, sources)
        
        return {
            "success": True,
            "response": formatted_response,
            "sources": sources,
            "original_transcription": transcription
        }
        
    except Exception as e:
        logger.error(f"Error processing voice RAG query: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "response": "I'm sorry, I encountered an error while searching your documents. Please try again."
        }

def format_response_for_voice(response: str, sources: List[Dict]) -> str:
    """
    Format RAG response for voice delivery
    - Keep it conversational
    - Include source mentions naturally
    - Ensure it flows well when spoken
    """
    if not response:
        return "I couldn't find relevant information in your documents for that question."
    
    # Add source mentions naturally in voice format
    if sources:
        source_names = [source.get("filename", "document") for source in sources[:2]]  # Limit to 2 for voice
        if len(source_names) == 1:
            source_mention = f"Based on your {source_names[0]}, "
        else:
            source_mention = f"Based on your documents {' and '.join(source_names)}, "
        
        # Insert source mention naturally
        response = source_mention + response.lower()
    
    return response

# Document Management Endpoints (existing)

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    try:
        success = await rag_service.delete_document(document_id)
        if success:
            return {"message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )

@router.post("/model/switch")
async def switch_model(request: Dict[str, Any]):
    """Switch between model providers (Ollama/Gemini)"""
    try:
        provider = request.get("provider")
        if provider not in ["ollama", "gemini"]:
            raise HTTPException(status_code=400, detail="Invalid provider. Use 'ollama' or 'gemini'")
        
        # Update the default provider
        settings.DEFAULT_MODEL_PROVIDER = provider
        
        return {
            "message": f"Switched to {provider} provider",
            "current_provider": provider
        }
    except Exception as e:
        logger.error(f"Error switching model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error switching model: {str(e)}"
        )
        
@router.websocket("/ws/voice-rag")
async def websocket_voice_rag(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice RAG integration
    Receives voice transcriptions and sends back RAG responses
    """
    await websocket.accept()
    logger.info("Voice RAG WebSocket connection established")
    
    try:
        while True:
            # Receive message from frontend
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "transcription":
                # Process voice transcription through RAG
                transcription = message.get("text", "").strip()
                
                if transcription:
                    logger.info(f"Processing voice transcription: {transcription}")
                    
                    try:
                        # Send acknowledgment
                        await websocket.send_text(json.dumps({
                            "type": "processing",
                            "message": "Searching your documents..."
                        }))
                        
                        # Process through RAG
                        query_request = QueryRequest(
                            question=transcription,
                            context_window=5,
                            model_provider=settings.DEFAULT_MODEL_PROVIDER
                        )
                        
                        response_chunks = []
                        async for chunk in rag_service.query_documents_stream(
                            question=query_request.question,
                            context_window=query_request.context_window,
                            model_provider=query_request.model_provider
                        ):
                            response_chunks.append(chunk)
                        
                        # Combine response
                        full_response = ""
                        sources = []
                        
                        for chunk in response_chunks:
                            if chunk.get("type") == "content":
                                full_response += chunk.get("content", "")
                            elif chunk.get("type") == "sources":
                                sources = chunk.get("sources", [])
                        
                        # Format for voice and send response
                        formatted_response = format_response_for_voice(full_response, sources)
                        
                        await websocket.send_text(json.dumps({
                            "type": "rag_response",
                            "response": formatted_response,
                            "sources": sources,
                            "original_question": transcription
                        }))
                        
                    except Exception as e:
                        logger.error(f"Error processing voice transcription: {str(e)}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Sorry, I encountered an error while searching your documents."
                        }))
                
            elif message_type == "ping":
                # Health check
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
                
    except WebSocketDisconnect:
        logger.info("Voice RAG WebSocket disconnected")
    except Exception as e:
        logger.error(f"Voice RAG WebSocket error: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass