"""Price service for business logic."""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models import PriceHistory, ForecastData
from typing import List, Optional
from datetime import datetime, timedelta


class PriceService:
    """Service for price operations."""
    
    @staticmethod
    def get_price_history_range(
        db: Session,
        days: int = 14,
    ) -> List[PriceHistory]:
        """Get price history for the last N days."""
        query = db.query(PriceHistory).order_by(desc(PriceHistory.date_time))
        
        latest = query.first()
        if not latest:
            return []
        
        start_date = latest.date_time - timedelta(days=days)
        
        return (
            db.query(PriceHistory)
            .filter(PriceHistory.date_time >= start_date)
            .order_by(PriceHistory.date_time)
            .all()
        )
    
    @staticmethod
    def get_latest_price(db: Session) -> Optional[PriceHistory]:
        """Get the latest price record."""
        return db.query(PriceHistory).order_by(desc(PriceHistory.date_time)).first()
    
    @staticmethod
    def get_prices_by_date_range(
        db: Session,
        start_date: datetime,
        end_date: datetime,
    ) -> List[PriceHistory]:
        """Get prices within a date range."""
        return (
            db.query(PriceHistory)
            .filter(
                PriceHistory.date_time >= start_date,
                PriceHistory.date_time <= end_date,
            )
            .order_by(PriceHistory.date_time)
            .all()
        )
