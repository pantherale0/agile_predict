"""Admin resource definitions for model management using starlette-admin."""
from starlette_admin.contrib.sqla import ModelView
from models import Forecast, ForecastData, PriceHistory, AgileData, History, TaskLog


class ForecastView(ModelView):
    """Custom view for Forecast model with optimized queries."""
    
    # Disable relationships loading to prevent N+1 queries and hangs
    exclude_columns = ["agile_data", "forecast_data"]
    
    # Limit page size significantly to avoid loading too much data
    page_size = 10
    page_size_options = [10, 25, 50]
    
    # Only show essential columns in list view
    column_list = [Forecast.id, Forecast.name, Forecast.created_at]
    
    # Order by most recent first
    column_default_sort = [(Forecast.created_at, True)]  # True = descending
    
    # Disable the count query which can be slow on large tables
    count = False


class ForecastDataView(ModelView):
    """Custom view for ForecastData model."""
    
    page_size = 50
    page_size_options = [10, 25, 50, 100]
    
    # Exclude relationship to avoid N+1 queries
    exclude_columns = ["forecast"]


class PriceHistoryView(ModelView):
    """Custom view for PriceHistory model."""
    
    page_size = 50
    page_size_options = [10, 25, 50, 100]


class AgileDataView(ModelView):
    """Custom view for AgileData model."""
    
    page_size = 50
    page_size_options = [10, 25, 50, 100]
    
    # Exclude relationship to avoid N+1 queries
    exclude_columns = ["forecast"]


class HistoryView(ModelView):
    """Custom view for History model."""
    
    page_size = 50
    page_size_options = [10, 25, 50, 100]


class TaskLogView(ModelView):
    """Custom view for TaskLog model."""
    
    page_size = 50
    page_size_options = [10, 25, 50, 100]


def register_admin_models(admin):
    """Register all models with the admin dashboard.
    
    Args:
        admin: Admin instance from setup_admin()
    """
    # Temporarily disable Forecast admin due to performance issues
    # admin.add_view(ForecastView(model=Forecast, name="Forecast", icon="fa fa-line-chart"))
    
    admin.add_view(ForecastDataView(model=ForecastData, name="Forecast Data", icon="fa fa-table"))
    admin.add_view(PriceHistoryView(model=PriceHistory, name="Price History", icon="fa fa-dollar"))
    admin.add_view(AgileDataView(model=AgileData, name="Agile Data", icon="fa fa-bolt"))
    admin.add_view(HistoryView(model=History, name="History", icon="fa fa-history"))
    admin.add_view(TaskLogView(model=TaskLog, name="Task Logs", icon="fa fa-tasks"))

