#!/usr/bin/env python3
"""
Test script to verify database permissions are set correctly.
"""

import asyncio
import asyncpg
import sys
import os
import logging

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_permissions():
    """Test if the study_buddy user has the necessary permissions"""
    
    try:
        # Connect as study_buddy user
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        logger.info("✅ Successfully connected to database as study_buddy user")
        
        # Test creating an enum type
        try:
            await conn.execute("DROP TYPE IF EXISTS test_enum CASCADE")
            await conn.execute("CREATE TYPE test_enum AS ENUM ('test1', 'test2')")
            logger.info("✅ Can create ENUM types")
            
            # Clean up
            await conn.execute("DROP TYPE test_enum CASCADE")
            
        except Exception as e:
            logger.error(f"❌ Cannot create ENUM types: {str(e)}")
            return False
        
        # Test creating a table
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100)
                )
            """)
            logger.info("✅ Can create tables")
            
            # Test inserting data
            await conn.execute("INSERT INTO test_table (name) VALUES ('test')")
            logger.info("✅ Can insert data")
            
            # Test querying data
            result = await conn.fetchval("SELECT name FROM test_table WHERE name = 'test'")
            if result == 'test':
                logger.info("✅ Can query data")
            
            # Clean up
            await conn.execute("DROP TABLE test_table")
            logger.info("✅ Can drop tables")
            
        except Exception as e:
            logger.error(f"❌ Cannot create/use tables: {str(e)}")
            return False
        
        await conn.close()
        logger.info("✅ All permission tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection or permission test failed: {str(e)}")
        return False

async def main():
    """Main test function"""
    logger.info("Testing database permissions for study_buddy user...")
    logger.info("=" * 50)
    
    success = await test_permissions()
    
    if success:
        logger.info("🎉 Database permissions are correctly configured!")
        logger.info("You can now run the migration script.")
    else:
        logger.error("💥 Database permissions need to be fixed.")
        logger.info("Please run one of these solutions:")
        logger.info("1. python setup_database.py")
        logger.info("2. psql -U postgres -h localhost -f setup_permissions.sql")
        logger.info("3. Manually grant permissions as shown in the documentation")

if __name__ == "__main__":
    asyncio.run(main())
