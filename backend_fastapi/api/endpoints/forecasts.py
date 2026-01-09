"""Forecast-related API endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from core.database import get_db
from models import Forecast, AgileData, ForecastData
from schemas import ForecastResponse, ForecastDetailResponse, AgileDataResponse
import pandas as pd

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("/latest", response_model=List[ForecastResponse])
def get_latest_forecast(
    db: Session = Depends(get_db),
):
    """Get the latest forecast."""
    latest = db.query(Forecast).order_by(desc(Forecast.created_at)).limit(1).all()
    return latest


@router.get("/{region}", response_model=List[ForecastDetailResponse])
def get_forecast_by_region(
    region: str,
    days: int = Query(14, ge=1, le=365),
    forecast_count: int = Query(1, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Get forecast data for a specific region."""
    region_upper = region.upper()
    
    # Get the latest N forecasts
    forecasts = (
        db.query(Forecast)
        .order_by(desc(Forecast.created_at))
        .limit(forecast_count)
        .all()
    )
    
    if not forecasts:
        return []
    
    forecast_ids = [f.id for f in forecasts]
    
    # Get agile data for the region
    agile_data = (
        db.query(AgileData)
        .filter(
            AgileData.forecast_id.in_(forecast_ids),
            AgileData.region == region_upper,
        )
        .order_by(desc(AgileData.date_time))
        .all()
    )
    
    # Filter by date range
    if agile_data:
        min_date = min([a.date_time for a in agile_data])
        max_date = min_date + pd.Timedelta(days=days)
        agile_data = [a for a in agile_data if a.date_time <= max_date]
    
    # Build response with agile data
    results = []
    for forecast in forecasts:
        forecast_agile_data = [a for a in agile_data if a.forecast_id == forecast.id]
        results.append(
            ForecastDetailResponse(
                id=forecast.id,
                name=forecast.name,
                created_at=forecast.created_at,
                mean=forecast.mean,
                stdev=forecast.stdev,
                agile_data=forecast_agile_data,
                forecast_data=[],
            )
        )
    
    return results
