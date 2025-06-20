#!/usr/bin/env python3
"""
Simple migration script to move existing file-based data to PostgreSQL database.
This script only handles database operations and doesn't depend on RAG service.
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
                    'created_at': datetime.fromtimestamp(stat.st_mtime),  # Use mtime instead of ctime
                    'file_path': str(file_path)
                }
                files_info.append(file_info)
                logger.info(f"Found file: {file_path.name} ({file_info['file_size']} bytes)")
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
    
    return files_info

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
        
        # Create document record with PROCESSING status (can be updated later)
        document = await DocumentService.create_document(
            session=session,
            original_filename=file_info['original_filename'],
            file_type=file_info['file_type'],
            file_size=file_info['file_size'],
            uuid_filename=file_info['uuid_filename'],
            metadata={
                'migrated_from_file': True,
                'original_path': file_info['file_path'],
                'migration_date': datetime.now().isoformat()
            }
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
            logger.info("Note: All documents are marked as 'PROCESSING' status.")
            logger.info("They will be re-processed when you upload them through the UI.")
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
    logger.info("Study Buddy Simple Data Migration Tool")
    logger.info("=" * 50)
    logger.info("This tool migrates existing uploaded files to the database.")
    logger.info("It does NOT depend on Ollama or other AI services.")
    logger.info("=" * 50)
    
    try:
        # Run migration
        await migrate_all_files()
        
        # Verify results
        await verify_migration()
        
        logger.info("Migration process completed!")
        logger.info("You can now start the application and the documents will be available.")
        
    except Exception as e:
        logger.error(f"Migration process failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
