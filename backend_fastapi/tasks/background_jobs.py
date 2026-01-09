"""Background task definitions for scheduled jobs."""
import logging
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pandas as pd

from core.database import SessionLocal
from core.config import settings
from services.forecast_service import ForecastService
from services.price_service import PriceService
from models import History, Forecast, PriceHistory, ForecastData, AgileData

logger = logging.getLogger(__name__)

# Constants
AGILE_REGIONS = ["G", "X"]

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
    try:
        db = SessionLocal()
        logger.info("Starting forecast update task")
        
        # Get latest historical data
        history_count = db.query(History).count()
        forecast_count = db.query(Forecast).count()
        
        logger.info("Forecast update: %s history records, %s forecasts", history_count, forecast_count)
        
        # TODO: Implement actual forecast generation using XGBoost model
        # For now, just log the operation
        logger.info("Forecast update completed successfully")
        job_status["last_update"] = datetime.now()
        job_status["last_update_error"] = None
        
    except Exception as e:
        logger.error("Forecast update failed: %s", str(e))
        job_status["last_update_error"] = str(e)
        job_status["last_update"] = datetime.now()
    finally:
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
        
        # TODO: Implement actual forecast deletion
        # old_forecasts = db.query(Forecast).filter(Forecast.created_at < cutoff_date).delete()
        
        logger.info("Forecast cleanup completed successfully")
        job_status["last_clean"] = datetime.now()
        job_status["last_clean_error"] = None
        
    except Exception as e:
        logger.error("Forecast cleanup failed: %s", str(e))
        job_status["last_clean_error"] = str(e)
        job_status["last_clean"] = datetime.now()
    finally:
        db.close()


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
        
        # Read data from HDF file
        ff = pd.read_hdf(hdf_path, key="Forecasts").set_index("name").sort_index()
        fd = pd.read_hdf(hdf_path, key="ForecastData")
        ph = pd.read_hdf(hdf_path, key="PriceHistory").set_index("date_time").sort_index()[["day_ahead", "agile"]]
        ad = pd.read_hdf(hdf_path, key="AgileData")
        
        # Track statistics
        stats = {
            "price_history_added": 0,
            "forecasts_added": 0,
            "forecast_data_added": 0,
            "agile_data_added": 0,
        }
        
        # Import Price History
        logger.info("Importing Price History...")
        model_ph_set = set(x.date_time for x in db.query(PriceHistory.date_time).all())
        ph = ph.drop([i for i in ph.index if i in model_ph_set])
        
        for index, row in ph.iterrows():
            try:
                new_ph = PriceHistory(
                    date_time=index,
                    day_ahead=row["day_ahead"],
                    agile=row["agile"]
                )
                db.add(new_ph)
                stats["price_history_added"] += 1
            except Exception as e:
                logger.error(f"Error importing price history at {index}: {str(e)}")
        
        # Import Forecasts and related data
        logger.info("Importing Forecasts...")
        
        for index, row in ff.iterrows():
            try:
                # Get or create Forecast
                ff_obj = db.query(Forecast).filter(Forecast.name == index).first()
                if not ff_obj:
                    ff_obj = Forecast(
                        name=index,
                        created_at=row["created_at"]
                    )
                    db.add(ff_obj)
                    db.flush()  # Get the ID
                    stats["forecasts_added"] += 1
                
                # Use the HDF file's forecast_id to find related data
                hdf_forecast_id = row["id"]
                
                # Import ForecastData for this forecast
                df = fd[fd["forecast_id"] == hdf_forecast_id].set_index("date_time")
                for fd_index, fd_row in df.iterrows():
                    try:
                        existing_fd = db.query(ForecastData).filter(
                            ForecastData.forecast_id == ff_obj.id,
                            ForecastData.date_time == fd_index
                        ).first()
                        
                        if not existing_fd:
                            new_fd = ForecastData(
                                forecast_id=ff_obj.id,
                                date_time=fd_index,
                                day_ahead=fd_row.get("day_ahead"),
                                bm_wind=fd_row.get("bm_wind"),
                                solar=fd_row.get("solar"),
                                emb_wind=fd_row.get("emb_wind"),
                                temp_2m=fd_row.get("temp_2m"),
                                wind_10m=fd_row.get("wind_10m"),
                                rad=fd_row.get("rad"),
                                demand=fd_row.get("demand")
                            )
                            db.add(new_fd)
                            stats["forecast_data_added"] += 1
                    except Exception as e:
                        logger.error(f"Error importing forecast data for {index} at {fd_index}: {str(e)}")
                
                # Import AgileData for this forecast
                agile_df = ad[ad["forecast_id"] == hdf_forecast_id].set_index("date_time")
                if len(agile_df) > 0:
                    for ad_index, ad_row in agile_df.iterrows():
                        # Import for all configured regions
                        for region in AGILE_REGIONS:
                            try:
                                existing_ad = db.query(AgileData).filter(
                                    AgileData.forecast_id == ff_obj.id,
                                    AgileData.date_time == ad_index,
                                    AgileData.region == region
                                ).first()
                                
                                if not existing_ad:
                                    new_ad = AgileData(
                                        forecast_id=ff_obj.id,
                                        date_time=ad_index,
                                        region=region,
                                        agile_pred=ad_row.get("agile_pred"),
                                        agile_low=ad_row.get("agile_low"),
                                        agile_high=ad_row.get("agile_high")
                                    )
                                    db.add(new_ad)
                                    stats["agile_data_added"] += 1
                            except Exception as e:
                                logger.error(f"Error importing agile data for {index} at {ad_index}, region {region}: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error processing forecast {index}: {str(e)}")
        
        # Commit all forecast-related changes at once
        db.commit()
        logger.info(f"Price History: {stats['price_history_added']} records added")
        
        logger.info(f"Sync completed - Forecasts: {stats['forecasts_added']}, "
                   f"ForecastData: {stats['forecast_data_added']}, "
                   f"AgileData: {stats['agile_data_added']}")
        
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
