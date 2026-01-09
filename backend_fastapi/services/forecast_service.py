"""Forecast service for business logic."""
from sqlalchemy.orm import Session
from models import Forecast, ForecastData, AgileData
from sqlalchemy import desc
from typing import List, Optional


class ForecastService:
    """Service for forecast operations."""
    
    @staticmethod
    def get_latest_forecast(db: Session, count: int = 1) -> List[Forecast]:
        """Get the latest N forecasts."""
        return (
            db.query(Forecast)
            .order_by(desc(Forecast.created_at))
            .limit(count)
            .all()
        )
    
    @staticmethod
    def get_forecast_by_id(db: Session, forecast_id: int) -> Optional[Forecast]:
        """Get forecast by ID."""
        return db.query(Forecast).filter(Forecast.id == forecast_id).first()
    
    @staticmethod
    def get_agile_data_by_forecast_and_region(
        db: Session,
        forecast_id: int,
        region: str,
    ) -> List[AgileData]:
        """Get agile data for a specific forecast and region."""
        return (
            db.query(AgileData)
            .filter(
                AgileData.forecast_id == forecast_id,
                AgileData.region == region.upper(),
            )
            .order_by(AgileData.date_time)
            .all()
        )
    
    @staticmethod
    def get_forecast_data_by_forecast(
        db: Session,
        forecast_id: int,
    ) -> List[ForecastData]:
        """Get all forecast data for a specific forecast."""
        return (
            db.query(ForecastData)
            .filter(ForecastData.forecast_id == forecast_id)
            .order_by(ForecastData.date_time)
            .all()
        )
