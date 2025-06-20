#!/usr/bin/env python3
"""
Migration script to update the database schema for multi-session chat management.
This script adds the new columns and tables needed for the enhanced chat system.
"""

import asyncio
import asyncpg
import logging
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration():
    """Run the database migration"""
    
    try:
        # Connect to the database
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        logger.info("Connected to database successfully")
        
        # Start transaction
        async with conn.transaction():
            
            # 1. Add title column to chat_sessions table if it doesn't exist
            try:
                await conn.execute("""
                    ALTER TABLE chat_sessions 
                    ADD COLUMN IF NOT EXISTS title VARCHAR(255)
                """)
                logger.info("✅ Added title column to chat_sessions table")
            except Exception as e:
                logger.error(f"Error adding title column: {str(e)}")
                raise
            
            # 2. Create chat_session_documents association table if it doesn't exist
            try:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_session_documents (
                        chat_session_id INTEGER NOT NULL,
                        document_id INTEGER NOT NULL,
                        added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        PRIMARY KEY (chat_session_id, document_id),
                        FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                """)
                logger.info("✅ Created chat_session_documents association table")
            except Exception as e:
                logger.error(f"Error creating association table: {str(e)}")
                raise
            
            # 3. Add indexes for better performance
            try:
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_session_documents_session_id 
                    ON chat_session_documents(chat_session_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_session_documents_document_id 
                    ON chat_session_documents(document_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_sessions_title 
                    ON chat_sessions(title)
                """)
                logger.info("✅ Created performance indexes")
            except Exception as e:
                logger.error(f"Error creating indexes: {str(e)}")
                raise
            
            # 4. Update existing sessions with default titles
            try:
                result = await conn.execute("""
                    UPDATE chat_sessions 
                    SET title = 'Chat ' || id::text 
                    WHERE title IS NULL
                """)
                updated_count = int(result.split()[-1])
                logger.info(f"✅ Updated {updated_count} existing sessions with default titles")
            except Exception as e:
                logger.error(f"Error updating session titles: {str(e)}")
                raise
        
        await conn.close()
        logger.info("🎉 Migration completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

async def verify_migration():
    """Verify that the migration was successful"""
    
    try:
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        logger.info("Verifying migration...")
        
        # Check if title column exists
        title_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'chat_sessions' 
                AND column_name = 'title'
            )
        """)
        
        # Check if association table exists
        assoc_table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'chat_session_documents'
            )
        """)
        
        # Check session count
        session_count = await conn.fetchval("SELECT COUNT(*) FROM chat_sessions")
        
        # Check document count
        document_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        
        await conn.close()
        
        logger.info("=" * 50)
        logger.info("MIGRATION VERIFICATION")
        logger.info("=" * 50)
        logger.info(f"✅ Title column exists: {title_exists}")
        logger.info(f"✅ Association table exists: {assoc_table_exists}")
        logger.info(f"📊 Chat sessions: {session_count}")
        logger.info(f"📊 Documents: {document_count}")
        
        if title_exists and assoc_table_exists:
            logger.info("🎉 Migration verification successful!")
            return True
        else:
            logger.error("❌ Migration verification failed!")
            return False
            
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        return False

async def main():
    """Main migration function"""
    logger.info("Study Buddy Multi-Session Migration")
    logger.info("=" * 50)
    logger.info("This script will update your database to support multi-session chat management.")
    logger.info("=" * 50)
    
    try:
        # Run migration
        success = await run_migration()
        
        if success:
            # Verify migration
            await verify_migration()
            
            logger.info("=" * 50)
            logger.info("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            logger.info("=" * 50)
            logger.info("Your Study Buddy application now supports:")
            logger.info("• Multiple chat sessions")
            logger.info("• Document-specific contexts per session")
            logger.info("• Session titles and management")
            logger.info("• Persistent chat history")
            logger.info("")
            logger.info("You can now restart your application to use the new features!")
            
        else:
            logger.error("❌ Migration failed. Please check the errors above.")
            
    except Exception as e:
        logger.error(f"Migration process failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
