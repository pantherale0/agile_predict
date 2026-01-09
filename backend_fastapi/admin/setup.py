"""Admin dashboard setup and configuration."""
from fastapi import FastAPI
from sqlalchemy.orm import Session
from core.database import engine, SessionLocal
import logging

logger = logging.getLogger(__name__)


def setup_admin(app: FastAPI):
    """Initialize and configure the admin dashboard.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Admin instance that can register models
    """
    # Import here to avoid circular imports
    from starlette_admin.contrib.sqla import Admin
    from admin.custom_views import SchedulerInfoView
    
    # Create admin instance
    admin = Admin(engine=engine, title="AgilePredictAPI Admin")
    
    # Register custom views (non-model views)
    admin.add_view(SchedulerInfoView())
    
    # Mount admin app
    admin.mount_to(app)
    
    logger.info("Admin dashboard configured at /admin")
    
    return admin


def get_admin_session() -> Session:
    """Get a database session for admin operations."""
    return SessionLocal()
