#!/usr/bin/env python3
"""
Migration script to move existing file-based data to PostgreSQL database.
This script will scan the uploads directory and create database records for existing documents.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database.connection import AsyncSessionLocal, init_database
from app.database.services import DocumentService
from app.database.models import ProcessingStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scan_upload_directory() -> List[Dict[str, Any]]:
    """Scan the upload directory for existing files"""
    upload_dir = Path(settings.UPLOAD_DIR)
    
    if not upload_dir.exists():
        logger.warning(f"Upload directory does not exist: {upload_dir}")
        return []
    
    files_info = []
    
    for file_path in upload_dir.iterdir():
        if file_path.is_file():
            try:
                stat = file_path.stat()
                file_info = {
                    'original_filename': file_path.name,
                    'uuid_filename': file_path.stem,  # Assuming UUID is the stem
                    'file_type': file_path.suffix[1:] if file_path.suffix else 'unknown',
                    'file_size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime),
                    'file_path': str(file_path)
                }
                files_info.append(file_info)
                logger.info(f"Found file: {file_path.name} ({file_info['file_size']} bytes)")
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
    
    return files_info

async def check_vector_store_status(uuid_filename: str) -> tuple[ProcessingStatus, int, List[str]]:
    """Check if a document exists in the vector store and get its status"""
    try:
        # Import here to avoid circular imports and handle missing dependencies
        from app.services.rag_service import EnhancedRAGService

        # Try to initialize RAG service - this might fail if Ollama is not available
        try:
            rag_service = EnhancedRAGService()

            # Check if document has any chunks in vector store
            # This is a simplified check - you might need to adapt based on your vector store implementation
            try:
                doc_count = await rag_service.vector_store_service.get_document_count()

                if doc_count > 0:
                    return ProcessingStatus.INDEXED, doc_count, []
                else:
                    return ProcessingStatus.PROCESSING, 0, []

            except Exception as e:
                logger.debug(f"Could not check vector store for {uuid_filename}: {str(e)}")
                return ProcessingStatus.PROCESSING, 0, []

        except Exception as rag_error:
            logger.warning(f"RAG service not available (this is OK for migration): {str(rag_error)}")
            # If RAG service is not available, assume documents need processing
            return ProcessingStatus.PROCESSING, 0, []

    except ImportError as e:
        logger.warning(f"Could not import RAG service (this is OK for migration): {str(e)}")
        return ProcessingStatus.PROCESSING, 0, []
    except Exception as e:
        logger.debug(f"Error checking vector store status: {str(e)}")
        return ProcessingStatus.PROCESSING, 0, []

async def migrate_file_to_database(session, file_info: Dict[str, Any]) -> bool:
    """Migrate a single file's information to the database"""
    try:
        # Check if document already exists in database
        existing_doc = await DocumentService.get_document_by_uuid(
            session, file_info['uuid_filename']
        )
        
        if existing_doc:
            logger.info(f"Document {file_info['original_filename']} already exists in database")
            return True
        
        # Check vector store status
        status, chunk_count, vector_ids = await check_vector_store_status(file_info['uuid_filename'])
        
        # Create document record
        document = await DocumentService.create_document(
            session=session,
            original_filename=file_info['original_filename'],
            file_type=file_info['file_type'],
            file_size=file_info['file_size'],
            uuid_filename=file_info['uuid_filename'],
            metadata={
                'migrated_from_file': True,
                'original_path': file_info['file_path'],
                'migration_date': datetime.utcnow().isoformat()
            }
        )
        
        # Update status if processed
        if status != ProcessingStatus.PROCESSING:
            await DocumentService.update_document_status(
                session=session,
                document_id=document.id,
                status=status,
                chunk_count=chunk_count,
                vector_store_ids=vector_ids
            )
        
        logger.info(f"✅ Migrated: {file_info['original_filename']} (ID: {document.id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to migrate {file_info['original_filename']}: {str(e)}")
        return False

async def migrate_all_files():
    """Main migration function"""
    logger.info("Starting migration of existing files to database...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Scan upload directory
        files_info = await scan_upload_directory()
        
        if not files_info:
            logger.info("No files found to migrate")
            return
        
        logger.info(f"Found {len(files_info)} files to migrate")
        
        # Migrate files
        success_count = 0
        failed_count = 0
        
        async with AsyncSessionLocal() as session:
            for file_info in files_info:
                try:
                    success = await migrate_file_to_database(session, file_info)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        
                    # Commit after each file to avoid losing progress
                    await session.commit()
                    
                except Exception as e:
                    logger.error(f"Error migrating file: {str(e)}")
                    await session.rollback()
                    failed_count += 1
        
        # Summary
        logger.info("=" * 50)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total files found: {len(files_info)}")
        logger.info(f"Successfully migrated: {success_count}")
        logger.info(f"Failed migrations: {failed_count}")
        
        if success_count > 0:
            logger.info("✅ Migration completed successfully!")
        else:
            logger.warning("⚠️  No files were migrated")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

async def verify_migration():
    """Verify the migration by checking database records"""
    logger.info("Verifying migration...")
    
    try:
        async with AsyncSessionLocal() as session:
            documents = await DocumentService.get_all_documents(session, limit=100)
            
            logger.info(f"Found {len(documents)} documents in database:")
            
            for doc in documents:
                logger.info(f"  - {doc.original_filename} ({doc.processing_status}) - {doc.file_size} bytes")
                
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")

async def main():
    """Main function"""
    logger.info("Study Buddy Data Migration Tool")
    logger.info("=" * 40)
    
    try:
        # Run migration
        await migrate_all_files()
        
        # Verify results
        await verify_migration()
        
        logger.info("Migration process completed!")
        
    except Exception as e:
        logger.error(f"Migration process failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
