"""
Database connection and session management for Study Buddy application.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import make_url
import logging
import ssl
from typing import AsyncGenerator, Tuple, Dict, Any
from contextlib import asynccontextmanager
from app.config import settings

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

def _prepare_database_url(raw_url: str) -> Tuple[str, Dict[str, Any]]:
    """
    Translate libpq-style sslmode query parameters to asyncpg-compatible kwargs.
    This prevents asyncpg from receiving unsupported keywords like `sslmode`.
    """
    url = make_url(raw_url)
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    sanitized_url = url.set(query=query)

    connect_args: Dict[str, Any] = {}
    if sslmode:
        ssl_arg = _map_sslmode_to_asyncpg_ssl(sslmode)
        if ssl_arg is not None:
            connect_args["ssl"] = ssl_arg
            logger.info("Applied SSL mode '%s' for database connections", sslmode)
        else:
            logger.warning("Unknown sslmode '%s'; defaulting to driver behavior", sslmode)

    return sanitized_url.render_as_string(hide_password=False), connect_args


def _map_sslmode_to_asyncpg_ssl(sslmode: str):
    """
    Map libpq sslmode values to asyncpg's `ssl` argument.
    """
    sslmode = sslmode.lower()
    if sslmode == "disable":
        return None
    if sslmode in {"allow", "prefer", "require"}:
        # True tells asyncpg to use its default SSL context (encryption without hostname verification)
        return True
    if sslmode == "verify-ca":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        return ctx
    if sslmode == "verify-full":
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        return ctx
    return True


database_url, connect_args = _prepare_database_url(settings.DATABASE_URL)

# Create async engine with connection pooling
engine = create_async_engine(
    database_url,
    echo=False,  # Set to True for SQL query logging
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
    connect_args=connect_args,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.
    Use this in FastAPI route dependencies.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()

@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.
    Use this for background tasks and manual session management.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()

async def init_database():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from app.database.models import Document, ChatSession, ChatMessage
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

async def close_database():
    """Close database connections"""
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {str(e)}")
