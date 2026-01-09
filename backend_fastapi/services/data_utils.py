"""Utility functions for data fetching and processing."""
import pandas as pd
import numpy as np
import requests
import time
import logging
from datetime import datetime
from http import HTTPStatus
from requests.exceptions import HTTPError
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session

from models import PriceHistory

logger = logging.getLogger(__name__)

# Constants
OCTOPUS_PRODUCT_URL = "https://api.octopus.energy/v1/products/"
RETRIES = 3
RETRY_CODES = [
    HTTPStatus.TOO_MANY_REQUESTS,
    HTTPStatus.INTERNAL_SERVER_ERROR,
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
    HTTPStatus.GATEWAY_TIMEOUT,
]

# UK Agile pricing regions mapping with conversion factors
REGIONS = {
    'X': {'name': 'National Average', 'factors': (0.2136, 12.21)},
    'A': {'name': 'Eastern England', 'factors': (0.21, 13)},
    'B': {'name': 'East Midlands', 'factors': (0.20, 14)},
    'C': {'name': 'London', 'factors': (0.22, 12)},
    'D': {'name': 'Merseyside and Northern Wales', 'factors': (0.21, 13)},
    'E': {'name': 'West Midlands', 'factors': (0.21, 13)},
    'F': {'name': 'North Eastern England', 'factors': (0.20, 14)},
    'G': {'name': 'North Western England', 'factors': (0.21, 13)},
    'H': {'name': 'Southern England', 'factors': (0.22, 12)},
    'J': {'name': 'South Eastern England', 'factors': (0.22, 12)},
    'K': {'name': 'Southern Wales', 'factors': (0.21, 13)},
    'L': {'name': 'South Western England', 'factors': (0.21, 13)},
    'M': {'name': 'Yorkshire', 'factors': (0.20, 14)},
    'N': {'name': 'Southern Scotland', 'factors': (0.20, 14)},
    'P': {'name': 'Northern Scotland', 'factors': (0.19, 15)},
}


class DataSet:
    """Class for downloading and processing data from external APIs."""
    
    def __init__(self, *args, **kwargs) -> None:
        self.params = kwargs.pop("params", {})
        self.tz = kwargs.pop("tz", "UTC")
        # Set all other kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

    def download(self, tz="GB", params=None) -> Tuple[pd.DataFrame, Optional[int]]:
        """Download data from the configured URL.
        
        Args:
            tz: Timezone for the data
            params: Additional parameters (unused, kept for compatibility)
            
        Returns:
            Tuple of (DataFrame, error_code)
        """
        logger.info(f"    Downloading from {self.url}")
        
        for n in range(RETRIES):
            try:
                response = requests.get(url=self.url, params=self.params)
                response.raise_for_status()
                code = None
                break
            except HTTPError as exc:
                code = exc.response.status_code
                if code in RETRY_CODES:
                    time.sleep(n + 1)
                    continue
                logger.error(f"HTTP error {code} for URL {self.url}")
                return pd.DataFrame(), code
        else:
            logger.error(f"Failed after {RETRIES} retries for URL {self.url}")
            return pd.DataFrame(), code

        try:
            df = pd.json_normalize(response.json(), self.record_path)
        except Exception:
            try:
                df = pd.DataFrame(response.json()[self.record_path[0]])
            except Exception as e:
                logger.error(f"Error parsing JSON for URL {self.url}: {e}")
                return pd.DataFrame(), code

        # Process the dataframe index
        try:
            df.index = pd.to_datetime(df[self.date_col])
            if df.index.tzinfo is None:
                df.index = df.index.tz_localize(self.tz, ambiguous="infer")
        except Exception as e:
            logger.error(f"Error setting datetime index: {e}")

        # Handle Settlement Period if present
        try:
            df.index = pd.to_datetime(df["Date"]) + (df["Settlement_period"] - 1) * pd.Timedelta("30min")
            df.index = df.index.tz_localize("UTC")
        except Exception:
            pass

        # Handle time column if present
        try:
            if hasattr(self, 'time_col'):
                df.index += pd.to_datetime(df[self.time_col].str[:5], format="%H:%M") - pd.Timestamp("1900-01-01")
        except Exception:
            pass

        # Handle period column if present
        try:
            if hasattr(self, 'period_col'):
                df.index += (df[self.period_col] - 1) * pd.Timedelta("30min")
        except Exception:
            pass

        # Convert timezone
        try:
            df.index = df.index.tz_convert(tz)
        except Exception:
            pass

        # Select columns
        try:
            df = df[self.cols]
        except Exception:
            pass

        # Resample if needed
        try:
            if hasattr(self, 'func'):
                df = df.resample(self.resample).aggregate(self.func)
            elif hasattr(self, 'resample'):
                df = df.resample(self.resample).mean()
        except Exception as e:
            logger.error(f"Error resampling: {e}")

        # Interpolate
        try:
            df = df.interpolate()
        except Exception:
            pass

        # Sort by column if specified
        try:
            if hasattr(self, 'sort_col'):
                df = df.sort_values(self.sort_col)
        except Exception:
            pass

        # Rename columns/series
        if isinstance(df, pd.DataFrame):
            try:
                if hasattr(self, 'rename'):
                    df = df.set_axis(self.rename, axis=1)
            except Exception:
                pass
        elif isinstance(df, pd.Series):
            try:
                if hasattr(self, 'rename'):
                    df = df.rename(self.rename)
            except Exception:
                pass

        df = df.sort_index()
        df = df[~df.index.duplicated()]
        return df, None


def get_gb60() -> pd.Series:
    """Fetch GB60 day-ahead prices from Nord Pool API.
    
    Returns:
        Series with day-ahead prices indexed by datetime
    """
    # Calculate delivery date (typically tomorrow)
    delivery_date = (pd.Timestamp.now() + pd.Timedelta("13h")).strftime("%Y-%m-%d")
    
    url = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"
    params = {
        "date": delivery_date,
        "market": "GbHalfHour_DayAhead",
        "deliveryArea": "UK",
        "currency": "GBP",
    }
    
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching GB60 data from {url}: {e}")
        return pd.Series([], dtype=float, index=pd.DatetimeIndex([]))
    
    try:
        data = r.json()
        
        # Parse the response structure - expecting multiAreaEntries
        if "multiAreaEntries" in data:
            price = pd.Series({
                pd.Timestamp(row["deliveryStart"]).tz_convert("GB"): float(row["entryPerArea"]["UK"])
                for row in data["multiAreaEntries"]
            })
            return price
        
        # If structure is different, log and return empty
        logger.warning(f"Unexpected GB60 data structure: {data}")
        return pd.Series([], dtype=float, index=pd.DatetimeIndex([]))
        
    except Exception as e:
        logger.error(f"Error parsing GB60 data: {e}")
        return pd.Series([], dtype=float, index=pd.DatetimeIndex([]))


def get_agile(start=pd.Timestamp("2023-07-01"), tz="GB", region="G") -> pd.Series:
    """Fetch Agile pricing data from Octopus Energy API.
    
    Args:
        start: Start date for fetching data
        tz: Timezone for the data
        region: Region code (A-P, X for national average)
        
    Returns:
        Series with Agile prices indexed by datetime
    """
    start = pd.Timestamp(start).tz_convert("UTC")
    product = "AGILE-24-10-01"
    url = f"{OCTOPUS_PRODUCT_URL}{product}"
    
    end = pd.Timestamp.now(tz="UTC").normalize() + pd.Timedelta("48h")
    code = f"E-1R-{product}-{region}"
    url = url + f"/electricity-tariffs/{code}/standard-unit-rates/"
    
    x = []
    while end > start:
        params = {
            "page_size": 1500,
            "order_by": "period",
            "period_from": datetime(
                year=pd.Timestamp(start).year,
                month=pd.Timestamp(start).month,
                day=pd.Timestamp(start).day,
            ),
            "period_to": datetime(
                year=pd.Timestamp(end).year,
                month=pd.Timestamp(end).month,
                day=pd.Timestamp(end).day,
            ),
        }
        
        try:
            r = requests.get(url, params=params)
            if r.status_code == 200 and r.text and "results" in r.json():
                data = r.json()["results"]
                if data:
                    x = x + data
                    end = pd.Timestamp(x[-1]["valid_from"]).ceil("24h")
                else:
                    break
            else:
                break
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing Agile response: {e}")
            break
    
    if not x:
        return pd.Series([], dtype=float, index=pd.DatetimeIndex([]), name="agile")
    
    df = pd.DataFrame(x).set_index("valid_from")[["value_inc_vat"]]
    df.index = pd.to_datetime(df.index)
    df.index = df.index.tz_convert(tz)
    df = df.sort_index()["value_inc_vat"]
    df = df[~df.index.duplicated()]
    return df.rename("agile")


def day_ahead_to_agile(df: pd.Series, reverse: bool = False, region: str = "G") -> pd.Series:
    """Convert between day-ahead and Agile prices using regional factors.
    
    Args:
        df: Series with prices to convert
        reverse: If True, convert from Agile to day-ahead, otherwise day-ahead to Agile
        region: Region code (A-P, X for national average)
        
    Returns:
        Series with converted prices
    """
    if df.empty:
        name = "day_ahead" if reverse else "agile"
        return pd.Series([], dtype=float, index=pd.DatetimeIndex([]), name=name)
    
    df.index = df.index.tz_convert("GB")
    x = pd.DataFrame(df).set_axis(["In"], axis=1)
    x["Out"] = x["In"]
    x["Peak"] = (x.index.hour >= 16) & (x.index.hour < 19)
    
    factor, offset = REGIONS[region]["factors"]
    
    if reverse:
        x.loc[x["Peak"], "Out"] -= offset
        x["Out"] /= factor
    else:
        x["Out"] *= factor
        x.loc[x["Peak"], "Out"] += offset
    
    name = "day_ahead" if reverse else "agile"
    return x["Out"].rename(name)


def get_latest_forecast() -> Tuple[pd.DataFrame, List[str]]:
    """Fetch latest forecast data from external APIs.
    
    Returns:
        Tuple of (DataFrame with forecast data, list of missing columns)
    """
    ndf_from = pd.Timestamp.now().normalize().strftime("%Y-%m-%d")
    ndf_to = (pd.Timestamp.now().normalize() + pd.Timedelta("24h")).strftime("%Y-%m-%d")
    
    forecast_data = [
        {
            "url": "https://api.neso.energy/api/3/action/datastore_search?resource_id=93c3048e-1dab-4057-a2a9-417540583929&limit=1000",
            "record_path": ["result", "records"],
            "tz": "UTC",
            "date_col": "Datetime",
            "cols": ["Wind_Forecast"],
            "rename": ["bm_wind"],
        },
        {
            "url": "https://api.neso.energy/api/3/action/datastore_search?resource_id=b2f03146-f05d-4824-a663-3a4f36090c71&limit=1000",
            "record_path": ["result", "records"],
            "tz": "UTC",
            "date_col": "Datetime_GMT",
            "cols": ["Incentive_forecast"],
            "rename": ["da_wind"],
        },
        {
            "url": "https://api.neso.energy/api/3/action/datastore_search?resource_id=db6c038f-98af-4570-ab60-24d71ebd0ae5&limit=1000",
            "record_path": ["result", "records"],
            "tz": "UTC",
            "cols": ["EMBEDDED_SOLAR_FORECAST", "EMBEDDED_WIND_FORECAST"],
            "rename": ["solar", "emb_wind"],
            "date_col": "DATE_GMT",
            "time_col": "TIME_GMT",
        },
        {
            "url": "https://api.neso.energy/api/3/action/datastore_search?resource_id=7c0411cd-2714-4bb5-a408-adb065edf34d&limit=5000",
            "record_path": ["result", "records"],
            "date_col": "GDATETIME",
            "tz": "UTC",
            "cols": ["NATIONALDEMAND"],
        },
        {
            "url": "https://api.open-meteo.com/v1/forecast",
            "params": {
                "latitude": 54.0,
                "longitude": 2.3,
                "current": "temperature_2m",
                "minutely_15": ["temperature_2m", "wind_speed_10m", "direct_radiation"],
                "forecast_days": 14,
            },
            "date_col": "time",
            "tz": "UTC",
            "resample": "30min",
            "record_path": ["minutely_15"],
            "cols": ["temperature_2m", "wind_speed_10m", "direct_radiation"],
            "rename": ["temp_2m", "wind_10m", "rad"],
        },
        {
            "url": "https://data.elexon.co.uk/bmrs/api/v1/datasets/NDF",
            "params": {"publishDateTimeFrom": ndf_from, "publishDateTimeTo": ndf_to},
            "record_path": ["data"],
            "date_col": "startTime",
            "cols": "demand",
            "sort_col": "publishTime",
        },
    ]
    
    downloaded_data = []
    download_errors = []
    
    for x in forecast_data:
        data, e = DataSet(**x).download()
        if len(data) > 0:
            downloaded_data.append(data)
        else:
            download_errors.append(e)
    
    if not downloaded_data:
        logger.error("No forecast data downloaded")
        return pd.DataFrame(), ["all"]
    
    df = pd.concat(downloaded_data, axis=1)
    
    # Merge demand columns if both are present
    demand_cols = ["demand", "NATIONALDEMAND"]
    if all([c in df.columns for c in demand_cols]):
        df["demand"] = df[demand_cols].mean(axis=1)
        df.drop(["NATIONALDEMAND"], axis=1, inplace=True)
        missing_cols = []
    elif "NATIONALDEMAND" not in df.columns:
        missing_cols = ["NATIONALDEMAND"]
    else:
        missing_cols = []
    
    # Merge wind forecast data
    if "da_wind" in df.columns and "bm_wind" in df.columns:
        df.loc[df["da_wind"] > 0, "bm_wind"] = df["da_wind"]
        df.drop("da_wind", axis=1, inplace=True)
    
    # Check for all required columns
    all_cols = ["emb_wind", "bm_wind", "solar", "demand", "temp_2m", "wind_10m", "rad"]
    missing_cols += [c for c in all_cols if c not in df.columns]
    
    if len(missing_cols) > 0:
        logger.error(f"Missing forecast data columns: {missing_cols}")
        return pd.DataFrame(), missing_cols
    
    # Add time features
    df["date_time"] = pd.to_datetime(df.index)
    df["time"] = df["date_time"].dt.hour + df["date_time"].dt.minute / 60
    df["day_of_week"] = df["date_time"].dt.day_of_week.astype(int)
    
    df.index = pd.to_datetime(df.index).tz_convert("GB")
    df.drop(["date_time"], axis=1, inplace=True)
    
    return df.sort_index().dropna(), missing_cols


def model_to_df(db: Session, model_class) -> Tuple[pd.DataFrame, pd.Timestamp]:
    """Convert SQLAlchemy model to DataFrame.
    
    Args:
        db: Database session
        model_class: SQLAlchemy model class to query
        
    Returns:
        Tuple of (DataFrame, start_timestamp)
    """
    from sqlalchemy import inspect
    
    records = db.query(model_class).all()
    start = pd.Timestamp("2023-07-01", tz="GB")
    
    if not records:
        return pd.DataFrame(), start
    
    # Get column names from the model using SQLAlchemy inspection
    columns = [c.name for c in inspect(model_class).columns if c.name not in ['id']]
    
    # Convert records to list of dictionaries
    df = pd.DataFrame([{col: getattr(r, col) for col in columns} for r in records])
    
    df.index = pd.to_datetime(df["date_time"])
    df = df.sort_index()
    # Localize as UTC first (data is stored as UTC-naive in DB but represents UTC times)
    # then convert to GB timezone
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("GB")
    df.drop(["date_time"], axis=1, inplace=True, errors='ignore')
    
    start = df.index[-1] + pd.Timedelta("30min")
    return df, start
