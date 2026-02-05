import uvicorn
from app.api.endpoints import router
from app.core.database import db
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from contextlib import asynccontextmanager


def main():
    """
CreditFlow AI - Main Application Entry Point

FastAPI application with LangGraph orchestration for credit risk analysis.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting CreditFlow AI...")
    print(f"Environment: {settings.api.environment}")
    print(f"Debug mode: {settings.api.debug}")

    # Initialize database connection
    await db.connect()
    print("✅ Database connected")

    # Initialize database schema for checkpointing
    if settings.features.enable_checkpointing:
        await db.initialize_schema()
        print("✅ Checkpoint schema initialized")

    yield

    # Shutdown
    print("🛑 Shutting down CreditFlow AI...")
    await db.disconnect()
    print("✅ Database disconnected")


# Create FastAPI application
app = FastAPI(
    title=settings.api.name,
    version=settings.api.version,
    description="AI-powered credit risk analysis system using LangGraph",
    lifespan=lifespan,
    debug=settings.api.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=settings.api.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.api.name,
        "version": settings.api.version,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level=settings.api.log_level.lower(),
    )
