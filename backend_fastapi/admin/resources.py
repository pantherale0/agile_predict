"""Admin resource definitions for model management using starlette-admin."""
from starlette_admin.contrib.sqla import ModelView
from models import Forecast, ForecastData, PriceHistory, AgileData, History


def register_admin_models(admin):
    """Register all models with the admin dashboard.
    
    Args:
        admin: Admin instance from setup_admin()
    """
    admin.add_view(ModelView(model=Forecast, name="Forecast", icon="fa fa-line-chart"))
    admin.add_view(ModelView(model=ForecastData, name="Forecast Data", icon="fa fa-table"))
    admin.add_view(ModelView(model=PriceHistory, name="Price History", icon="fa fa-dollar"))
    admin.add_view(ModelView(model=AgileData, name="Agile Data", icon="fa fa-bolt"))
    admin.add_view(ModelView(model=History, name="History", icon="fa fa-history"))
