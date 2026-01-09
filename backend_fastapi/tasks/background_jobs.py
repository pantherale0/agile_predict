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
from models import History, Forecast, PriceHistory, ForecastData, AgileData

logger = logging.getLogger(__name__)

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
        
        # Clean up old/invalid forecasts
        MIN_FORECAST_DATA = 600
        forecasts_to_keep = []
        
        for f in db.query(Forecast).order_by(Forecast.created_at.desc()).all():
            fd_count = db.query(ForecastData).filter(ForecastData.forecast_id == f.id).count()
            if fd_count >= MIN_FORECAST_DATA:
                dt = pd.to_datetime(f.name).tz_localize("GB")
                days = (pd.Timestamp.now(tz="GB") - dt).days
                
                # Keep forecasts from specific hours within 120 days
                if days < 120:
                    for hour in [6, 10, 11, 16, 22]:
                        if f"{hour:02d}:15" in f.name:
                            forecasts_to_keep.append(f.id)
                            break
        
        # Delete forecasts not in the keep list
        forecasts_to_delete = db.query(Forecast).filter(~Forecast.id.in_(forecasts_to_keep)).all()
        for forecast in forecasts_to_delete:
            db.delete(forecast)
        db.commit()
        logger.info(f"Cleaned up forecasts, keeping {len(forecasts_to_keep)}")
        
        # Get historical prices
        prices, start = model_to_df(db, PriceHistory)
        logger.info(f"Retrieved {len(prices)} price history records")
        
        if len(prices) == 0:
            logger.warning("No historical prices available")
            job_status["last_update"] = datetime.now()
            job_status["last_update_error"] = None
            return
        
        # Fetch new Agile prices
        agile = get_agile(start=start)
        day_ahead = day_ahead_to_agile(agile, reverse=True)
        
        new_prices = pd.concat([day_ahead, agile], axis=1)
        if len(prices) > 0:
            new_prices = new_prices[new_prices.index > prices.index[-1]]
        
        # Save new prices to database
        if len(new_prices) > 0:
            logger.info(f"Adding {len(new_prices)} new price records")
            for timestamp, row in new_prices.iterrows():
                try:
                    price_record = PriceHistory(
                        date_time=timestamp,
                        day_ahead=row["day_ahead"],
                        agile=row["agile"]
                    )
                    db.add(price_record)
                except Exception as e:
                    logger.error(f"Error saving price at {timestamp}: {e}")
            db.commit()
            prices = pd.concat([prices, new_prices]).sort_index()
        
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
        
        # Prepare training data
        train_X, train_y, test_X, test_y, ff_train = prepare_training_data(db, prices)
        
        if len(train_X) == 0:
            logger.warning("No training data available, cannot generate forecast")
            job_status["last_update"] = datetime.now()
            job_status["last_update_error"] = "No training data available"
            return
        
        # Train XGBoost model
        logger.info("Training XGBoost model")
        xg_model, scores = train_xgboost_model(train_X, train_y)
        
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
            mean_score=-np.mean(scores),
            stdev_score=np.std(scores)
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
    try:
        db = SessionLocal()
        logger.info("Starting latest Agile prices update task")
        
        # Get current price count
        current_prices = db.query(PriceHistory).count()
        
        # TODO: Implement actual Agile price fetching
        # For now, just log the operation
        logger.info("Latest Agile prices updated: %s total records", current_prices)
        job_status["last_latest_agile"] = datetime.now()
        job_status["last_latest_agile_error"] = None
        
    except Exception as e:
        logger.error("Latest Agile prices update failed: %s", str(e))
        job_status["last_latest_agile_error"] = str(e)
        job_status["last_latest_agile"] = datetime.now()
    finally:
        db.close()


def update_national_agile():
    """Update national Agile data.
    
    This is equivalent to: python manage.py national_agile
    Fetches national-level Agile pricing data.
    """
    try:
        logger.info("Starting national Agile data update task")
        
        # TODO: Implement actual national Agile data fetching
        logger.info("National Agile data updated successfully")
        
    except Exception as e:
        logger.error("National Agile data update failed: %s", str(e))


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
                day_ahead=row["day_ahead"],
                agile=row["agile"]
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
                    day_ahead=row.get("day_ahead"),
                    bm_wind=row.get("bm_wind"),
                    solar=row.get("solar"),
                    emb_wind=row.get("emb_wind"),
                    temp_2m=row.get("temp_2m"),
                    wind_10m=row.get("wind_10m"),
                    rad=row.get("rad"),
                    demand=row.get("demand")
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
                        agile_pred=row.get("agile_pred"),
                        agile_low=row.get("agile_low"),
                        agile_high=row.get("agile_high")
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
