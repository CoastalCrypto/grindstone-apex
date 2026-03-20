"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.database import init_db, get_db
from src.config import get_settings
from src.api import routes
from src.api import live_trading_routes
from src.api import phase5_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown logic."""
    # Startup
    logger.info("Starting Grindstone Apex API...")
    settings = get_settings()
    logger.info(f"Environment: {settings.env}")
    logger.info(f"Database: {settings.database_url}")
    logger.info(f"Pairs to trade: {settings.pairs_list}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Grindstone Apex API...")


# Create FastAPI app
app = FastAPI(
    title="Grindstone Apex",
    description="AI-Driven Self-Improving Trading Bot",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router, prefix="/api/v1", tags=["api"])
app.include_router(live_trading_routes.router)
app.include_router(phase5_routes.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Grindstone Apex is running",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Grindstone Apex",
        "description": "AI-Driven Self-Improving Trading Bot",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        workers=settings.workers,
        reload=(settings.env == "development"),
        log_level=settings.log_level.lower(),
    )
