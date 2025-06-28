import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.api import router as api_router
from app.database.connection import engine
from app.database.models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include the main API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Study Buddy API...")
    async with engine.begin() as conn:
        # This ensures tables are created, but it's safe to run again
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Study Buddy API started successfully.")
    logger.info(f"Model Provider: {settings.DEFAULT_MODEL_PROVIDER}")
    model_in_use = settings.GEMINI_MODEL if settings.DEFAULT_MODEL_PROVIDER == 'gemini' else settings.OLLAMA_MODEL
    logger.info(f"Using Model: {model_in_use}")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Shutting down Study Buddy API.")

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Study Buddy API!"} 