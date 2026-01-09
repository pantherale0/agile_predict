"""Settings and configuration management for FastAPI application."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        json_schema_extra={"env": {
            "ALLOWED_HOSTS": {"case_sensitive": False},
            "CORS_ORIGINS": {"case_sensitive": False},
        }}
    )
    
    # Project
    PROJECT_NAME: str = "AgilePredictAPI"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "FastAPI backend for energy price forecasting"
    
    # API
    API_V1_STR: str = "/api"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./agile_predict.db"
    SQLALCHEMY_ECHO: bool = False
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "agilepredict.com", ".agilepredict.com", ".fly.dev"]
    )
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    
    # Logging
    LOG_DIR: str = os.path.join(os.path.dirname(__file__), "../../logs")
    LOG_LEVEL: str = "INFO"
    
    # Scheduler
    SCHEDULER_TIMEZONE: str = "UTC"
    SCHEDULER_CONFIG: dict = {
        "apscheduler.timezone": "UTC",
    }
    
    # Data paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PLOTS_DIR: Path = BASE_DIR / "plots"
    STATS_PLOTS_DIR: Path = PLOTS_DIR / "stats_plots"
    TRENDS_DIR: Path = PLOTS_DIR / "trends"
    
    # Local sync settings
    LOCAL_SYNC_DIR: str = "temp"
    LOCAL_SYNC_HDF_FILE: str = "forecast.hdf"
    
    @field_validator("ALLOWED_HOSTS", "CORS_ORIGINS", mode="before")
    @classmethod
    def parse_comma_separated(cls, v):
        """Parse comma-separated strings from environment variables."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


settings = Settings()
