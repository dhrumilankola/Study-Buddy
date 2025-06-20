#!/usr/bin/env python3
"""
Reprocess documents that are in error status
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
from app.database.services import DocumentService
from app.services.rag_service import EnhancedRAGService
from app.database.models import ProcessingStatus
from app.models.schemas import Document as SchemaDocument
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reprocess_error_documents():
    """Reprocess all documents that are in error status"""
    print("=" * 60)
    print("REPROCESSING ERROR DOCUMENTS")
    print("=" * 60)
    
    rag_service = EnhancedRAGService()
    
    async with get_db_session_context() as db:
        try:
            # Get all documents
            documents = await DocumentService.get_all_documents(db, limit=100)
            
            # Filter documents that need reprocessing (error status or indexed with 0 chunks)
            docs_to_process = []
            for doc in documents:
                if (doc.processing_status == ProcessingStatus.ERROR or 
                    (doc.processing_status == ProcessingStatus.INDEXED and doc.chunk_count == 0)):
                    docs_to_process.append(doc)
            
            print(f"Found {len(docs_to_process)} documents to reprocess")
            
            for doc in docs_to_process:
                print(f"\nProcessing: {doc.original_filename} (ID: {doc.id})")
                
                # Check if file exists
                file_path = os.path.join(settings.UPLOAD_DIR, f"{doc.uuid_filename}.{doc.file_type}")
                if not os.path.exists(file_path):
                    print(f"  File not found: {file_path}")
                    continue
                
                # Create schema document for processing
                schema_document = SchemaDocument(
                    id=str(doc.id),  # Use database ID as string
                    filename=doc.original_filename,
                    uuid_filename=doc.uuid_filename,  # Include uuid_filename for metadata
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    upload_date=doc.created_at,
                    processed=False
                )
                
                try:
                    # Reset document status to processing
                    await DocumentService.update_document_status(db, doc.id, ProcessingStatus.PROCESSING)
                    print(f"  Status set to PROCESSING")
                    
                    # Process document with correct metadata
                    success = await rag_service.process_document(schema_document, file_path)
                    
                    if success:
                        # Update status and chunk count
                        chunk_count = await rag_service.vector_store_service.get_document_chunk_count(doc.uuid_filename)
                        await DocumentService.update_document_status(db, doc.id, ProcessingStatus.INDEXED)
                        await DocumentService.update_document_chunks(db, doc.id, chunk_count)
                        print(f"  ✓ Successfully processed: {chunk_count} chunks")
                    else:
                        await DocumentService.update_document_status(db, doc.id, ProcessingStatus.ERROR)
                        print(f"  ✗ Failed to process document")
                        
                except Exception as e:
                    print(f"  ✗ Error processing {doc.original_filename}: {e}")
                    await DocumentService.update_document_status(db, doc.id, ProcessingStatus.ERROR)
            
            await db.commit()
            print(f"\nReprocessing complete!")
            
        except Exception as e:
            print(f"Error reprocessing documents: {e}")
            await db.rollback()
            raise

async def main():
    """Main function"""
    try:
        await reprocess_error_documents()
        print("\n" + "=" * 60)
        print("REPROCESSING COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during reprocessing: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
