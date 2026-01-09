"""XGBoost-based forecast generation and training."""
import logging
import numpy as np
import pandas as pd
import xgboost as xg
from datetime import datetime
from sqlalchemy.orm import Session
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.neighbors import KernelDensity
from typing import Tuple, Dict, Optional

from models import Forecast, ForecastData, AgileData, PriceHistory
from services.data_utils import REGIONS, day_ahead_to_agile

logger = logging.getLogger(__name__)

# Training constants
MAX_DAYS = 60  # Maximum age of forecast data to use in training
MAX_TEST_X = 20000  # Maximum test samples to use

# Sample weight calculation constants
# Used to emphasize extreme values in model training
SAMPLE_WEIGHT_OFFSET = 10  # Offset to avoid log(0)
SAMPLE_WEIGHT_SCALE = 5    # Scale factor for log transformation
SAMPLE_WEIGHT_SHIFT = 4    # Shift to adjust weight range

MODEL_FEATURES = [
    "bm_wind",
    "solar",
    "demand",
    "peak",
    "days_ago",
    "wind_10m",
    "weekend",
]


def kde_quantiles(
    kde: KernelDensity,
    dt: list,
    pred: list,
    quantiles: Dict[str, float] = {"low": 0.1, "mid": 0.5, "high": 0.9},
    lim: Tuple[float, float] = (0, 150)
) -> Dict[str, list]:
    """Calculate quantiles using Kernel Density Estimation.
    
    Args:
        kde: Fitted KernelDensity model
        dt: Days ahead values
        pred: Predicted values
        quantiles: Dictionary of quantile names and values
        lim: Price range limits for KDE
        
    Returns:
        Dictionary with quantile names as keys and lists of quantile values
    """
    if not isinstance(dt, list):
        dt = [dt]
    if not isinstance(pred, list):
        pred = [pred]
    
    results = {q: [] for q in quantiles}
    for dt1, pred1 in zip(dt, pred):
        x = np.array([[dt1, pred1, p] for p in range(int(lim[0]), int(lim[1]))])
        c = pd.Series(index=x[:, 2], data=np.exp(kde.score_samples(x)).cumsum())
        c /= c.iloc[-1]
        
        for q in quantiles:
            if len(c[c < quantiles[q]]) > 0:
                idx = c[c < quantiles[q]].index[-1]
                results[q] += [(quantiles[q] - c[idx]) / (c[idx + 1] - c[idx]) + idx]
            else:
                results[q] += [np.nan]
    
    return results


def prepare_training_data(
    db: Session,
    prices: pd.DataFrame,
    max_days: int = MAX_DAYS,
    ignore_forecast_ids: list = None
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame]:
    """Prepare training and test data from historical forecasts.
    
    Args:
        db: Database session
        prices: DataFrame with historical prices
        max_days: Maximum age of forecast data to use
        ignore_forecast_ids: List of forecast IDs to exclude
        
    Returns:
        Tuple of (train_X, train_y, test_X, test_y, ff_train)
    """
    if ignore_forecast_ids is None:
        ignore_forecast_ids = []
    
    # Get all forecasts (excluding ignored ones)
    forecasts = db.query(Forecast).filter(
        ~Forecast.id.in_(ignore_forecast_ids)
    ).order_by(Forecast.created_at.desc()).all()
    
    if not forecasts:
        logger.warning("No forecasts found for training")
        return pd.DataFrame(), pd.Series(), pd.DataFrame(), pd.Series(), pd.DataFrame()
    
    # Get forecast data
    forecast_data_records = db.query(ForecastData).filter(
        ~ForecastData.forecast_id.in_(ignore_forecast_ids)
    ).all()
    
    if not forecast_data_records:
        logger.warning("No forecast data found for training")
        return pd.DataFrame(), pd.Series(), pd.DataFrame(), pd.Series(), pd.DataFrame()
    
    # Convert to DataFrames
    fd = pd.DataFrame([{
        'forecast_id': r.forecast_id,
        'date_time': r.date_time,
        'bm_wind': r.bm_wind,
        'solar': r.solar,
        'emb_wind': r.emb_wind,
        'temp_2m': r.temp_2m,
        'wind_10m': r.wind_10m,
        'rad': r.rad,
        'demand': r.demand,
    } for r in forecast_data_records])
    
    ff = pd.DataFrame([{
        'id': f.id,
        'name': f.name,
        'created_at': f.created_at,
        'mean': f.mean,
        'stdev': f.stdev,
    } for f in forecasts])
    
    ff = ff.set_index("id").sort_index()
    ff["created_at"] = pd.to_datetime(ff["name"]).dt.tz_localize("GB")
    ff["date"] = ff["created_at"].dt.tz_convert("GB").dt.normalize()
    ff["ag_start"] = ff["created_at"].dt.normalize() + pd.Timedelta(hours=22)
    ff["ag_end"] = ff["created_at"].dt.normalize() + pd.Timedelta(hours=46)
    
    # Select forecasts closest to 16:15 for training
    ff["dt1600"] = (
        (ff["date"] + pd.Timedelta(hours=16, minutes=15) - ff["created_at"].dt.tz_convert("GB"))
        .dt.total_seconds()
        .abs()
    )
    ff_train = (
        ff.sort_values("dt1600")
        .drop_duplicates("date")
        .sort_index()
        .drop(["date", "dt1600"], axis=1)
    )
    
    # Merge forecast data with forecast metadata
    df = (
        fd.merge(ff, right_index=True, left_on="forecast_id")
        .set_index("date_time")
    )
    
    # Add time-based features
    df["dow"] = df.index.day_of_week
    df["weekend"] = (df.index.day_of_week >= 5).astype(int)
    df["time"] = df.index.tz_convert("GB").hour + df.index.minute / 60
    df["days_ago"] = (pd.Timestamp.now(tz="UTC") - df["created_at"]).dt.total_seconds() / 3600 / 24
    df["dt"] = (df.index - df["created_at"]).dt.total_seconds() / 3600 / 24
    df["peak"] = ((df["time"] >= 16) & (df["time"] < 19)).astype(float)
    
    # Prepare training data (only forecasts closest to 16:15)
    train_X = df[df["forecast_id"].isin(ff_train.index)]
    train_X = train_X[train_X["days_ago"] < max_days]
    train_X = train_X[MODEL_FEATURES]
    
    # Merge with prices
    train_X = train_X.merge(prices["day_ahead"], left_index=True, right_index=True, how="left")
    train_X = train_X.dropna(subset=["day_ahead"])
    
    if len(train_X) == 0:
        logger.warning("No training data available after filtering")
        return pd.DataFrame(), pd.Series(), pd.DataFrame(), pd.Series(), ff_train
    
    train_y = train_X.pop("day_ahead")
    
    # Prepare test data (other forecasts)
    test_X = df[~df["forecast_id"].isin(ff_train.index)]
    test_X = test_X[test_X.index > test_X["ag_start"]]
    test_X = test_X[test_X["days_ago"] < max_days]
    test_X = test_X.merge(prices["day_ahead"], left_index=True, right_index=True)
    test_y = test_X["day_ahead"]
    
    # Limit test set size
    if len(test_X) > MAX_TEST_X:
        # Keep a random sample of MAX_TEST_X samples
        samples_to_keep = min(MAX_TEST_X, len(test_X))
        test_X, _, test_y, _ = train_test_split(
            test_X, test_y, 
            train_size=samples_to_keep, 
            random_state=42
        )
    
    logger.info(f"Training data: {len(train_X)} samples, Test data: {len(test_X)} samples")
    
    return train_X, train_y, test_X, test_y, ff_train


def train_xgboost_model(
    train_X: pd.DataFrame,
    train_y: pd.Series
) -> Tuple[xg.XGBRegressor, np.ndarray]:
    """Train XGBoost model with cross-validation.
    
    Args:
        train_X: Training features
        train_y: Training targets
        
    Returns:
        Tuple of (trained model, cross-validation scores)
    """
    # Calculate sample weights to emphasize extreme values
    # Formula: log10(|error| + OFFSET) * SCALE - SHIFT
    # This gives more weight to predictions that are further from the mean
    sample_weights = (
        (np.log10((train_y - train_y.mean()).abs() + SAMPLE_WEIGHT_OFFSET) * SAMPLE_WEIGHT_SCALE) 
        - SAMPLE_WEIGHT_SHIFT
    ).round(0)
    
    # Initialize XGBoost model
    xg_model = xg.XGBRegressor(
        objective="reg:squarederror",
        booster="dart",
        gamma=0.2,
        subsample=1.0,
        n_estimators=200,
        max_depth=10,
        colsample_bytree=1,
    )
    
    # Cross-validation
    cv_folds = min(5, len(train_X))
    scores = cross_val_score(
        xg_model,
        train_X,
        train_y,
        cv=cv_folds,
        scoring="neg_root_mean_squared_error"
    )
    logger.info(f"Cross-validation RMSE: {-scores.mean():.2f} ± {scores.std():.2f}")
    
    # Train final model
    xg_model.fit(train_X, train_y, sample_weight=sample_weights, verbose=False)
    
    return xg_model, scores


def generate_forecast_predictions(
    xg_model: xg.XGBRegressor,
    fc: pd.DataFrame,
    prices: pd.DataFrame,
    test_X: pd.DataFrame,
    test_y: pd.Series,
    no_ranges: bool = False
) -> pd.DataFrame:
    """Generate forecast predictions with confidence intervals.
    
    Args:
        xg_model: Trained XGBoost model
        fc: Forecast data to predict on
        prices: Historical prices
        test_X: Test features for KDE fitting
        test_y: Test targets for KDE fitting
        no_ranges: If True, skip KDE-based confidence intervals
        
    Returns:
        DataFrame with predictions and confidence intervals
    """
    # Add time-based features to forecast
    fc["weekend"] = (fc.index.day_of_week >= 5).astype(int)
    fc["days_ago"] = 0
    fc["time"] = fc.index.tz_convert("GB").hour + fc.index.minute / 60
    fc["dt"] = (fc.index - pd.Timestamp.now(tz="UTC")).total_seconds() / 86400
    fc["peak"] = ((fc["time"] >= 16) & (fc["time"] < 19)).astype(float)
    
    # Select features and predict
    fc_features = fc[MODEL_FEATURES]
    fc["day_ahead"] = xg_model.predict(fc_features)
    
    # Calculate confidence intervals using KDE
    if len(test_X) > 10 and not no_ranges:
        try:
            # Prepare data for KDE
            results = test_X[["dt", "day_ahead"]].copy()
            results["pred"] = xg_model.predict(test_X[MODEL_FEATURES])
            
            kde = KernelDensity()
            kde.fit(results[["dt", "pred", "day_ahead"]].to_numpy())
            
            # Calculate price range limits for KDE
            # Using factors of 11 and 9 to provide reasonable price boundaries
            xlim = (
                np.floor(results[["pred", "day_ahead"]].min(axis=1).min() / 11) * 10,
                np.ceil(results[["pred", "day_ahead"]].max(axis=1).max() / 9) * 10,
            )
            
            quantiles = kde_quantiles(
                kde,
                fc["dt"].to_list(),
                fc["day_ahead"].to_list(),
                lim=xlim,
                quantiles={"day_ahead_low": 0.1, "day_ahead_high": 0.9},
            )
            
            fc_quantiles = pd.DataFrame(index=fc.index, data=quantiles)
            fc = pd.concat([fc, fc_quantiles], axis=1)
            
            # Smooth the confidence intervals
            for case in ["low", "high"]:
                fc[f"day_ahead_{case}"] = (
                    fc[f"day_ahead_{case}"].rolling(3, center=True).mean().bfill().ffill()
                )
            
            fc["day_ahead_low"] = fc[["day_ahead", "day_ahead_low"]].min(axis=1)
            fc["day_ahead_high"] = fc[["day_ahead", "day_ahead_high"]].max(axis=1)
        except Exception as e:
            logger.error(f"Error calculating confidence intervals with KDE: {e}")
            fc["day_ahead_low"] = fc["day_ahead"] * 0.9
            fc["day_ahead_high"] = fc["day_ahead"] * 1.1
    else:
        # Simple confidence intervals
        fc["day_ahead_low"] = fc["day_ahead"] * 0.9
        fc["day_ahead_high"] = fc["day_ahead"] * 1.1
    
    # Blend with actual prices where available
    agile_end = prices.index[-1]
    
    # Create scale factors for blending
    sfs = [
        pd.DataFrame(
            index=pd.date_range(fc.index[0], agile_end, freq="30min"),
            data={"mult": 0, "shift": 1}
        )
    ]
    
    # Add forecast-only periods
    sfs.append(
        pd.DataFrame(
            index=fc.index.difference(sfs[0].index),
            data={"mult": 1, "shift": 0}
        )
    )
    
    scale_factors = pd.concat(sfs)
    scale_factors = pd.concat([scale_factors, prices.reindex(scale_factors.index).fillna(0)], axis=1)
    
    # Apply blending
    fc["day_ahead"] = (
        fc["day_ahead"] * scale_factors["mult"] +
        scale_factors["day_ahead"] * (1 - scale_factors["mult"])
    )
    fc["day_ahead_low"] = (
        fc["day_ahead_low"] * scale_factors["mult"] +
        scale_factors["day_ahead"] * (1 - scale_factors["mult"]) -
        scale_factors["shift"]
    )
    fc["day_ahead_high"] = (
        fc["day_ahead_high"] * scale_factors["mult"] +
        scale_factors["day_ahead"] * (1 - scale_factors["mult"]) +
        scale_factors["shift"]
    )
    
    return fc


def create_agile_predictions(fc: pd.DataFrame) -> pd.DataFrame:
    """Create Agile price predictions for all regions.
    
    Args:
        fc: Forecast DataFrame with day-ahead predictions
        
    Returns:
        DataFrame with Agile predictions for all regions
    """
    ag_data = []
    
    for region in REGIONS.keys():
        ag = pd.DataFrame(
            index=fc.index,
            data={
                "region": region,
                "agile_pred": day_ahead_to_agile(fc["day_ahead"], region=region)
                    .astype(float)
                    .round(2),
                "agile_low": day_ahead_to_agile(fc["day_ahead_low"], region=region)
                    .astype(float)
                    .round(2),
                "agile_high": day_ahead_to_agile(fc["day_ahead_high"], region=region)
                    .astype(float)
                    .round(2),
            },
        )
        ag_data.append(ag)
    
    return pd.concat(ag_data)


def save_forecast_to_db(
    db: Session,
    forecast_name: str,
    fc: pd.DataFrame,
    ag: pd.DataFrame,
    mean_score: float,
    stdev_score: float
) -> Forecast:
    """Save forecast and predictions to database.
    
    Args:
        db: Database session
        forecast_name: Name for the forecast
        fc: Forecast DataFrame with predictions
        ag: Agile predictions DataFrame
        mean_score: Mean cross-validation score
        stdev_score: Standard deviation of cross-validation scores
        
    Returns:
        Created Forecast object
    """
    # Create forecast record
    forecast = Forecast(
        name=forecast_name,
        mean=mean_score,
        stdev=stdev_score,
        created_at=pd.Timestamp.now(tz="GB")
    )
    db.add(forecast)
    db.flush()  # Get the ID
    
    # Save forecast data
    fc_cols = ["bm_wind", "solar", "emb_wind", "temp_2m", "wind_10m", "rad", "demand", "day_ahead"]
    for timestamp, row in fc[fc_cols].iterrows():
        forecast_data = ForecastData(
            forecast_id=forecast.id,
            date_time=timestamp,
            day_ahead=row["day_ahead"],
            bm_wind=row["bm_wind"],
            solar=row["solar"],
            emb_wind=row["emb_wind"],
            temp_2m=row["temp_2m"],
            wind_10m=row["wind_10m"],
            rad=row["rad"],
            demand=row["demand"]
        )
        db.add(forecast_data)
    
    # Save agile data
    for timestamp, row in ag.iterrows():
        agile_data = AgileData(
            forecast_id=forecast.id,
            date_time=timestamp,
            region=row["region"],
            agile_pred=row["agile_pred"],
            agile_low=row["agile_low"],
            agile_high=row["agile_high"]
        )
        db.add(agile_data)
    
    db.commit()
    logger.info(f"Saved forecast {forecast.id}: {forecast.name}")
    
    return forecast
