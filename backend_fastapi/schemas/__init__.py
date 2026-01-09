"""Pydantic schemas for forecast-related endpoints."""
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class ForecastBase(BaseModel):
    """Base forecast schema."""
    name: str
    mean: Optional[float] = None
    stdev: Optional[float] = None


class ForecastCreate(ForecastBase):
    """Schema for creating a forecast."""
    pass


class ForecastData(BaseModel):
    """Schema for forecast data."""
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
    
    class Config:
        from_attributes = True


class AgileDataResponse(BaseModel):
    """Schema for Agile price data response."""
    forecast_id: int
    region: str
    agile_pred: float
    agile_low: float
    agile_high: float
    date_time: datetime
    
    class Config:
        from_attributes = True


class ForecastResponse(ForecastBase):
    """Schema for forecast response."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ForecastDetailResponse(ForecastResponse):
    """Schema for detailed forecast response with related data."""
    agile_data: List[AgileDataResponse] = []
    forecast_data: List[ForecastData] = []
    
    class Config:
        from_attributes = True
