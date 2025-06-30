from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from app.database.models import Document, ChatSession, ChatMessage, ProcessingStatus, ModelProvider, SessionType

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for document-related database operations"""
    
    @staticmethod
    async def create_document(
        session: AsyncSession,
        original_filename: str,
        uuid_filename: str,
        file_type: str,
        file_size: int
    ) -> Document:
        """Create a new document record"""
        document = Document(
            original_filename=original_filename,
            uuid_filename=uuid_filename,
            file_type=file_type,
            file_size=file_size,
            processing_status=ProcessingStatus.PROCESSING
        )
        
        session.add(document)
        await session.flush()
        logger.info(f"Created document: {original_filename} with UUID: {uuid_filename}")
        return document
    
    @staticmethod
    async def get_document_by_id(session: AsyncSession, document_id: int) -> Optional[Document]:
        """Get document by ID"""
        result = await session.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_documents(session: AsyncSession, limit: int = 100, offset: int = 0) -> List[Document]:
        """Get all documents with pagination"""
        result = await session.execute(
            select(Document)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_document_status(
        session: AsyncSession,
        document_id: int,
        status: ProcessingStatus,
        chunk_count: Optional[int] = None
    ) -> bool:
        """Update document processing status"""
        update_values = {"processing_status": status}
        if chunk_count is not None:
            update_values["chunk_count"] = chunk_count
            
        result = await session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(**update_values)
        )
        
        success = result.rowcount > 0
        if success:
            logger.info(f"Updated document {document_id} status to {status}")
        return success
    
    @staticmethod
    async def delete_document(session: AsyncSession, document_id: int) -> bool:
        """Delete a document record and its associations"""
        # First, retrieve the document with its chat session relationships
        result = await session.execute(
            select(Document).options(selectinload(Document.chat_sessions)).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            logger.warning(f"Attempted to delete non-existent document with ID {document_id}")
            return False

        # Manually clear the many-to-many relationship
        document.chat_sessions.clear()
        
        # Now, delete the document itself
        await session.delete(document)
        
        logger.info(f"Deleted document {document_id} and its associations")
        return True

class ChatService:
    """Service for chat-related database operations"""
    
    @staticmethod
    async def create_session(
        session: AsyncSession,
        session_uuid: Optional[str] = None,
        title: Optional[str] = None,
        document_ids: Optional[List[int]] = None,
        session_type: str = 'text'
    ) -> ChatSession:
        """Create a new chat session with optional document associations"""
        if session_uuid is None:
            session_uuid = str(uuid.uuid4())

        session_type_enum = SessionType.VOICE if session_type == 'voice' else SessionType.TEXT

        chat_session = ChatSession(
            session_uuid=session_uuid, 
            title=title,
            session_type=session_type_enum
        )
        session.add(chat_session)
        await session.flush()

        if document_ids:
            await ChatService.add_documents_to_session(session, chat_session.id, document_ids)

        logger.info(f"Created {session_type} chat session: {chat_session.session_uuid} with {len(document_ids or [])} documents")
        return chat_session
    
    @staticmethod
    async def get_session_by_uuid(session: AsyncSession, session_uuid: str) -> Optional[ChatSession]:
        """Get chat session by UUID"""
        result = await session.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.session_uuid == session_uuid)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_recent_sessions(session: AsyncSession, limit: int = 10) -> List[ChatSession]:
        """Get recent chat sessions"""
        result = await session.execute(
            select(ChatSession)
            .order_by(ChatSession.last_activity.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def add_message(
        session: AsyncSession,
        session_id: int,
        message_content: str,
        response_content: Optional[str] = None,
        model_provider: Optional[ModelProvider] = None,
        token_count: Optional[int] = None,
        processing_time_ms: Optional[int] = None
    ) -> ChatMessage:
        """Add a message to a chat session"""
        message = ChatMessage(
            session_id=session_id,
            message_content=message_content,
            response_content=response_content,
            model_provider=model_provider,
            token_count=token_count,
            processing_time_ms=processing_time_ms
        )
        
        session.add(message)
        
        await session.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(
                total_messages=ChatSession.total_messages + 1,
                last_activity=datetime.utcnow(),
                model_provider_used=model_provider
            )
        )
        
        await session.flush()
        logger.info(f"Added message to session {session_id}")
        return message
    
    @staticmethod
    async def get_session_messages(
        session: AsyncSession,
        session_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Get messages for a chat session"""
        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp.asc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    @staticmethod
    async def delete_session(session: AsyncSession, session_uuid: str) -> bool:
        """Delete a chat session and all its messages"""
        result = await session.execute(
            delete(ChatSession).where(ChatSession.session_uuid == session_uuid)
        )
        success = result.rowcount > 0
        if success:
            logger.info(f"Deleted session {session_uuid}")
        return success
    
    @staticmethod
    async def add_documents_to_session(
        session: AsyncSession,
        session_id: int,
        document_ids: List[int]
    ) -> bool:
        """Add documents to a chat session"""
        try:
            result = await session.execute(
                select(ChatSession)
                .options(selectinload(ChatSession.documents))
                .where(ChatSession.id == session_id)
            )
            chat_session = result.scalar_one_or_none()

            if not chat_session:
                logger.error(f"Chat session {session_id} not found")
                return False

            for doc_id in document_ids:
                doc_result = await session.execute(select(Document).where(Document.id == doc_id))
                document = doc_result.scalar_one_or_none()
                if document and document not in chat_session.documents:
                    chat_session.documents.append(document)

            await session.flush()
            logger.info(f"Added {len(document_ids)} documents to session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding documents to session: {str(e)}")
            return False

    @staticmethod
    async def remove_documents_from_session(
        session: AsyncSession,
        session_id: int,
        document_ids: List[int]
    ) -> bool:
        """Remove documents from a chat session"""
        try:
            result = await session.execute(
                select(ChatSession)
                .options(selectinload(ChatSession.documents))
                .where(ChatSession.id == session_id)
            )
            chat_session = result.scalar_one_or_none()

            if not chat_session:
                logger.error(f"Chat session {session_id} not found")
                return False

            documents_to_remove = [doc for doc in chat_session.documents if doc.id in document_ids]
            for document in documents_to_remove:
                chat_session.documents.remove(document)

            await session.flush()
            logger.info(f"Removed {len(documents_to_remove)} documents from session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing documents from session: {str(e)}")
            return False

    @staticmethod
    async def get_session_documents(session: AsyncSession, session_id: int) -> List[Document]:
        """Get all documents associated with a chat session"""
        try:
            result = await session.execute(
                select(ChatSession)
                .options(selectinload(ChatSession.documents))
                .where(ChatSession.id == session_id)
            )
            chat_session = result.scalar_one_or_none()

            if not chat_session:
                return []

            return chat_session.documents

        except Exception as e:
            logger.error(f"Error getting session documents: {str(e)}")
            return []

    @staticmethod
    async def update_session_title(
        session: AsyncSession,
        session_uuid: str,
        title: str
    ) -> bool:
        """Update the title of a chat session"""
        try:
            result = await session.execute(
                update(ChatSession)
                .where(ChatSession.session_uuid == session_uuid)
                .values(title=title, last_activity=datetime.utcnow())
            )

            success = result.rowcount > 0
            if success:
                logger.info(f"Updated session {session_uuid} title to: {title}")
            return success

        except Exception as e:
            logger.error(f"Error updating session title: {str(e)}")
            return False