"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from core.config import settings
from core.security import add_cors_middleware, add_trusted_host_middleware
from core.database import engine
from models import Base
from api.endpoints import forecasts, price_history, tasks
from tasks.scheduler import start_scheduler, stop_scheduler
from admin.setup import setup_admin
from admin.resources import register_admin_models

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    logger.info("Starting up FastAPI application")
    start_scheduler()
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application")
    stop_scheduler()


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    lifespan=lifespan,
)

# Add middleware
add_cors_middleware(app)
add_trusted_host_middleware(app)

# Setup admin dashboard
admin = setup_admin(app)
register_admin_models(admin)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "version": settings.PROJECT_VERSION})


# Include routers
app.include_router(forecasts.router, prefix=settings.API_V1_STR)
app.include_router(price_history.router, prefix=settings.API_V1_STR)
app.include_router(tasks.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AgilePredictAPI",
        "version": settings.PROJECT_VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
