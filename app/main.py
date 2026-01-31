from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import init_db
from app.api.routes import auth, conversations, messages, runs, media

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application"""
    # Startup
    logger.info("Starting up application")
    logger.info("Initializing database")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title="LangGraph Chat Backend",
    description="Backend API for Android-first chat application with async LangGraph agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - configured for VM access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(messages.router)
app.include_router(runs.router)
app.include_router(media.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LangGraph Chat Backend API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
