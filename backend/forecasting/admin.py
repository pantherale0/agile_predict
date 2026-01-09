from django.contrib import admin
from .models import Forecasts, PriceHistory, AgileData, History, ForecastData


@admin.register(Forecasts)
class ForecastsAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "mean", "stdev")
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("date_time", "day_ahead", "agile")
    search_fields = ("date_time",)
    ordering = ("-date_time",)


@admin.register(AgileData)
class AgileDataAdmin(admin.ModelAdmin):
    list_display = ("forecast", "region", "date_time", "agile_pred")
    search_fields = ("forecast__name", "region")
    ordering = ("-date_time",)


@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ("date_time", "total_wind", "solar", "demand")
    search_fields = ("date_time",)
    ordering = ("-date_time",)


@admin.register(ForecastData)
class ForecastDataAdmin(admin.ModelAdmin):
    list_display = ("forecast", "date_time", "day_ahead")
    search_fields = ("forecast__name", "date_time")
    ordering = ("-date_time",)
