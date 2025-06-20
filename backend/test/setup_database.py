#!/usr/bin/env python3
"""
Database setup script for Study Buddy application.
This script creates the PostgreSQL database and user if they don't exist.
"""

import asyncio
import asyncpg
import logging
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_database_and_user():
    """Create database and user if they don't exist"""
    
    # Connect to PostgreSQL as superuser (usually 'postgres')
    try:
        # First, connect to the default 'postgres' database
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user='postgres',  # Default superuser
            password='password',  # You may need to change this
            database='postgres'
        )
        
        # Check if user exists
        user_exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = $1",
            settings.DATABASE_USER
        )
        
        if not user_exists:
            await conn.execute(f"""
                CREATE USER {settings.DATABASE_USER} 
                WITH PASSWORD '{settings.DATABASE_PASSWORD}'
            """)
            logger.info(f"Created user: {settings.DATABASE_USER}")
        else:
            logger.info(f"User {settings.DATABASE_USER} already exists")
        
        # Check if database exists
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.DATABASE_NAME
        )
        
        if not db_exists:
            await conn.execute(f"CREATE DATABASE {settings.DATABASE_NAME}")
            logger.info(f"Created database: {settings.DATABASE_NAME}")

            # Grant privileges on database
            await conn.execute(f"""
                GRANT ALL PRIVILEGES ON DATABASE {settings.DATABASE_NAME}
                TO {settings.DATABASE_USER}
            """)
            logger.info(f"Granted database privileges to {settings.DATABASE_USER}")
        else:
            logger.info(f"Database {settings.DATABASE_NAME} already exists")

        await conn.close()

        # Now connect to the study_buddy database to grant schema privileges
        try:
            conn = await asyncpg.connect(
                host=settings.DATABASE_HOST,
                port=settings.DATABASE_PORT,
                user='postgres',  # Still need superuser for schema privileges
                password='postgres',
                database=settings.DATABASE_NAME  # Connect to the study_buddy database
            )

            # Grant schema privileges
            await conn.execute(f"GRANT ALL ON SCHEMA public TO {settings.DATABASE_USER}")
            await conn.execute(f"GRANT CREATE ON SCHEMA public TO {settings.DATABASE_USER}")
            await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {settings.DATABASE_USER}")
            await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {settings.DATABASE_USER}")
            await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO {settings.DATABASE_USER}")

            logger.info(f"Granted schema privileges to {settings.DATABASE_USER}")

        except Exception as schema_error:
            logger.warning(f"Could not grant schema privileges: {str(schema_error)}")
            logger.info("You may need to run these commands manually as postgres superuser:")
            logger.info(f"GRANT ALL ON SCHEMA public TO {settings.DATABASE_USER};")
            logger.info(f"GRANT CREATE ON SCHEMA public TO {settings.DATABASE_USER};")
        
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Error setting up database: {str(e)}")
        logger.info("Please ensure PostgreSQL is running and you have the correct credentials")
        logger.info("You may need to:")
        logger.info("1. Install PostgreSQL")
        logger.info("2. Start PostgreSQL service")
        logger.info("3. Update the postgres user password")
        logger.info("4. Run this script with appropriate credentials")
        raise

async def test_connection():
    """Test connection to the Study Buddy database"""
    try:
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        # Test query
        result = await conn.fetchval("SELECT version()")
        logger.info(f"Successfully connected to database!")
        logger.info(f"PostgreSQL version: {result}")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        return False

async def main():
    """Main setup function"""
    logger.info("Setting up Study Buddy database...")
    logger.info(f"Host: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}")
    logger.info(f"Database: {settings.DATABASE_NAME}")
    logger.info(f"User: {settings.DATABASE_USER}")
    
    try:
        # Create database and user
        await create_database_and_user()
        
        # Test connection
        if await test_connection():
            logger.info("✅ Database setup completed successfully!")
            logger.info("You can now run the application or create migrations")
        else:
            logger.error("❌ Database setup failed")
            
    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
