from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import os
import uuid
from datetime import datetime
import aiofiles
import asyncio
import json # Added for parsing RAG response
from app.models.schemas import Document, QueryRequest, LLMConfig
from app.services.rag_service import EnhancedRAGService
from app.config import settings
import logging
from hume.client import HumeClient, AsyncHumeClient
# Remove TranscriptionConfig as it's not used for EVI based on current understanding
# from hume.models.config import TranscriptionConfig
from hume.models.messages import UserInputMessage, AudioOutput, SessionInfoMessage, AssistantMessage, ErrorMessage # Added EVI message types

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

@router.get("/generate-hume-token")
async def generate_hume_token():
    """Generate a Hume API access token"""
    if not settings.HUME_API_KEY or not settings.HUME_SECRET_KEY:
        logger.error("Hume API key or secret key not configured.")
        raise HTTPException(
            status_code=500,
            detail="Hume API credentials are not configured on the server."
        )

    try:
        client = HumeClient(api_key=settings.HUME_API_KEY)
        # The new SDK does not use get_access_token; you may need to adjust this logic based on your use case.
        # For now, just return a success message if the client is created.
        return {"status": "success", "message": "HumeClient initialized."}
    except Exception as e:
        logger.error(f"Error generating Hume token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Hume client: {str(e)}"
        )

@router.websocket("/ws/voice-chat")
async def websocket_voice_chat(client_ws: WebSocket):
    await client_ws.accept()
    logger.info("Client WebSocket connection accepted.")

    if not settings.HUME_API_KEY:
        logger.error("Hume API key not configured for WebSocket.")
        await client_ws.close(code=1008, reason="HUME_API_KEY is not configured on the server.")
        return

    evi_client = AsyncHumeClient(api_key=settings.HUME_API_KEY)

    # Use a placeholder for config_id if you support multiple EVI configurations later
    # For now, using default or None
    config_id: Optional[str] = None
    # If you have a specific EVI config ID, you can set it here:
    # config_id = "your-evi-config-id"


    try:
        async with evi_client.connect(config_id=config_id) as session:
            logger.info(f"Connected to Hume EVI session (config_id: {config_id if config_id else 'default'}).")
            await client_ws.send_text(json.dumps({"type": "system", "message": "Connected to Hume EVI."}))

            async def client_to_hume_task():
                """Receives audio from client and forwards to Hume EVI."""
                try:
                    while True:
                        data = await client_ws.receive()
                        if "bytes" in data:
                            audio_bytes = data["bytes"]
                            logger.debug(f"Received {len(audio_bytes)} audio bytes from client. Sending to Hume EVI.")
                            await session.send_audio_input(audio_bytes)
                        elif "text" in data:
                            text_data = data["text"]
                            logger.info(f"Received text from client: {text_data}. (Note: EVI primarily expects audio input or specific commands)")
                            # Potentially handle text commands to EVI if your EVI config supports them
                            # For now, we log it. If it's a start/stop signal, implement here.
                            # Example: if json.loads(text_data).get("command") == "stop_session":
                            #    await session.close()
                            #    break
                except WebSocketDisconnect:
                    logger.info("Client WebSocket disconnected.")
                except Exception as e:
                    logger.error(f"Error in client_to_hume_task: {e}", exc_info=True)
                finally:
                    logger.info("client_to_hume_task finished.")
                    # Consider closing EVI session if client disconnects abruptly
                    if not session.is_closed:
                         await session.close()


            async def hume_to_client_and_rag_task():
                """Receives messages from Hume EVI, processes transcriptions with RAG, and forwards audio to client."""
                try:
                    async for message in session.stream_output():
                        if message.get('type') == 'user_input':
                            user_input = message.message.message
                            logger.info(f"Hume EVI UserInputMessage (transcription): {user_input}")

                            if not user_input or user_input.strip() == "":
                                logger.info("Received empty transcription, skipping RAG.")
                                continue

                            await client_ws.send_text(json.dumps({"type": "transcription", "text": user_input}))

                            full_rag_response = ""
                            try:
                                logger.info(f"Sending to RAG: '{user_input}'")
                                async for rag_chunk_str in rag_service.generate_response(QueryRequest(question=user_input, context_window=settings.DEFAULT_CONTEXT_WINDOW)):
                                    if rag_chunk_str.startswith("data: "):
                                        data_json_str = rag_chunk_str[len("data: "):].strip()
                                        try:
                                            data_json = json.loads(data_json_str)
                                            if data_json.get("type") == "response":
                                                chunk_content = data_json.get("content", "")
                                                full_rag_response += chunk_content
                                                # Optionally send RAG chunks to client for real-time display
                                                # await client_ws.send_text(json.dumps({"type": "rag_chunk", "content": chunk_content}))
                                            elif data_json.get("type") == "sources":
                                                # Optionally send sources to client
                                                # await client_ws.send_text(json.dumps({"type": "rag_sources", "sources": data_json.get("sources")}))
                                                pass
                                            elif data_json.get("type") == "done":
                                                logger.info("RAG processing done.")
                                                break
                                        except json.JSONDecodeError:
                                            logger.error(f"Failed to parse RAG JSON chunk: {data_json_str}")
                                    elif "DONE" in rag_chunk_str: # Check for explicit DONE message if not JSON
                                        logger.info("RAG processing explicitly done.")
                                        break

                                logger.info(f"Full RAG response: {full_rag_response}")
                                if full_rag_response.strip():
                                    await client_ws.send_text(json.dumps({"type": "rag_response", "text": full_rag_response}))
                                    logger.info(f"Sending full RAG response to Hume EVI for synthesis: {full_rag_response}")
                                    await session.send_custom_assistant_message(full_rag_response)
                                else:
                                    logger.info("RAG response was empty. Not sending to EVI for synthesis.")
                                    # Optionally send a default message or silence if EVI expects a response
                                    # await session.send_custom_assistant_message("I don't have a response for that.")

                            except Exception as e:
                                logger.error(f"Error during RAG processing or sending to EVI: {e}", exc_info=True)
                                await client_ws.send_text(json.dumps({"type": "error", "source": "rag", "message": str(e)}))


                        elif message.get('type') == 'audio_output':
                            audio_bytes = message.data
                            logger.debug(f"Hume EVI AudioOutput: {len(audio_bytes)} bytes. Forwarding to client.")
                            await client_ws.send_bytes(audio_bytes)

                        elif message.get('type') == 'assistant':
                             logger.info(f"Hume EVI AssistantMessage: {message.model_dump_json()}")
                             # This might contain text from EVI's own LLM if not using send_custom_assistant_message
                             # Or could be other control messages.

                        elif message.get('type') == 'session_info':
                            logger.info(f"Hume EVI SessionInfoMessage: {message.type}, {message.message}")
                            # e.g. session_started, session_ended
                            await client_ws.send_text(json.dumps({"type": "system", "sub_type": message.type, "message": message.message}))


                        elif message.get('type') == 'error':
                            logger.error(f"Hume EVI ErrorMessage: {message.error} - {message.message} (Code: {message.code})")
                            await client_ws.send_text(json.dumps({"type": "error", "source": "hume_evi", "code": message.code, "message": message.message, "details": message.error}))

                        else:
                            logger.debug(f"Received other message type from Hume EVI: {type(message)}")

                except WebSocketDisconnect:
                    logger.info("Hume EVI WebSocket seems to have disconnected (client disconnected earlier or EVI ended session).")
                except Exception as e:
                    logger.error(f"Error in hume_to_client_and_rag_task: {e}", exc_info=True)
                    if client_ws.client_state == client_ws.client_state.CONNECTED: # type: ignore
                         await client_ws.send_text(json.dumps({"type": "error", "source": "hume_handler", "message": str(e)}))
                finally:
                    logger.info("hume_to_client_and_rag_task finished.")
                    if not client_ws.client_state == client_ws.client_state.DISCONNECTED: # type: ignore
                        await client_ws.close(code=1000, reason="Hume EVI session ended or error.")

            # Run both tasks concurrently
            # If one task finishes (e.g., client disconnects), the other should ideally be cancelled or stop.
            # asyncio.gather will wait for both to complete. If one raises an exception, gather will raise it.
            done, pending = await asyncio.wait(
                [client_to_hume_task(), hume_to_client_and_rag_task()],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel() # Request cancellation of still pending tasks

            for task in done: # Check for exceptions in completed tasks
                try:
                    task.result()
                except Exception as e:
                    logger.error(f"Task completed with error: {e}", exc_info=True)


    except WebSocketDisconnect:
        logger.info("Client WebSocket disconnected before Hume EVI session could start or during setup.")
    except Exception as e:
        logger.error(f"Overall WebSocket voice chat error: {e}", exc_info=True)
        if client_ws.client_state == client_ws.client_state.CONNECTED: # type: ignore
            await client_ws.close(code=1011, reason=f"Server error: {str(e)}")
    finally:
        logger.info("WebSocket voice_chat endpoint handler finished.")
        if client_ws.client_state == client_ws.client_state.CONNECTED: # type: ignore
             await client_ws.close(code=1000, reason="Session normally ended.")