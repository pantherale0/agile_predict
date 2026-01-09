"""Settings and configuration management for FastAPI application."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List
import os
from pathlib import Path

# Get the directory of this config file (backend_fastapi/core/)
CONFIG_DIR = Path(__file__).parent
# Get backend_fastapi directory
BACKEND_DIR = CONFIG_DIR.parent
# Point to backend_fastapi/.env specifically, not parent directories
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        case_sensitive=True,
        populate_by_name=True,  # Allow both field name and alias
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
    # Use string fields with validator instead of List to avoid JSON parsing
    ALLOWED_HOSTS_STR: str = Field(
        default="localhost,127.0.0.1,agilepredict.com,.agilepredict.com,.fly.dev",
        alias="ALLOWED_HOSTS"
    )
    
    # CORS
    CORS_ORIGINS_STR: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="CORS_ORIGINS"
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
    
    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        """Parse ALLOWED_HOSTS from comma-separated string."""
        return [item.strip() for item in self.ALLOWED_HOSTS_STR.split(",") if item.strip()]
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse CORS_ORIGINS from comma-separated string."""
        return [item.strip() for item in self.CORS_ORIGINS_STR.split(",") if item.strip()]


settings = Settings()
