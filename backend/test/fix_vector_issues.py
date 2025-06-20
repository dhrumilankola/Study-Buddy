#!/usr/bin/env python3
"""
Fix vector database and document management issues
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database.connection import get_db_session_context
from app.database.services import DocumentService, ChatService
from app.services.vector_store import EnhancedVectorStoreService
from app.services.document_processor import EnhancedDocumentProcessor
from app.services.rag_service import EnhancedRAGService
from app.database.models import Document, ChatSession, ProcessingStatus
from app.models.schemas import Document as SchemaDocument
from sqlalchemy import select, func
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clean_orphaned_chunks():
    """Remove all orphaned chunks from vector store"""
    print("=" * 60)
    print("CLEANING ORPHANED CHUNKS")
    print("=" * 60)
    
    vector_service = EnhancedVectorStoreService()
    
    try:
        # Initialize vector store
        if vector_service._vector_store is None:
            vector_service._initialize_vector_store()
        
        collection = vector_service._vector_store._collection
        
        # Get all chunks
        all_results = collection.get()
        
        if not all_results or 'metadatas' not in all_results:
            print("No chunks found in vector store")
            return
        
        # Get all valid document UUIDs from database
        async with get_db_session_context() as db:
            documents = await DocumentService.get_all_documents(db, limit=100)
            valid_uuids = {doc.uuid_filename for doc in documents}
        
        print(f"Found {len(all_results['ids'])} chunks in vector store")
        print(f"Found {len(valid_uuids)} valid document UUIDs in database")
        
        # Identify chunks to remove
        chunks_to_remove = []
        
        for i, metadata in enumerate(all_results['metadatas']):
            chunk_id = all_results['ids'][i]
            
            # Check if chunk has valid uuid_filename
            if not metadata or 'uuid_filename' not in metadata:
                chunks_to_remove.append(chunk_id)
            elif metadata['uuid_filename'] not in valid_uuids:
                chunks_to_remove.append(chunk_id)
        
        print(f"Identified {len(chunks_to_remove)} orphaned chunks to remove")
        
        if chunks_to_remove:
            # Remove orphaned chunks
            collection.delete(ids=chunks_to_remove)
            print(f"Removed {len(chunks_to_remove)} orphaned chunks")
            
            # Persist changes
            if hasattr(vector_service._vector_store, "_persist"):
                vector_service._vector_store._persist()
        else:
            print("No orphaned chunks found")
            
    except Exception as e:
        print(f"Error cleaning orphaned chunks: {e}")
        raise

async def reprocess_documents():
    """Reprocess all documents with correct metadata format"""
    print("\n" + "=" * 60)
    print("REPROCESSING DOCUMENTS")
    print("=" * 60)
    
    rag_service = EnhancedRAGService()
    
    async with get_db_session_context() as db:
        try:
            # Get all documents
            documents = await DocumentService.get_all_documents(db, limit=100)
            print(f"Found {len(documents)} documents to reprocess")
            
            for doc in documents:
                print(f"\nProcessing: {doc.original_filename}")
                
                # Check if file exists
                file_path = os.path.join(settings.UPLOAD_DIR, doc.uuid_filename)
                if not os.path.exists(file_path):
                    print(f"  File not found: {file_path}")
                    continue
                
                # Create schema document for processing
                schema_document = SchemaDocument(
                    id=str(doc.id),
                    filename=doc.original_filename,
                    uuid_filename=doc.uuid_filename,  # Include uuid_filename for proper metadata
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    upload_date=doc.created_at,
                    processed=False
                )
                
                try:
                    # Reset document status
                    await DocumentService.update_document_status(db, doc.id, ProcessingStatus.PROCESSING)
                    
                    # Process document with correct metadata
                    success = await rag_service.process_document(schema_document, file_path)
                    
                    if success:
                        # Update status and chunk count
                        chunk_count = await rag_service.vector_store_service.get_document_chunk_count(doc.uuid_filename)
                        await DocumentService.update_document_status(db, doc.id, ProcessingStatus.INDEXED)
                        await DocumentService.update_document_chunks(db, doc.id, chunk_count)
                        print(f"  Successfully processed: {chunk_count} chunks")
                    else:
                        await DocumentService.update_document_status(db, doc.id, ProcessingStatus.ERROR)
                        print(f"  Failed to process document")
                        
                except Exception as e:
                    print(f"  Error processing {doc.original_filename}: {e}")
                    await DocumentService.update_document_status(db, doc.id, ProcessingStatus.ERROR)
            
            await db.commit()
            print("\nDocument reprocessing complete")
            
        except Exception as e:
            print(f"Error reprocessing documents: {e}")
            await db.rollback()
            raise

async def verify_fixes():
    """Verify that the fixes worked correctly"""
    print("\n" + "=" * 60)
    print("VERIFYING FIXES")
    print("=" * 60)
    
    vector_service = EnhancedVectorStoreService()
    
    # Check vector store status
    try:
        total_chunks = await vector_service.get_document_count()
        print(f"Total chunks in vector store: {total_chunks}")
    except Exception as e:
        print(f"Error checking vector store: {e}")
    
    # Check database documents
    async with get_db_session_context() as db:
        try:
            documents = await DocumentService.get_all_documents(db, limit=100)
            total_db_chunks = sum(doc.chunk_count for doc in documents if doc.processing_status == ProcessingStatus.INDEXED)
            
            print(f"Total documents in database: {len(documents)}")
            print(f"Total chunks in database: {total_db_chunks}")
            print(f"Chunk count consistency: {'✓' if total_chunks == total_db_chunks else '✗'}")
            
            # Check for proper metadata format
            if vector_service._vector_store is None:
                vector_service._initialize_vector_store()
            
            collection = vector_service._vector_store._collection
            sample_results = collection.get(limit=3)
            
            if sample_results and 'metadatas' in sample_results:
                print("\nSample chunk metadata (checking for uuid_filename):")
                for i, metadata in enumerate(sample_results['metadatas'][:3]):
                    has_uuid = 'uuid_filename' in metadata if metadata else False
                    print(f"  Chunk {i+1}: {'✓' if has_uuid else '✗'} uuid_filename present")
                    if metadata and has_uuid:
                        print(f"    UUID: {metadata['uuid_filename']}")
            
        except Exception as e:
            print(f"Error verifying fixes: {e}")

async def main():
    """Main function to fix all vector database issues"""
    print("Starting vector database issue fixes...")
    
    try:
        # Step 1: Clean orphaned chunks
        await clean_orphaned_chunks()
        
        # Step 2: Reprocess documents with correct metadata
        await reprocess_documents()
        
        # Step 3: Verify fixes
        await verify_fixes()
        
        print("\n" + "=" * 60)
        print("ALL FIXES COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during fix process: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
