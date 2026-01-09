"""Price history and generation-related API endpoints."""
from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from datetime import datetime
from core.database import get_db
from models import PriceHistory, ForecastData, Forecast
from schemas.price import PriceHistoryResponse, GenerationDataResponse, StatsResponse
from services.stats_service import StatsService
import pandas as pd

router = APIRouter(prefix="/api", tags=["prices"])


@router.get("/price-history", response_model=List[PriceHistoryResponse])
def get_price_history(
    days: int = Query(14, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get historical price data."""
    query = db.query(PriceHistory).order_by(desc(PriceHistory.date_time))
    
    # Filter by date range
    if query.first():
        latest_date = query.first().date_time
        start_date = latest_date - pd.Timedelta(days=days)
        query = query.filter(PriceHistory.date_time >= start_date)
    
    return query.order_by(PriceHistory.date_time).all()


@router.get("/{region}/generation", response_model=List[GenerationDataResponse])
def get_generation_data(
    region: str = Path(...),
    days: int = Query(14, ge=1, le=365),
    forecast_count: int = Query(1, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Get generation/demand forecast data for a specific region."""
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
    
    # Get forecast data
    query = (
        db.query(ForecastData)
        .filter(ForecastData.forecast_id.in_(forecast_ids))
        .order_by(ForecastData.date_time)
    )
    
    results = query.all()
    
    # Filter by date range
    if results:
        min_date = min([r.date_time for r in results])
        max_date = min_date + pd.Timedelta(days=days)
        results = [r for r in results if r.date_time <= max_date]
    
    return results


@router.get("/history/actual/", response_model=List[PriceHistoryResponse])
def get_actual_price_history(
    days: int = Query(14, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get actual historical prices."""
    return get_price_history(days=days, db=db)


@router.get("/history/heatmap/", response_model=StatsResponse)
def get_price_heatmap(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Get price heatmap data showing hourly prices across days."""
    heatmap_data = StatsService.get_price_heatmap_data(db, days=days)
    
    return StatsResponse(
        stats_chart=heatmap_data.get("heatmap"),
        message=heatmap_data.get("message", "Heatmap generated successfully")
    )


@router.get("/history/daily/{date_str}", response_model=StatsResponse)
def get_daily_breakdown(
    date_str: str = Path(...),
    db: Session = Depends(get_db),
):
    """Get daily price breakdown for a specific date (format: YYYY-MM-DD)."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    breakdown_data = StatsService.get_daily_breakdown(db, target_date)
    
    if breakdown_data.get("daily_data") is None:
        return StatsResponse(
            stats_chart=None,
            message=breakdown_data.get("message")
        )
    
    return StatsResponse(
        stats_chart=breakdown_data,
        message="Daily breakdown generated successfully"
    )


@router.get("/stats/", response_model=StatsResponse)
def get_stats(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get comprehensive statistics with charts, trends, and forecast accuracy."""
    stats_data = StatsService.get_comprehensive_stats(db, days=days)
    
    return StatsResponse(
        stats_chart=stats_data,
        message=stats_data.get("message", "Stats generated successfully")
    )
