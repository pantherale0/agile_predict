"""
Management command to populate historical forecast data for bootstrapping the ML model.
Creates Forecasts and ForecastData records from existing historical data.
"""
import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone
from forecasting.models import Forecasts, ForecastData, History
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Populate historical forecast data from price history for model training"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days-back",
            type=int,
            default=30,
            help="Number of days back to populate from (default: 30)",
        )
        parser.add_argument(
            "--interval-hours",
            type=int,
            default=24,
            help="Create forecasts at this interval in hours (default: 24 = daily at 14:00)",
        )

    def handle(self, *args, **options):
        days_back = options["days_back"]
        interval_hours = options["interval_hours"]

        # Get historical data
        history = pd.DataFrame(list(History.objects.all().values()))
        if history.empty:
            self.stdout.write(self.style.ERROR("No historical data found"))
            return

        # Convert date_time to datetime if needed
        history["date_time"] = pd.to_datetime(history["date_time"])
        history = history.set_index("date_time").sort_index()

        # Calculate date range
        end_date = history.index.max()
        start_date = end_date - pd.Timedelta(days=days_back)

        self.stdout.write(f"History range: {history.index.min()} to {history.index.max()}")
        self.stdout.write(f"Creating forecasts from {start_date} to {end_date}")

        # Create forecasts at regular intervals - one per day at midnight UTC for simplicity
        forecast_times = pd.date_range(start=start_date, end=end_date, freq="D", tz="UTC")
        # Round to nearest existing data point
        forecast_times = [pd.Timestamp(t.date(), tz="UTC") + pd.Timedelta(hours=14) for t in forecast_times]

        created_count = 0
        forecast_data_count = 0
        skipped_count = 0

        for forecast_time in forecast_times:
            # Skip if forecast already exists
            forecast_name = forecast_time.strftime("%Y-%m-%d %H:%M")
            if Forecasts.objects.filter(name=forecast_name).exists():
                skipped_count += 1
                continue

            # Create Forecast record
            forecast = Forecasts.objects.create(
                name=forecast_name,
                mean=0.5,  # Placeholder - will be updated when model trains
                stdev=0.1,
            )
            created_count += 1
            self.stdout.write(f"Created forecast: {forecast_name}")

            # Create ForecastData records for future time periods
            # Use data from the forecast time onwards for the next 14 days
            future_start = forecast_time
            future_end = forecast_time + pd.Timedelta(days=14)

            try:
                future_history = history.loc[future_start:future_end]
            except KeyError:
                future_history = history[(history.index >= future_start) & (history.index <= future_end)]

            if future_history.empty:
                self.stdout.write(self.style.WARNING(f"No data found for forecast {forecast_name}"))
                continue

            for idx, row in future_history.iterrows():
                try:
                    ForecastData.objects.create(
                        forecast=forecast,
                        date_time=idx,
                        day_ahead=None,  # Will be filled by model
                        bm_wind=float(row.get("bm_wind", 0)),
                        solar=float(row.get("solar", 0)),
                        emb_wind=float(row.get("total_wind", 0)),  # Use total_wind as emb_wind placeholder
                        temp_2m=float(row.get("temp_2m", 0)),
                        wind_10m=float(row.get("wind_10m", 0)),
                        rad=float(row.get("rad", 0)),
                        demand=float(row.get("demand", 0)),
                    )
                    forecast_data_count += 1
                except Exception as e:
                    logger.error(f"Error creating ForecastData for {idx}: {e}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {created_count} forecasts (skipped {skipped_count}), "
                f"{forecast_data_count} forecast data records"
            )
        )
