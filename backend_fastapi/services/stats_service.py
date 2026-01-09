"""Statistics and visualization service for generating reports and charts."""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models import PriceHistory, AgileData, Forecast, ForecastData
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Any, Optional
import json


class StatsService:
    """Service for statistics, heatmaps, and diagnostic generation."""
    
    @staticmethod
    def get_price_heatmap_data(
        db: Session,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Generate heatmap data for price history."""
        # Get price history
        query = db.query(PriceHistory).order_by(desc(PriceHistory.date_time))
        latest = query.first()
        
        if not latest:
            return {
                "heatmap": None,
                "message": "No data available for heatmap"
            }
        
        start_date = latest.date_time - timedelta(days=days)
        prices = db.query(PriceHistory).filter(
            PriceHistory.date_time >= start_date
        ).order_by(PriceHistory.date_time).all()
        
        if not prices:
            return {"heatmap": None, "message": "No data in date range"}
        
        # Create DataFrame
        df = pd.DataFrame({
            'date_time': [p.date_time for p in prices],
            'agile': [p.agile for p in prices],
            'day_ahead': [p.day_ahead for p in prices],
        })
        
        df['date'] = df['date_time'].dt.date
        df['hour'] = df['date_time'].dt.hour
        
        # Create pivot for heatmap
        heatmap_data = df.pivot_table(
            values='agile',
            index='date',
            columns='hour',
            aggfunc='mean'
        )
        
        # Convert to JSON-serializable format
        heatmap_json = {
            "dates": [str(d) for d in heatmap_data.index],
            "hours": list(range(24)),
            "values": heatmap_data.values.tolist(),
            "min": float(df['agile'].min()),
            "max": float(df['agile'].max()),
            "mean": float(df['agile'].mean()),
        }
        
        return {
            "heatmap": heatmap_json,
            "date_range": {
                "start": str(start_date),
                "end": str(latest.date_time),
                "days": days,
            }
        }
    
    @staticmethod
    def get_daily_breakdown(
        db: Session,
        target_date: datetime,
    ) -> Dict[str, Any]:
        """Get detailed price breakdown for a specific date."""
        # Get all prices for the day
        day_start = datetime.combine(target_date.date(), datetime.min.time())
        day_end = datetime.combine(target_date.date(), datetime.max.time())
        
        prices = db.query(PriceHistory).filter(
            PriceHistory.date_time >= day_start,
            PriceHistory.date_time <= day_end,
        ).order_by(PriceHistory.date_time).all()
        
        if not prices:
            return {
                "daily_data": None,
                "message": f"No data available for {target_date.date()}"
            }
        
        # Create DataFrame
        df = pd.DataFrame({
            'date_time': [p.date_time for p in prices],
            'agile': [p.agile for p in prices],
            'day_ahead': [p.day_ahead for p in prices],
        })
        
        df['hour'] = df['date_time'].dt.hour
        
        # Create hourly breakdown
        hourly_data = []
        for _, row in df.iterrows():
            hourly_data.append({
                "time": row['date_time'].isoformat(),
                "hour": int(row['hour']),
                "agile": float(row['agile']),
                "day_ahead": float(row['day_ahead']),
            })
        
        return {
            "date": str(target_date.date()),
            "daily_data": hourly_data,
            "summary": {
                "min_agile": float(df['agile'].min()),
                "max_agile": float(df['agile'].max()),
                "mean_agile": float(df['agile'].mean()),
                "std_agile": float(df['agile'].std()),
                "min_day_ahead": float(df['day_ahead'].min()),
                "max_day_ahead": float(df['day_ahead'].max()),
                "mean_day_ahead": float(df['day_ahead'].mean()),
                "records": len(prices),
            }
        }
    
    @staticmethod
    def get_comprehensive_stats(
        db: Session,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Generate comprehensive statistics with charts and diagnostics."""
        # Get recent price history
        query = db.query(PriceHistory).order_by(desc(PriceHistory.date_time))
        latest = query.first()
        
        if not latest:
            return {
                "stats_chart": None,
                "trend_image": None,
                "diagnostic_plots": [],
                "message": "No price history data available"
            }
        
        start_date = latest.date_time - timedelta(days=days)
        prices = db.query(PriceHistory).filter(
            PriceHistory.date_time >= start_date
        ).order_by(PriceHistory.date_time).all()
        
        if not prices:
            return {
                "stats_chart": None,
                "trend_image": None,
                "diagnostic_plots": [],
                "message": "No data in date range"
            }
        
        # Create DataFrame
        df = pd.DataFrame({
            'date_time': [p.date_time for p in prices],
            'agile': [p.agile for p in prices],
            'day_ahead': [p.day_ahead for p in prices],
        })
        
        # Calculate statistics
        stats = {
            "agile": {
                "min": float(df['agile'].min()),
                "max": float(df['agile'].max()),
                "mean": float(df['agile'].mean()),
                "median": float(df['agile'].median()),
                "std": float(df['agile'].std()),
                "q25": float(df['agile'].quantile(0.25)),
                "q75": float(df['agile'].quantile(0.75)),
            },
            "day_ahead": {
                "min": float(df['day_ahead'].min()),
                "max": float(df['day_ahead'].max()),
                "mean": float(df['day_ahead'].mean()),
                "median": float(df['day_ahead'].median()),
                "std": float(df['day_ahead'].std()),
                "q25": float(df['day_ahead'].quantile(0.25)),
                "q75": float(df['day_ahead'].quantile(0.75)),
            },
            "correlation": float(df['agile'].corr(df['day_ahead'])),
        }
        
        # Get forecast accuracy if available
        forecasts = db.query(Forecast).order_by(desc(Forecast.created_at)).limit(1).all()
        forecast_accuracy = None
        
        if forecasts:
            forecast = forecasts[0]
            agile_data = db.query(AgileData).filter(
                AgileData.forecast_id == forecast.id,
                AgileData.date_time >= start_date,
            ).all()
            
            if agile_data:
                # Match with actual prices
                forecast_values = []
                actual_values = []
                
                for agile in agile_data:
                    actual = next(
                        (p for p in prices if p.date_time == agile.date_time),
                        None
                    )
                    if actual:
                        forecast_values.append(agile.agile_pred)
                        actual_values.append(actual.agile)
                
                if forecast_values:
                    forecast_df = pd.DataFrame({
                        'forecast': forecast_values,
                        'actual': actual_values,
                    })
                    
                    # Calculate RMSE and MAE
                    forecast_df['error'] = forecast_df['forecast'] - forecast_df['actual']
                    mse = (forecast_df['error'] ** 2).mean()
                    rmse = mse ** 0.5
                    mae = forecast_df['error'].abs().mean()
                    mape = (forecast_df['error'].abs() / forecast_df['actual']).mean() * 100
                    
                    forecast_accuracy = {
                        "forecast_date": forecast.created_at.isoformat(),
                        "rmse": float(rmse),
                        "mae": float(mae),
                        "mape": float(mape),
                        "samples": len(forecast_values),
                    }
        
        # Generate chart data (Plotly format)
        chart_data = {
            "x": [p.date_time.isoformat() for p in prices],
            "agile": [p.agile for p in prices],
            "day_ahead": [p.day_ahead for p in prices],
        }
        
        return {
            "summary_stats": stats,
            "forecast_accuracy": forecast_accuracy,
            "chart_data": chart_data,
            "date_range": {
                "start": str(start_date),
                "end": str(latest.date_time),
                "days": days,
                "samples": len(prices),
            },
            "message": "Statistics generated successfully"
        }
    
    @staticmethod
    def get_price_trends(
        db: Session,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get price trends over time."""
        query = db.query(PriceHistory).order_by(desc(PriceHistory.date_time))
        latest = query.first()
        
        if not latest:
            return {"trends": None, "message": "No data available"}
        
        start_date = latest.date_time - timedelta(days=days)
        prices = db.query(PriceHistory).filter(
            PriceHistory.date_time >= start_date
        ).order_by(PriceHistory.date_time).all()
        
        if not prices:
            return {"trends": None, "message": "No data in date range"}
        
        # Create DataFrame and calculate trends
        df = pd.DataFrame({
            'date_time': [p.date_time for p in prices],
            'agile': [p.agile for p in prices],
        })
        
        # Daily averages
        df['date'] = df['date_time'].dt.date
        daily_avg = df.groupby('date')['agile'].agg(['mean', 'min', 'max', 'std']).reset_index()
        
        # Calculate moving averages
        df_sorted = df.sort_values('date_time')
        df_sorted['ma7'] = df_sorted['agile'].rolling(window=168, min_periods=1).mean()  # 7 days
        df_sorted['ma30'] = df_sorted['agile'].rolling(window=720, min_periods=1).mean()  # 30 days
        
        return {
            "daily_trends": [
                {
                    "date": str(row['date']),
                    "mean": float(row['mean']),
                    "min": float(row['min']),
                    "max": float(row['max']),
                    "std": float(row['std']),
                }
                for _, row in daily_avg.iterrows()
            ],
            "chart_data": {
                "x": [p.date_time.isoformat() for p in prices],
                "agile": [p.agile for p in prices],
                "ma7": df_sorted['ma7'].tolist(),
                "ma30": df_sorted['ma30'].tolist(),
            },
            "date_range": {
                "start": str(start_date),
                "end": str(latest.date_time),
                "days": days,
            }
        }
