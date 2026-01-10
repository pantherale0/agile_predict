"""Pydantic schemas for price-related endpoints."""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any


class PriceHistoryResponse(BaseModel):
    """Schema for price history response."""
    id: int
    date_time: datetime
    day_ahead: float
    agile: float
    
    model_config = ConfigDict(from_attributes=True)


class GenerationDataResponse(BaseModel):
    """Schema for generation/demand data response."""
    id: int
    forecast_id: int
    date_time: datetime
    day_ahead: Optional[float] = None
    bm_wind: float
    solar: float
    emb_wind: float
    temp_2m: float
    wind_10m: float
    rad: float
    demand: float
    
    model_config = ConfigDict(from_attributes=True)


class StatsResponse(BaseModel):
    """Schema for stats response."""
    stats_chart: Optional[dict] = None
    trend_image: Optional[str] = None
    diagnostic_plots: list = []
    message: Optional[str] = None
    summary_stats: Optional[dict] = None
    forecast_accuracy: Optional[dict] = None
    date_range: Optional[dict] = None
    
    model_config = ConfigDict(extra='allow')
