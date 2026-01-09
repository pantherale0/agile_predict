from django.urls import path
from .views import PriceForecastAPIView, PriceForecastRegionAPIView, GenerationDemandAPIView, PriceHistoryAPIView, StatsAPIView, PriceHeatmapAPIView, PriceDailyBreakdownAPIView

urlpatterns = [
    path("", PriceForecastAPIView.as_view()),
    # Exact paths must come before parameterized paths
    path("history/actual/", PriceHistoryAPIView.as_view()),
    path("history/heatmap/", PriceHeatmapAPIView.as_view()),
    path("history/daily/<str:date_str>/", PriceDailyBreakdownAPIView.as_view()),
    path("stats/", StatsAPIView.as_view()),
    # Parameterized paths must come last
    path("<str:region>/generation/", GenerationDemandAPIView.as_view()),
    path("<str:region>/", PriceForecastRegionAPIView.as_view()),
]
