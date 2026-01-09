"""Initialize database with all models."""
from core.database import engine
from models import Base

# Create all tables
Base.metadata.create_all(bind=engine)
print("✅ Database tables created successfully")
