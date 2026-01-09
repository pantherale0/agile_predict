"""Shared dependencies for API endpoints."""
from fastapi import Depends
from sqlalchemy.orm import Session
from core.database import get_db


async def get_database() -> Session:
    """Get database session."""
    async for session in get_db():
        yield session
