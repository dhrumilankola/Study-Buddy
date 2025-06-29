import asyncio
import logging
from typing import List, Dict, Any
import aiofiles
import aiohttp
import os
from app.config import settings

logger = logging.getLogger(__name__)

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html",
    ".epub": "application/epub+zip",
}

class ElevenLabsService:
    def __init__(self):
        if not settings.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY not configured")
        if not settings.AGENT_ID:
            raise ValueError("ELEVENLABS_AGENT_ID not configured")
        
        self.api_key = settings.ELEVENLABS_API_KEY
        self.agent_id = settings.AGENT_ID
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def upload_documents_to_kb(self, file_paths: List[str]) -> List[str]:
        """Upload documents to ElevenLabs workspace knowledge base"""
        doc_ids = []
        
        async with aiohttp.ClientSession() as session:
            for file_path in file_paths:
                try:
                    # Resolve to absolute path
                    absolute_file_path = os.path.join(settings.UPLOAD_DIR, file_path)
                    
                    async with aiofiles.open(absolute_file_path, 'rb') as f:
                        file_content = await f.read()
                        
                    data = aiohttp.FormData()
                    file_ext = os.path.splitext(file_path)[1].lower()
                    content_type = MIME_TYPES.get(file_ext, 'application/octet-stream')

                    data.add_field(
                        'file', 
                        file_content, 
                        filename=os.path.basename(file_path),
                        content_type=content_type
                    )
                    
                    headers = {"xi-api-key": self.api_key}
                    
                    async with session.post(
                        f"https://api.elevenlabs.io/v1/convai/knowledge-base/file", 
                        data=data, 
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            doc_ids.append(result.get('document_id'))
                            logger.info(f"Uploaded {file_path} to ElevenLabs KB")
                        else:
                            error_text = await response.text()
                            logger.error(f"Failed to upload {file_path}: {error_text}")
                            raise Exception(f"Upload failed: {error_text}")
                            
                except Exception as e:
                    logger.error(f"Error uploading {file_path}: {e}")
                    raise
                    
        return doc_ids

    async def attach_documents_to_agent(self, doc_ids: List[str]) -> bool:
        """Attach documents to the conversation agent"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "knowledge_base": {
                        "documents": [{"id": doc_id} for doc_id in doc_ids]
                    }
                }
                
                async with session.patch(
                    f"{self.base_url}/convai/agents/{self.agent_id}",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        logger.info(f"Attached {len(doc_ids)} documents to agent")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to attach documents: {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error attaching documents to agent: {e}")
            return False

    async def clear_agent_knowledge_base(self) -> bool:
        """Clear all documents from agent knowledge base"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "knowledge_base": {
                        "documents": []
                    }
                }
                
                async with session.patch(
                    f"{self.base_url}/convai/agents/{self.agent_id}",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        logger.info("Cleared agent knowledge base")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to clear knowledge base: {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error clearing agent knowledge base: {e}")
            return False

    async def delete_documents_from_kb(self, doc_ids: List[str]) -> bool:
        """Delete documents from workspace knowledge base"""
        try:
            async with aiohttp.ClientSession() as session:
                for doc_id in doc_ids:
                    async with session.delete(
                        f"{self.base_url}/knowledge-base/documents/{doc_id}",
                        headers={"xi-api-key": self.api_key}
                    ) as response:
                        if response.status == 200:
                            logger.info(f"Deleted document {doc_id}")
                        else:
                            logger.warning(f"Failed to delete document {doc_id}")
                            
                return True
                
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False

elevenlabs_service = ElevenLabsService()