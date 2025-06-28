import asyncio
import os
from dotenv import load_dotenv

async def setup_database():
    """Drop all existing tables and create new ones based on the models."""
    load_dotenv()
    
    from app.database.connection import engine
    from app.database.models import Base
    
    print("Connecting to the database...")
    async with engine.begin() as conn:
        print("Dropping all existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating new tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("\nSUCCESS: Database schema has been reset successfully!")
    print("You can now safely delete the init_db.py script and restart the server.")

if __name__ == "__main__":
    asyncio.run(setup_database()) 