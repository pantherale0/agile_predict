"""SQLAlchemy models for the application."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Forecast(Base):
    """Forecast model - stores forecast metadata."""
    __tablename__ = "forecasting_forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    mean = Column(Float, nullable=True)
    stdev = Column(Float, nullable=True)
    
    # Relationships
    agile_data = relationship("AgileData", back_populates="forecast", cascade="all, delete-orphan")
    forecast_data = relationship("ForecastData", back_populates="forecast", cascade="all, delete-orphan")
    
    def __str__(self) -> str:
        return self.name


class ForecastData(Base):
    """Forecast data model - stores detailed forecast information."""
    __tablename__ = "forecasting_forecastdata"
    
    id = Column(Integer, primary_key=True, index=True)
    forecast_id = Column(Integer, ForeignKey("forecasting_forecasts.id"), index=True)
    date_time = Column(DateTime, index=True)
    day_ahead = Column(Float, nullable=True)
    day_ahead_low = Column(Float, nullable=True)
    day_ahead_high = Column(Float, nullable=True)
    bm_wind = Column(Float)
    solar = Column(Float)
    emb_wind = Column(Float)
    temp_2m = Column(Float)
    wind_10m = Column(Float)
    rad = Column(Float)
    demand = Column(Float)
    
    # Relationships
    forecast = relationship("Forecast", back_populates="forecast_data")


class PriceHistory(Base):
    """Price history model - stores actual historical prices."""
    __tablename__ = "forecasting_pricehistory"
    
    id = Column(Integer, primary_key=True, index=True)
    date_time = Column(DateTime, unique=True, index=True)
    day_ahead = Column(Float)
    agile = Column(Float)


class AgileData(Base):
    """Agile data model - stores Agile price predictions by region."""
    __tablename__ = "forecasting_agiledata"
    
    id = Column(Integer, primary_key=True, index=True)
    forecast_id = Column(Integer, ForeignKey("forecasting_forecasts.id"), index=True)
    region = Column(String(1), index=True)
    agile_pred = Column(Float)
    agile_low = Column(Float)
    agile_high = Column(Float)
    date_time = Column(DateTime, index=True)
    
    # Relationships
    forecast = relationship("Forecast", back_populates="agile_data")


class History(Base):
    """Historical data model - stores weather and demand data."""
    __tablename__ = "forecasting_history"
    
    id = Column(Integer, primary_key=True, index=True)
    date_time = Column(DateTime, unique=True, index=True)
    total_wind = Column(Float)
    bm_wind = Column(Float)
    solar = Column(Float)
    temp_2m = Column(Float)
    wind_10m = Column(Float)
    rad = Column(Float)
    demand = Column(Float)


class TaskLog(Base):
    """Task execution log model - tracks background job executions."""
    __tablename__ = "task_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(128), index=True)
    job_name = Column(String(255), index=True)
    started_at = Column(DateTime, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    status = Column(String(20), default="running", index=True)  # running, success, failed
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __str__(self) -> str:
        return f"{self.job_name} - {self.started_at}"
