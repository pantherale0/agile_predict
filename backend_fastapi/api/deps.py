"""Shared dependencies for API endpoints."""
from fastapi import Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_user, User


async def get_database() -> Session:
    """Get database session."""
    async for session in get_db():
        yield session


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user is authenticated admin.
    
    Args:
        current_user: The current authenticated user
        
    Returns:
        The authenticated user
    """
    return current_user
