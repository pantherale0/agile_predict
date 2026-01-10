"""Background task definitions for scheduled jobs."""
import logging
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pandas as pd
import numpy as np

from core.database import SessionLocal
from core.config import settings
from services.forecast_service import ForecastService
from services.price_service import PriceService
from models import History, Forecast, PriceHistory, ForecastData, AgileData, TaskLog

logger = logging.getLogger(__name__)


def log_task_execution(job_id: str, job_name: str, status: str, error_message: str = None, duration_seconds: float = None):
    """Log task execution to the database.
    
    Args:
        job_id: Unique job identifier
        job_name: Human-readable job name
        status: Job status (success, failed, running)
        error_message: Error message if job failed
        duration_seconds: Execution duration in seconds
    """
    try:
        db = SessionLocal()
        task_log = TaskLog(
            job_id=job_id,
            job_name=job_name,
            started_at=datetime.utcnow(),
            status=status,
            error_message=error_message,
            duration_seconds=duration_seconds
        )
        db.add(task_log)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Failed to log task execution: {e}")

# Constants
# UK Agile pricing regions mapping
AGILE_REGIONS = {
    'X': 'National Average',
    'A': 'Eastern England',
    'B': 'East Midlands',
    'C': 'London',
    'D': 'Merseyside and Northern Wales',
    'E': 'West Midlands',
    'F': 'North Eastern England',
    'G': 'North Western England',
    'H': 'Southern England',
    'J': 'South Eastern England',
    'K': 'Southern Wales',
    'L': 'South Western England',
    'M': 'Yorkshire',
    'N': 'Southern Scotland',
    'P': 'Northern Scotland'
}

# Job status tracking
job_status = {
    "last_update": None,
    "last_update_error": None,
    "last_latest_agile": None,
    "last_latest_agile_error": None,
    "last_clean": None,
    "last_clean_error": None,
    "last_sync_local": None,
    "last_sync_local_error": None,
}


def update_forecasts():
    """Update forecasts with latest data.
    
    This is equivalent to: python manage.py update
    Runs the ML model to generate new forecasts based on recent data.
    """
    db = None
    try:
        db = SessionLocal()
        logger.info("Starting forecast update task")
        
        # Import required modules
        from services.data_utils import model_to_df, get_latest_forecast, get_agile, day_ahead_to_agile, get_gb60
        from services.xgboost_forecast import (
            prepare_training_data,
            train_xgboost_model,
            generate_forecast_predictions,
            create_agile_predictions,
            save_forecast_to_db
        )
        
        # Get latest historical data counts
        history_count = db.query(History).count()
        forecast_count = db.query(Forecast).count()
        logger.info(f"Current database state: {history_count} history records, {forecast_count} forecasts")
        
        # Clean up old/invalid forecasts - keep the 5 most recent valid forecasts
        MIN_FORECAST_DATA = 600
        all_forecasts = db.query(Forecast).order_by(Forecast.created_at.desc()).all()
        forecasts_to_keep = []
        
        for f in all_forecasts:
            fd_count = db.query(ForecastData).filter(ForecastData.forecast_id == f.id).count()
            # Keep up to 5 recent forecasts with sufficient data
            if fd_count >= MIN_FORECAST_DATA and len(forecasts_to_keep) < 5:
                dt = pd.to_datetime(f.name).tz_localize("GB")
                days = (pd.Timestamp.now(tz="GB") - dt).days
                
                # Keep forecasts from the last 120 days
                if days < 120:
                    forecasts_to_keep.append(f.id)
        
        # Delete forecasts not in the keep list
        if all_forecasts:
            forecasts_to_delete = db.query(Forecast).filter(~Forecast.id.in_(forecasts_to_keep)).all()
            for forecast in forecasts_to_delete:
                db.delete(forecast)
            db.commit()
        logger.info(f"Cleaned up forecasts, keeping {len(forecasts_to_keep)} recent ones")
        
        # Get historical prices
        prices, start = model_to_df(db, PriceHistory)
        logger.info(f"Retrieved {len(prices)} price history records (start date: {start})")
        
        # Fetch new Agile prices (even if database is empty)
        agile = get_agile(start=start)
        day_ahead = day_ahead_to_agile(agile, reverse=True)
        
        new_prices = pd.concat([day_ahead, agile], axis=1)
        if len(prices) > 0:
            new_prices = new_prices[new_prices.index > prices.index[-1]]
        
        # Save new prices to database
        if len(new_prices) > 0:
            logger.info(f"Adding {len(new_prices)} new price records")
            
            # Remove duplicates within new_prices itself (keep first occurrence)
            new_prices_sorted = new_prices.sort_index()
            new_prices_deduped = new_prices_sorted[~new_prices_sorted.index.duplicated(keep='first')]
            duplicates_removed = len(new_prices) - len(new_prices_deduped)
            if duplicates_removed > 0:
                logger.info(f"Removed {duplicates_removed} duplicate timestamps from data source")
            
            # Convert timezone-aware index to UTC (handles DST transitions correctly)
            # The index should be Europe/London timezone-aware
            if new_prices_deduped.index.tz is not None:
                # Convert to UTC to properly distinguish DST transition duplicates
                utc_index = new_prices_deduped.index.tz_convert('UTC')
                new_prices_deduped.index = utc_index
                logger.info("Converted Europe/London timezone data to UTC")
            
            # Add records in batches
            if len(new_prices_deduped) > 0:
                batch_size = 500
                total_added = 0
                
                for i in range(0, len(new_prices_deduped), batch_size):
                    batch = new_prices_deduped.iloc[i:i+batch_size]
                    
                    try:
                        for timestamp, row in batch.iterrows():
                            price_record = PriceHistory(
                                date_time=timestamp,
                                day_ahead=row['day_ahead'],
                                agile=row['agile']
                            )
                            db.add(price_record)
                        
                        db.commit()
                        total_added += len(batch)
                        logger.info(f"Batch {i//batch_size + 1}: Added {len(batch)} records ({total_added} total)")
                    except Exception as e:
                        logger.error(f"Error in batch {i//batch_size + 1}: {e}")
                        db.rollback()
                        raise
                
                logger.info(f"Successfully added {total_added} price records (stored as UTC to preserve DST transitions)")
            
            prices = pd.concat([prices, new_prices]).sort_index()
        
        # Check if we have any prices after fetching
        if len(prices) == 0:
            logger.warning("No price data available after fetching from external sources")
            job_status["last_update"] = datetime.now()
            job_status["last_update_error"] = "No price data available"
            return
        
        agile_end = prices.index[-1]
        
        # Get GB60 future prices
        gb60 = get_gb60()
        if len(gb60) > 0:
            gb60 = gb60.resample("30min").ffill().loc[agile_end + pd.Timedelta("30min"):]
            if len(gb60) > 0:
                gb60 = gb60.reindex(
                    pd.date_range(gb60.index[0], gb60.index[-1] + pd.Timedelta("30min"), freq="30min")
                ).ffill()
                gb60 = pd.concat([gb60, day_ahead_to_agile(gb60)], axis=1).set_axis(["day_ahead", "agile"], axis=1)
                prices = pd.concat([prices, gb60]).sort_index()
                logger.info(f"Added {len(gb60)} GB60 future prices")
        
        # Generate new forecast name
        new_name = pd.Timestamp.now(tz="GB").strftime("%Y-%m-%d %H:%M")
        
        # Check if forecast already exists
        existing = db.query(Forecast).filter(Forecast.name == new_name).first()
        if existing:
            logger.info(f"Forecast {new_name} already exists, skipping")
            job_status["last_update"] = datetime.now()
            job_status["last_update_error"] = None
            return
        
        # Get latest forecast data from external APIs
        logger.info("Fetching latest forecast data from external APIs")
        fc, missing_fc = get_latest_forecast()
        
        if len(missing_fc) > 0:
            logger.error(f"Unable to run forecast due to missing columns: {', '.join(missing_fc)}")
            job_status["last_update"] = datetime.now()
            job_status["last_update_error"] = f"Missing forecast data: {', '.join(missing_fc)}"
            return
        
        if len(fc) == 0:
            logger.error("No forecast data available")
            job_status["last_update"] = datetime.now()
            job_status["last_update_error"] = "No forecast data available"
            return
        
        logger.info(f"Retrieved forecast data from {fc.index[0]} to {fc.index[-1]}")
        
        # Prepare training data (pass current forecast for initial training)
        train_X, train_y, test_X, test_y, ff_train = prepare_training_data(db, prices, current_forecast=fc)
        
        # Initialize variables for model scoring
        mean_score = 0.0
        stdev_score = 0.0
        
        if len(train_X) == 0:
            logger.warning("No training data available, generating forecast without ML model")
            logger.warning("First forecast will use simple day-ahead to agile conversion")
            
            # For the first forecast with no historical data, use a simple approach:
            # Use the mean of recent day-ahead prices as the baseline prediction
            if len(prices) > 0:
                # Use recent average as baseline
                recent_prices = prices.tail(48)  # Last 24 hours (48 half-hour periods)
                baseline_day_ahead = recent_prices["day_ahead"].mean()
                
                # Add day_ahead column to fc using baseline
                fc["day_ahead"] = baseline_day_ahead
                fc["day_ahead_low"] = baseline_day_ahead * 0.9
                fc["day_ahead_high"] = baseline_day_ahead * 1.1
                
                logger.info(f"Using baseline day-ahead price: {baseline_day_ahead:.2f}")
            else:
                # If no prices available, use a reasonable default
                fc["day_ahead"] = 50.0  # £50/MWh as default
                fc["day_ahead_low"] = 45.0
                fc["day_ahead_high"] = 55.0
                logger.warning("No price history available, using default baseline")
        else:
            # Train XGBoost model
            logger.info("Training XGBoost model")
            xg_model, scores = train_xgboost_model(train_X, train_y)
            mean_score = -np.mean(scores)
            stdev_score = np.std(scores)
            
            # Generate predictions
            logger.info("Generating forecast predictions")
            fc = generate_forecast_predictions(xg_model, fc, prices, test_X, test_y)
        
        # Create Agile predictions for all regions
        logger.info("Creating Agile price predictions for all regions")
        ag = create_agile_predictions(fc)
        
        # Save forecast to database
        logger.info("Saving forecast to database")
        forecast = save_forecast_to_db(
            db,
            new_name,
            fc,
            ag,
            mean_score=mean_score,
            stdev_score=stdev_score
        )
        
        logger.info(f"Forecast update completed successfully: {forecast.id} - {forecast.name}")
        job_status["last_update"] = datetime.now()
        job_status["last_update_error"] = None
        
    except Exception as e:
        logger.error(f"Forecast update failed: {str(e)}", exc_info=True)
        job_status["last_update_error"] = str(e)
        job_status["last_update"] = datetime.now()
        if db is not None:
            db.rollback()
    finally:
        if db is not None:
            db.close()


def update_latest_agile():
    """Update latest Agile prices.
    
    This is equivalent to: python manage.py latest_agile
    Fetches the latest Agile pricing data from external sources.
    """
    db = SessionLocal()
    try:
        logger.info("Starting latest Agile prices update task")
        
        from services.data_utils import get_agile, day_ahead_to_agile, model_to_df
        
        # Get historical prices
        prices_list = db.query(PriceHistory).all()
        prices = pd.DataFrame([
            {
                'date_time': p.date_time,
                'day_ahead': p.day_ahead,
                'agile': p.agile
            }
            for p in prices_list
        ])
        
        start = pd.Timestamp("2023-07-01", tz="GB")
        if len(prices) > 0:
            prices.index = pd.to_datetime(prices["date_time"])
            prices = prices.sort_index()
            # Localize tz-naive timestamps to UTC first, then convert to GB
            if prices.index.tz is None:
                prices.index = prices.index.tz_localize("UTC")
            prices.index = prices.index.tz_convert("GB")
            prices.drop(["date_time"], axis=1, inplace=True)
            start = prices.index[-1] + pd.Timedelta("30min")
        
        logger.info(f"Historical prices loaded. Starting from {start}")
        
        # Fetch new Agile prices
        agile = get_agile(start=start)
        day_ahead = day_ahead_to_agile(agile, reverse=True)
        
        new_prices = pd.concat([day_ahead, agile], axis=1)
        if len(prices) > 0:
            new_prices = new_prices[new_prices.index > prices.index[-1]]
        
        if len(new_prices) > 0:
            logger.info(f"Found {len(new_prices)} new price records to add")
            
            # Convert timezone-aware index to UTC for storage
            if new_prices.index.tz is not None:
                utc_index = new_prices.index.tz_convert('UTC')
                new_prices.index = utc_index
                logger.info("Converted Europe/London timezone data to UTC")
            
            # Add records in batches
            batch_size = 500
            total_added = 0
            
            for i in range(0, len(new_prices), batch_size):
                batch = new_prices.iloc[i:i+batch_size]
                
                try:
                    for timestamp, row in batch.iterrows():
                        price_record = PriceHistory(
                            date_time=timestamp,
                            day_ahead=row['day_ahead'],
                            agile=row['agile']
                        )
                        db.add(price_record)
                    
                    db.commit()
                    total_added += len(batch)
                    logger.info(f"Batch {i//batch_size + 1}: Added {len(batch)} records ({total_added} total)")
                except Exception as e:
                    logger.error(f"Error in batch {i//batch_size + 1}: {e}")
                    db.rollback()
                    raise
            
            logger.info(f"Successfully added {total_added} new price records")
        else:
            logger.info("No new price records found")
        
        job_status["last_latest_agile"] = datetime.now()
        job_status["last_latest_agile_error"] = None
        
    except Exception as e:
        logger.error("Latest Agile prices update failed: %s", str(e), exc_info=True)
        job_status["last_latest_agile_error"] = str(e)
        job_status["last_latest_agile"] = datetime.now()
        db.rollback()
    finally:
        db.close()


def update_national_agile():
    """Update national Agile data.
    
    This is equivalent to: python manage.py national_agile
    Fetches national-level Agile pricing data for all regions.
    """
    db = SessionLocal()
    try:
        logger.info("Starting national Agile data update task")
        
        from services.data_utils import day_ahead_to_agile
        
        # Get all forecast data with day_ahead prices and date_time
        forecast_data_list = db.query(
            ForecastData.forecast_id, 
            ForecastData.date_time,
            ForecastData.day_ahead
        ).all()
        
        if not forecast_data_list:
            logger.info("No forecast data available for national Agile calculation")
            job_status["last_national_agile"] = datetime.now()
            job_status["last_national_agile_error"] = None
            return
        
        # Convert to DataFrame with DatetimeIndex
        df = pd.DataFrame([
            {
                'forecast_id': fd.forecast_id,
                'date_time': fd.date_time,
                'day_ahead': fd.day_ahead
            }
            for fd in forecast_data_list
        ])
        
        # Set date_time as index and convert to Series for day_ahead_to_agile
        df.index = pd.to_datetime(df['date_time'])
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        
        # Calculate agile predictions for national region (X)
        day_ahead_series = df["day_ahead"]
        agile_series = day_ahead_to_agile(day_ahead_series, region="X")
        
        df["agile_pred"] = agile_series
        df["region"] = "X"
        
        logger.info(f"Calculating national Agile data for {df['forecast_id'].nunique()} forecasts")
        
        # Process each forecast
        records_added = 0
        for forecast_id in df["forecast_id"].unique():
            try:
                forecast_df = df[df["forecast_id"] == forecast_id].copy()
                
                # Check if forecast exists
                forecast = db.query(Forecast).filter(Forecast.id == int(forecast_id)).first()
                if not forecast:
                    logger.debug(f"Forecast {forecast_id} not found in database, skipping")
                    continue
                
                # Add national Agile data records
                for timestamp, row in forecast_df.iterrows():
                    # Check if record already exists
                    existing = db.query(AgileData).filter(
                        AgileData.forecast_id == forecast_id,
                        AgileData.date_time == timestamp,
                        AgileData.region == "X"
                    ).first()
                    
                    if not existing:
                        agile_record = AgileData(
                            forecast_id=int(forecast_id),
                            date_time=timestamp,
                            region="X",
                            agile_pred=row['agile_pred'],
                            agile_low=row['agile_pred'] * 0.95,  # Conservative bounds
                            agile_high=row['agile_pred'] * 1.05
                        )
                        db.add(agile_record)
                        records_added += 1
                
            except Exception as e:
                logger.error(f"Error processing forecast {forecast_id} for national Agile: {str(e)}", exc_info=True)
        
        # Commit all changes
        db.commit()
        logger.info(f"National Agile data update completed: {records_added} records added/updated")
        
        job_status["last_national_agile"] = datetime.now()
        job_status["last_national_agile_error"] = None
        
    except Exception as e:
        logger.error("National Agile data update failed: %s", str(e), exc_info=True)
        job_status["last_national_agile_error"] = str(e)
        job_status["last_national_agile"] = datetime.now()
        db.rollback()
    finally:
        db.close()


def clean_old_forecasts():
    """Clean old forecasts from database.
    
    This is equivalent to: python manage.py clean_forecasts
    Removes forecasts older than a specified period to keep database clean.
    """
    db = SessionLocal()
    try:
        logger.info("Starting forecast cleanup task")
        
        # Clean forecasts older than 60 days
        cutoff_date = datetime.now() - timedelta(days=60)
        
        # Query for old forecasts
        old_forecasts_query = db.query(Forecast).filter(Forecast.created_at < cutoff_date)
        
        # Get count without fetching all records
        count_to_delete = old_forecasts_query.count()
        
        if count_to_delete > 0:
            logger.info(f"Found {count_to_delete} forecasts older than {cutoff_date}")
            
            # Delete old forecasts (cascade will handle related ForecastData and AgileData)
            deleted_count = old_forecasts_query.delete(synchronize_session=False)
            db.commit()
            
            logger.info(f"Forecast cleanup completed: {deleted_count} forecasts deleted")
        else:
            logger.info("No old forecasts found to delete")
        
        job_status["last_clean"] = datetime.now()
        job_status["last_clean_error"] = None
        
    except Exception as e:
        logger.error("Forecast cleanup failed: %s", str(e))
        job_status["last_clean_error"] = str(e)
        job_status["last_clean"] = datetime.now()
        db.rollback()
    finally:
        db.close()


def _import_price_history(db: Session, price_history_df: pd.DataFrame) -> int:
    """Import price history records from HDF file.
    
    Args:
        db: Database session
        price_history_df: DataFrame containing price history data
        
    Returns:
        Number of records added
    """
    existing_timestamps = set(
        timestamp.date_time 
        for timestamp in db.query(PriceHistory.date_time).all()
    )
    new_records_df = price_history_df.drop(
        [timestamp for timestamp in price_history_df.index if timestamp in existing_timestamps]
    )
    
    records_added = 0
    for timestamp, row in new_records_df.iterrows():
        try:
            price_record = PriceHistory(
                date_time=timestamp,
                day_ahead=float(row["day_ahead"]),
                agile=float(row["agile"])
            )
            db.add(price_record)
            records_added += 1
        except Exception as e:
            logger.error(f"Error importing price history at {timestamp}: {str(e)}")
    
    return records_added


def _import_forecast_data(
    db: Session,
    forecast: Forecast,
    hdf_forecast_id: int,
    forecast_data_df: pd.DataFrame
) -> int:
    """Import forecast data records for a specific forecast.
    
    Args:
        db: Database session
        forecast: Forecast object from database
        hdf_forecast_id: Forecast ID from HDF file
        forecast_data_df: DataFrame containing all forecast data
        
    Returns:
        Number of records added
    """
    records_added = 0
    related_data_df = forecast_data_df[
        forecast_data_df["forecast_id"] == hdf_forecast_id
    ].set_index("date_time")
    
    for timestamp, row in related_data_df.iterrows():
        try:
            existing_record = db.query(ForecastData).filter(
                ForecastData.forecast_id == forecast.id,
                ForecastData.date_time == timestamp
            ).first()
            
            if not existing_record:
                forecast_data = ForecastData(
                    forecast_id=forecast.id,
                    date_time=timestamp,
                    day_ahead=float(row.get("day_ahead")) if row.get("day_ahead") is not None else None,
                    bm_wind=float(row.get("bm_wind")) if row.get("bm_wind") is not None else None,
                    solar=float(row.get("solar")) if row.get("solar") is not None else None,
                    emb_wind=float(row.get("emb_wind")) if row.get("emb_wind") is not None else None,
                    temp_2m=float(row.get("temp_2m")) if row.get("temp_2m") is not None else None,
                    wind_10m=float(row.get("wind_10m")) if row.get("wind_10m") is not None else None,
                    rad=float(row.get("rad")) if row.get("rad") is not None else None,
                    demand=float(row.get("demand")) if row.get("demand") is not None else None
                )
                db.add(forecast_data)
                records_added += 1
        except Exception as e:
            logger.error(f"Error importing forecast data at {timestamp}: {str(e)}")
    
    return records_added


def _import_agile_data(
    db: Session,
    forecast: Forecast,
    hdf_forecast_id: int,
    agile_data_df: pd.DataFrame
) -> int:
    """Import agile data records for a specific forecast.
    
    Args:
        db: Database session
        forecast: Forecast object from database
        hdf_forecast_id: Forecast ID from HDF file
        agile_data_df: DataFrame containing all agile data
        
    Returns:
        Number of records added
    """
    records_added = 0
    related_agile_df = agile_data_df[
        agile_data_df["forecast_id"] == hdf_forecast_id
    ].set_index("date_time")
    
    if len(related_agile_df) == 0:
        return 0
    
    for timestamp, row in related_agile_df.iterrows():
        for region in AGILE_REGIONS.keys():
            try:
                existing_record = db.query(AgileData).filter(
                    AgileData.forecast_id == forecast.id,
                    AgileData.date_time == timestamp,
                    AgileData.region == region
                ).first()
                
                if not existing_record:
                    agile_data = AgileData(
                        forecast_id=forecast.id,
                        date_time=timestamp,
                        region=region,
                        agile_pred=float(row.get("agile_pred")) if row.get("agile_pred") is not None else None,
                        agile_low=float(row.get("agile_low")) if row.get("agile_low") is not None else None,
                        agile_high=float(row.get("agile_high")) if row.get("agile_high") is not None else None
                    )
                    db.add(agile_data)
                    records_added += 1
            except Exception as e:
                logger.error(
                    f"Error importing agile data at {timestamp}, region {region}: {str(e)}"
                )
    
    return records_added


def sync_local_data():
    """Sync local data sources.
    
    This is equivalent to: python manage.py sync_local
    Synchronizes data with local sources by reading from HDF5 file
    and importing forecast data into the database.
    """
    db = SessionLocal()
    try:
        logger.info("Starting local data sync task")
        
        # Construct path to HDF file
        local_dir = os.path.join(os.getcwd(), settings.LOCAL_SYNC_DIR)
        hdf_path = os.path.join(local_dir, settings.LOCAL_SYNC_HDF_FILE)
        
        if not os.path.exists(hdf_path):
            logger.warning(f"HDF file not found at {hdf_path}. Skipping sync.")
            job_status["last_sync_local"] = datetime.now()
            job_status["last_sync_local_error"] = None
            return
        
        logger.info(f"Reading HDF file from {hdf_path}")
        
        # Read data from HDF file with descriptive variable names
        forecasts_df = pd.read_hdf(hdf_path, key="Forecasts").set_index("name").sort_index()
        forecast_data_df = pd.read_hdf(hdf_path, key="ForecastData")
        price_history_df = pd.read_hdf(
            hdf_path, key="PriceHistory"
        ).set_index("date_time").sort_index()[["day_ahead", "agile"]]
        agile_data_df = pd.read_hdf(hdf_path, key="AgileData")
        
        # Track statistics
        import_stats = {
            "price_history_added": 0,
            "forecasts_added": 0,
            "forecast_data_added": 0,
            "agile_data_added": 0,
        }
        
        # Import Price History
        logger.info("Importing Price History...")
        import_stats["price_history_added"] = _import_price_history(db, price_history_df)
        
        # Import Forecasts and related data
        logger.info("Importing Forecasts...")
        
        for forecast_name, forecast_row in forecasts_df.iterrows():
            try:
                # Get or create Forecast
                forecast = db.query(Forecast).filter(Forecast.name == forecast_name).first()
                if not forecast:
                    forecast = Forecast(
                        name=forecast_name,
                        created_at=forecast_row["created_at"]
                    )
                    db.add(forecast)
                    db.flush()  # Get the database-generated ID
                    import_stats["forecasts_added"] += 1
                
                # Use the HDF file's forecast_id to find related data
                hdf_forecast_id = forecast_row["id"]
                
                # Import ForecastData for this forecast
                import_stats["forecast_data_added"] += _import_forecast_data(
                    db, forecast, hdf_forecast_id, forecast_data_df
                )
                
                # Import AgileData for this forecast
                import_stats["agile_data_added"] += _import_agile_data(
                    db, forecast, hdf_forecast_id, agile_data_df
                )
                
            except Exception as e:
                logger.error(f"Error processing forecast {forecast_name}: {str(e)}")
        
        # Commit all changes at once
        db.commit()
        logger.info(f"Price History: {import_stats['price_history_added']} records added")
        
        logger.info(
            f"Sync completed - Forecasts: {import_stats['forecasts_added']}, "
            f"ForecastData: {import_stats['forecast_data_added']}, "
            f"AgileData: {import_stats['agile_data_added']}"
        )
        
        job_status["last_sync_local"] = datetime.now()
        job_status["last_sync_local_error"] = None
        
    except Exception as e:
        logger.error(f"Local data sync failed: {str(e)}")
        job_status["last_sync_local_error"] = str(e)
        job_status["last_sync_local"] = datetime.now()
        try:
            db.rollback()
        except Exception:
            pass  # Ignore rollback errors if nothing to rollback
    finally:
        db.close()


def configure_scheduled_jobs(scheduler: BackgroundScheduler):
    """Configure all scheduled background jobs.
    
    Args:
        scheduler: APScheduler BackgroundScheduler instance
    """
    # Update latest Agile prices every 30 minutes
    scheduler.add_job(
        update_latest_agile,
        trigger=IntervalTrigger(minutes=30),
        id="update_latest_agile",
        name="Update Latest Agile Prices",
        misfire_grace_time=60,
        coalesce=True,
    )
    logger.info("Scheduled: Update Latest Agile (every 30 minutes)")
    
    # Update forecasts daily at 01:00 AM
    scheduler.add_job(
        update_forecasts,
        trigger=CronTrigger(hour=1, minute=0),
        id="update_forecasts",
        name="Update Forecasts",
        misfire_grace_time=600,
        coalesce=True,
    )
    logger.info("Scheduled: Update Forecasts (daily at 01:00)")
    
    # Update national Agile data every hour
    scheduler.add_job(
        update_national_agile,
        trigger=IntervalTrigger(hours=1),
        id="update_national_agile",
        name="Update National Agile Data",
        misfire_grace_time=300,
        coalesce=True,
    )
    logger.info("Scheduled: Update National Agile (every hour)")
    
    # Clean old forecasts daily at 02:00 AM
    scheduler.add_job(
        clean_old_forecasts,
        trigger=CronTrigger(hour=2, minute=0),
        id="clean_forecasts",
        name="Clean Old Forecasts",
        misfire_grace_time=600,
        coalesce=True,
    )
    logger.info("Scheduled: Clean Forecasts (daily at 02:00)")
    
    # Sync local data every 6 hours
    scheduler.add_job(
        sync_local_data,
        trigger=IntervalTrigger(hours=6),
        id="sync_local",
        name="Sync Local Data",
        misfire_grace_time=300,
        coalesce=True,
    )
    logger.info("Scheduled: Sync Local Data (every 6 hours)")
