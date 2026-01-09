from django.shortcuts import render
import pandas as pd
import json
from pathlib import Path
import plotly.graph_objects as go

# Create your views here.
from rest_framework import generics
from rest_framework.response import Response
from forecasting.models import Forecasts, ForecastData, PriceHistory, AgileData
from .serializers import PriceForecastSerializer, PriceForecastRegionSerializer, GenerationDataSerializer, PriceHistorySerializer


# class PriceForecastAPIView(generics.ListAPIView):
#     ids = [f.id for f in Forecasts.objects.all().order_by("-created_at")[:1]]


#     queryset = Forecasts.objects.filter(id__in=ids)
#     # queryset = Forecasts.objects.all()
#     serializer_class = PriceForecastSerializer
class PriceForecastAPIView(generics.ListAPIView):
    serializer_class = PriceForecastSerializer

    def get_queryset(self):
        latest = Forecasts.objects.order_by("-created_at")[:1]
        return latest


class PriceForecastRegionAPIView(generics.ListAPIView):
    serializer_class = PriceForecastRegionSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        context.update({"region": self.kwargs["region"].upper()})
        context.update({"days": int(self.request.query_params.get("days", 14))})
        context.update({"high_low": self.request.query_params.get("high_low", "true").lower() in ["true", "1"]})
        return context

    def get_queryset(self):
        forecast_count = int(self.request.query_params.get("forecast_count", 1))
        print(f"forecast_count: {forecast_count}")
        ids = [f.id for f in Forecasts.objects.all().order_by("-created_at")[:forecast_count]]
        queryset = Forecasts.objects.filter(id__in=ids).order_by("-created_at")
        return queryset


class GenerationDemandAPIView(generics.ListAPIView):
    serializer_class = GenerationDataSerializer
    pagination_class = None  # Disable pagination for this endpoint

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        context.update({"days": int(self.request.query_params.get("days", 14))})
        return context

    def get_queryset(self):
        forecast_count = int(self.request.query_params.get("forecast_count", 1))
        days = int(self.request.query_params.get("days", 14))
        
        ids = [f.id for f in Forecasts.objects.all().order_by("-created_at")[:forecast_count]]
        queryset = ForecastData.objects.filter(forecast_id__in=ids).order_by("date_time")
        
        # Filter by date range if we have data
        dates = list(queryset.values_list('date_time', flat=True).distinct())
        if dates:
            max_date = min(dates) + pd.Timedelta(days=days)
            queryset = queryset.filter(date_time__lte=max_date)
        
        return queryset

class PriceHistoryAPIView(generics.ListAPIView):
    serializer_class = PriceHistorySerializer
    pagination_class = None  # Disable pagination

    def get_queryset(self):
        days = int(self.request.query_params.get("days", 14))
        
        # Get all price history
        queryset = PriceHistory.objects.all().order_by("date_time")
        
        # Filter to last N days
        if queryset.exists():
            latest_date = queryset.order_by("-date_time").first().date_time
            start_date = latest_date - pd.Timedelta(days=days)
            queryset = queryset.filter(date_time__gte=start_date)
        
        return queryset


class StatsAPIView(generics.GenericAPIView):
    """API endpoint that returns stats data including charts and diagnostic images"""
    pagination_class = None  # Disable pagination
    
    def get(self, request, *args, **kwargs):
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        from django.conf import settings
        PRIOR_DAYS = 2
        BASE_DIR = settings.BASE_DIR
        
        # Get actual prices for the last 7+ days
        price_history = PriceHistory.objects.all().order_by("-date_time").first()
        if not price_history:
            # Return empty response with message instead of 404
            return Response({
                "stats_chart": None,
                "trend_image": None,
                "diagnostic_plots": [],
                "message": "No price history data available yet. Please run data import commands to populate the database."
            })
        
        agile_actuals_end = pd.Timestamp(price_history.date_time)
        agile_actuals_start = agile_actuals_end - pd.Timedelta("7D")

        agile_actuals_objects = PriceHistory.objects.filter(date_time__gt=agile_actuals_start).order_by("date_time")
        df = pd.DataFrame(
            index=[obj.date_time for obj in agile_actuals_objects],
            data={"actuals": [obj.agile for obj in agile_actuals_objects]},
        )

        agile_forecast_data = AgileData.objects.filter(
            date_time__gt=agile_actuals_start, date_time__lte=agile_actuals_end
        )
        
        # Create the stats figure
        figure = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=("Agile Price", "Error HeatMap"),
            shared_xaxes=True,
            vertical_spacing=0.05,
        )

        for forecast in agile_forecast_data.values_list("forecast").distinct():
            forecast_created_at = pd.Timestamp(Forecasts.objects.filter(id=forecast[0])[0].created_at).tz_convert("GB")
            forecast_after = (
                pd.Timestamp.combine(forecast_created_at.date(), pd.Timestamp("22:00").time())
                .tz_localize("UTC")
                .tz_convert("GB")
            )

            if forecast_created_at.hour >= 16:
                forecast_after += pd.Timedelta("24h")

            agile_pred_objects = agile_forecast_data.filter(forecast=forecast[0])
            index = [
                obj.date_time
                for obj in agile_pred_objects
                if forecast_after < obj.date_time < forecast_after + pd.Timedelta("7D")
            ]
            data = [
                obj.agile_pred
                for obj in agile_pred_objects
                if forecast_after < obj.date_time < forecast_after + pd.Timedelta("7D")
            ]
            if len(data) > 0:
                df.loc[index, forecast_created_at] = data
                figure.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df[forecast_created_at],
                        line={"color": "grey", "width": 0.5},
                        showlegend=False,
                        mode="lines",
                    ),
                )

        figure.add_trace(
            go.Scatter(
                x=df.index,
                y=df["actuals"],
                line={"color": "yellow", "width": 3},
                showlegend=False,
            ),
        )

        # Calculate price range for locking axes
        price_min = df["actuals"].min()
        price_max = df["actuals"].max()
        price_padding = (price_max - price_min) * 0.05

        layout = dict(
            yaxis={"title": "Agile Price [p/kWh]", "fixedrange": False},
            xaxis={"fixedrange": False},
            dragmode="pan",
            margin={"r": 5, "t": 50},
            height=800,
            template="plotly_dark",
            plot_bgcolor="#212529",
            paper_bgcolor="#343a40",
            font={"color": "#ccc"}
        )

        figure.update_layout(**layout)

        for x in df.columns[1:]:
            df[x] = abs(df[x] - df["actuals"])
        df_to_plot = df.drop(["actuals"], axis=1).sort_index(axis=1).T
        df_to_plot = df_to_plot.loc[df_to_plot.index > agile_actuals_start - pd.Timedelta("3D")]
        x = df_to_plot.columns
        y = df_to_plot.index
        z = df_to_plot.to_numpy()

        figure.add_heatmap(x=x, y=y, z=z, row=2, col=1, colorbar={"title": "Error\n[p/kWh]"})
        figure.update_yaxes(row=2, col=1, title_text="Forecast Age")

        # Convert figure to JSON
        import json
        figure_json = json.loads(figure.to_json())

        # Get diagnostic plot files
        plot_dir = BASE_DIR / "plots" / "stats_plots"
        descriptions = {
            "1_actual_vs_predicted_over_time.png": (
                "This plot shows the full training dataset used for the last forecast. Actual data are plotted as the black line. "
                "The fitted data from the trained model are plotted in red and should generally overlay the black. Forecasts generated "
                "from the model using prior data are plotted as the points with the colour indicating the lead time from forecast to actual pricing. "
                "All of the plots below other than the XGBoost Feature Importance show the same data in different ways.",
                "Actual vs Predicted Over Time",
            ),
            "2_scatters.png": (
                "Scatter plot of predicted vs actual prices. Color shows forecast lead time (in days).",
                "Prediction vs Actual Scatter",
            ),
            "3_residuals.png": (
                "Histogram of prediction errors (residuals) to visualize model bias and spread.",
                "Residuals Distribution",
            ),
            "4_kde_error_by_horizon.png": (
                "KDE heatmap showing how forecast error varies by lead time. Initially the data are biased towards shorter lead times but as the database "
                "grows this bias should reduce. The distribution is, however, always expected to be tighter over short lead times.",
                "Forecast Error by Horizon (KDE)",
            ),
            "5_feature_importance.png": (
                "This plot is slightly different to the others in that it shows the relative importance of the various inputs in building the regression model. Details of each feature can be found on the About page.",
                "XGBoost Feature Importance",
            ),
        }

        plot_files = [
            {
                "filename": f"stats_plots/{f.name}",
                "description": descriptions.get(f.name, ("", ""))[0],
                "title": descriptions.get(f.name, ("", ""))[1] or f.name.replace("_", " ").title().replace(".Png", ""),
            }
            for f in plot_dir.glob("*.png")
            if f.is_file()
        ]
        # Build full URLs for static files
        request_host = request.build_absolute_uri('/').rstrip('/')
        trend_image_url = f"{request_host}/static/trends/trend.png"
        
        return Response({
            "stats_chart": figure_json,
            "trend_image": trend_image_url,
            "diagnostic_plots": plot_files
        })


class PriceHeatmapAPIView(generics.GenericAPIView):
    """API endpoint that returns 365-day price heatmap data"""
    pagination_class = None  # Disable pagination
    
    def get(self, request, *args, **kwargs):
        import plotly.graph_objects as go
        
        # Get price history for last 365 days
        end_date = pd.Timestamp(PriceHistory.objects.all().order_by("-date_time")[0].date_time)
        start_date = end_date - pd.Timedelta("365D")
        
        price_history = PriceHistory.objects.filter(
            date_time__gte=start_date,
            date_time__lte=end_date
        ).order_by("date_time")
        
        # Create dataframe with date and price
        df = pd.DataFrame(
            list(price_history.values('date_time', 'agile'))
        )
        
        if df.empty:
            return Response({"error": "No price history available"}, status=400)
        
        # Calculate daily average prices
        df['date'] = pd.to_datetime(df['date_time']).dt.date
        daily_avg = df.groupby('date')['agile'].mean().reset_index()
        daily_avg['date'] = pd.to_datetime(daily_avg['date'])
        
        # Create week and day of week for calendar heatmap
        daily_avg['year'] = daily_avg['date'].dt.isocalendar().year
        daily_avg['week'] = daily_avg['date'].dt.isocalendar().week
        daily_avg['day_of_week'] = daily_avg['date'].dt.day_name()
        daily_avg['day_num'] = daily_avg['date'].dt.dayofweek  # 0=Mon, 6=Sun
        
        # Create pivot table for heatmap (weeks x day_of_week)
        pivot = daily_avg.pivot_table(
            index='day_num',
            columns='week',
            values='agile',
            aggfunc='mean'
        )
        
        # Create heatmap
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Create a date mapping for clicking - map (week, day_num) to actual dates
        date_mapping = {}
        for _, row in daily_avg.iterrows():
            week = row['week']
            day_num = row['day_num']
            date_str = row['date'].strftime('%Y-%m-%d')
            date_mapping[f"{week}_{day_num}"] = date_str
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=[days[i] for i in pivot.index],
            customdata=[[date_mapping.get(f"{int(pivot.columns[col_idx])}_{int(pivot.index[row_idx])}", "") 
                         for col_idx in range(len(pivot.columns))] 
                        for row_idx in range(len(pivot.index))],
            colorscale='RdYlGn_r',  # Red (high prices) to Green (low prices)
            colorbar=dict(title="Price (p/kWh)"),
            hovertemplate="Week %{x}<br>%{y}<br>Date: %{customdata}<br>Avg Price: £%{z:.2f}/MWh<extra></extra>"
        ))
        
        fig.update_layout(
            title="Daily Average Agile Price - Last 365 Days",
            xaxis_title="Week of Year",
            yaxis_title="Day of Week",
            template="plotly_dark",
            plot_bgcolor="#212529",
            paper_bgcolor="#343a40",
            font={"color": "#ccc"},
            height=400,
            hovermode='closest'
        )
        
        # Convert to JSON
        heatmap_json = json.loads(fig.to_json())
        
        # Also return raw data for statistics
        stats = {
            "min_price": float(daily_avg['agile'].min()),
            "max_price": float(daily_avg['agile'].max()),
            "avg_price": float(daily_avg['agile'].mean()),
            "median_price": float(daily_avg['agile'].median()),
            "std_dev": float(daily_avg['agile'].std()),
            "days_with_data": len(daily_avg)
        }
        
        return Response({
            "heatmap": heatmap_json,
            "stats": stats,
            "date_mapping": date_mapping
        })


class PriceDailyBreakdownAPIView(generics.GenericAPIView):
    """API endpoint that returns hourly price breakdown for a specific date"""
    pagination_class = None
    
    def get(self, request, date_str, *args, **kwargs):
        """Get hourly prices for a specific date (format: YYYY-MM-DD)"""
        try:
            target_date = pd.to_datetime(date_str).date()
        except:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
        
        # Get all prices for the target date
        prices = PriceHistory.objects.filter(
            date_time__date=target_date
        ).order_by('date_time')
        
        if not prices.exists():
            return Response({"error": f"No price data available for {date_str}"}, status=404)
        
        # Create DataFrame
        df = pd.DataFrame(list(prices.values('date_time', 'agile')))
        df['hour'] = pd.to_datetime(df['date_time']).dt.strftime('%H:%M')
        df['time'] = pd.to_datetime(df['date_time'])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['hour'],
            y=df['agile'],
            mode='lines+markers',
            name='Price',
            line=dict(color='#ff7f0e', width=3),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(255, 127, 14, 0.2)',
            hovertemplate='<b>%{x}</b><br>Price: £%{y:.2f}/MWh<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"Hourly Agile Prices - {target_date.strftime('%A, %B %d, %Y')}",
            xaxis_title="Time of Day",
            yaxis_title="Price (p/kWh)",
            template="plotly_dark",
            plot_bgcolor="#212529",
            paper_bgcolor="#343a40",
            font={"color": "#ccc"},
            height=400,
            hovermode='x unified',
            xaxis_tickangle=-45
        )
        
        chart_json = json.loads(fig.to_json())
        
        # Calculate statistics
        stats = {
            "date": str(target_date),
            "min_price": float(df['agile'].min()),
            "max_price": float(df['agile'].max()),
            "avg_price": float(df['agile'].mean()),
            "median_price": float(df['agile'].median()),
            "data_points": len(df)
        }
        
        return Response({
            "chart": chart_json,
            "stats": stats,
            "hourly_data": [
                {"time": row['hour'], "price": row['agile']}
                for _, row in df.iterrows()
            ]
        })