"""Statistics and visualization service for generating reports and charts."""
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from models import PriceHistory, AgileData, Forecast, ForecastData
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Any, Optional
import json
import plotly.graph_objects as go


class StatsService:
    """Service for statistics, heatmaps, and diagnostic generation."""
    
    @staticmethod
    def get_price_heatmap_data(
        db: Session,
        days: int = 365,
    ) -> Dict[str, Any]:
        """Generate heatmap data for price history - calendar style like Django."""
        
        # Get the latest date in the database
        latest_record = db.query(PriceHistory).order_by(desc(PriceHistory.date_time)).first()
        
        if not latest_record:
            return {
                "heatmap": None,
                "message": "No data available for heatmap"
            }
        
        latest_date_result = latest_record.date_time
        start_date = latest_date_result - timedelta(days=days)
        prices = db.query(PriceHistory).filter(
            PriceHistory.date_time >= start_date
        ).order_by(PriceHistory.date_time).all()
        
        if not prices:
            return {"heatmap": None, "message": "No data in date range"}
        
        # Create DataFrame with date and price
        df = pd.DataFrame({
            'date_time': [p.date_time for p in prices],
            'agile': [p.agile for p in prices],
        })
        
        # Calculate daily average prices
        df['date'] = pd.to_datetime(df['date_time']).dt.date
        daily_avg = df.groupby('date')['agile'].mean().reset_index()
        daily_avg['date'] = pd.to_datetime(daily_avg['date'])
        
        # Create week and day of week for calendar heatmap
        daily_avg['year'] = daily_avg['date'].dt.isocalendar().year
        daily_avg['week'] = daily_avg['date'].dt.isocalendar().week
        daily_avg['day_of_week'] = daily_avg['date'].dt.day_name()
        daily_avg['day_num'] = daily_avg['date'].dt.dayofweek  # 0=Mon, 6=Sun
        
        # Create pivot table for heatmap (days x weeks)
        pivot = daily_avg.pivot_table(
            index='day_num',
            columns='week',
            values='agile',
            aggfunc='mean'
        )
        
        # Create a date mapping for clicking
        date_mapping = {}
        for _, row in daily_avg.iterrows():
            week = row['week']
            day_num = row['day_num']
            date_str = row['date'].strftime('%Y-%m-%d')
            date_mapping[f"{int(week)}_{int(day_num)}"] = date_str
        
        # Create customdata array for dates
        customdata = []
        for row_idx in range(len(pivot.index)):
            row_data = []
            for col_idx in range(len(pivot.columns)):
                week = int(pivot.columns[col_idx])
                day_num = int(pivot.index[row_idx])
                date_str = date_mapping.get(f"{week}_{day_num}", "")
                row_data.append(date_str)
            customdata.append(row_data)
        
        days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Create plotly figure
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=[days_list[i] for i in pivot.index],
            customdata=customdata,
            colorscale='RdYlGn_r',  # Red (high prices) to Green (low prices)
            colorbar=dict(title="Price (p/kWh)"),
            hovertemplate="Week %{x}<br>%{y}<br>Date: %{customdata}<br>Avg Price: £%{z:.2f}/kWh<extra></extra>"
        ))
        
        fig.update_layout(
            title="Daily Average Agile Price - Last 365 Days",
            xaxis_title="Week of Year",
            yaxis_title="Day of Week",
            template="plotly_dark",
            plot_bgcolor="#212529",
            paper_bgcolor="#343a40",
            font={"color": "#ccc"},
            height=400,
            hovermode='closest'
        )
        
        # Convert to JSON
        heatmap_json = json.loads(fig.to_json())
        
        # Return statistics
        stats = {
            "min_price": float(daily_avg['agile'].min()),
            "max_price": float(daily_avg['agile'].max()),
            "avg_price": float(daily_avg['agile'].mean()),
            "median_price": float(daily_avg['agile'].median()),
        }
        
        return {
            "heatmap": heatmap_json,
            "stats": stats,
            "date_range": {
                "start": str(start_date),
                "end": str(latest_date_result),
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
        
        # Create Plotly chart format
        chart_plotly = {
            "data": [
                {
                    "x": [p.date_time.isoformat() for p in prices],
                    "y": [p.agile for p in prices],
                    "name": "Agile Price",
                    "type": "scatter",
                    "mode": "lines+markers",
                    "line": {"color": "#007bff"}
                },
                {
                    "x": [p.date_time.isoformat() for p in prices],
                    "y": [p.day_ahead for p in prices],
                    "name": "Day Ahead Price",
                    "type": "scatter",
                    "mode": "lines+markers",
                    "line": {"color": "#dc3545"}
                }
            ],
            "layout": {
                "title": f"Hourly Prices for {target_date.date()}",
                "xaxis": {
                    "title": "Time"
                },
                "yaxis": {
                    "title": "Price (p/kWh)"
                },
                "hovermode": "x unified",
                "height": 500,
                "margin": {
                    "l": 60,
                    "r": 60,
                    "b": 60,
                    "t": 80
                }
            }
        }
        
        return {
            "chart": chart_plotly,
            "date": str(target_date.date()),
            "stats": {
                "min_price": float(df['agile'].min()),
                "max_price": float(df['agile'].max()),
                "avg_price": float(df['agile'].mean()),
                "median_price": float(df['agile'].median()),
            },
            "daily_data": [
                {
                    "time": p.date_time.isoformat(),
                    "hour": int(p.date_time.hour),
                    "agile": float(p.agile),
                    "day_ahead": float(p.day_ahead),
                }
                for p in prices
            ],
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
