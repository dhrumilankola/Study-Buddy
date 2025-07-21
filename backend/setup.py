import asyncio
from app.database.connection import engine
from app.database.models import Base

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅  Tables created")

asyncio.run(create())