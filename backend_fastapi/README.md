# FastAPI Backend for AgilePredictAPI

Modern, high-performance REST API backend built with FastAPI, SQLAlchemy, and scheduled background tasks.

## Features

- **FastAPI**: Modern async web framework with automatic OpenAPI documentation
- **SQLAlchemy ORM**: Type-safe database operations with support for SQLite and PostgreSQL
- **fastapi-amis-admin**: Professional admin dashboard for data management
- **fastapi-scheduler**: Background task scheduling with APScheduler
- **Pydantic**: Data validation and serialization
- **CORS & Security**: Configurable cross-origin requests and trusted hosts

## Project Structure

```
backend_fastapi/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment configuration template
├── core/
│   ├── config.py          # Settings management
│   ├── database.py        # SQLAlchemy setup and session management
│   └── security.py        # CORS and security middleware
├── models/
│   └── __init__.py        # SQLAlchemy ORM models
├── schemas/
│   ├── __init__.py        # Pydantic schemas (forecast)
│   └── price.py           # Pydantic schemas (price data)
├── api/
│   ├── deps.py            # Shared dependencies
│   └── endpoints/
│       ├── forecasts.py   # Forecast endpoints
│       └── price_history.py # Price history and stats endpoints
├── services/
│   ├── forecast_service.py # Forecast business logic
│   └── price_service.py    # Price business logic
├── tasks/
│   ├── scheduler.py       # APScheduler configuration
│   └── __init__.py
└── migrations/
    └── __init__.py        # Alembic migrations (future)
```

## Installation

### 1. Create Virtual Environment

```bash
cd /home/jordanh/Documents/agile_predict
python -m venv .venv_fastapi
source .venv_fastapi/bin/activate
```

### 2. Install Dependencies

```bash
cd backend_fastapi
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

## Running the Application

### Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### With Docker

```bash
docker build -t agile-predict-fastapi .
docker run -p 8000:8000 agile-predict-fastapi
```

## API Documentation

Once the server is running, access:
- **Interactive API docs (Swagger)**: http://localhost:8000/docs
- **Alternative API docs (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## API Endpoints

### Forecasts
- `GET /api/forecasts/latest` - Get latest forecast
- `GET /api/forecasts/{region}` - Get forecast by region with query parameters:
  - `days` (default: 14) - Number of days to forecast
  - `forecast_count` (default: 1) - Number of forecasts to retrieve

### Price History
- `GET /api/price-history` - Get historical prices
  - `days` (default: 14) - Days of history to retrieve
- `GET /api/history/actual/` - Get actual historical prices
- `GET /api/history/heatmap/` - Get heatmap visualization
- `GET /api/history/daily/{date}` - Get daily breakdown for a specific date
- `GET /api/{region}/generation` - Get generation data by region

### Statistics
- `GET /api/stats/` - Get comprehensive statistics and diagnostics

### Health
- `GET /health` - Health check endpoint
- `GET /` - Root information endpoint

## Database Models

### Forecast
- Stores forecast metadata and statistics
- Related to AgileData and ForecastData

### ForecastData
- Detailed forecast predictions with generation and weather data
- References Forecast

### PriceHistory
- Actual historical price data
- Day-ahead and Agile prices

### AgileData
- Agile price predictions by region
- References Forecast

### History
- Historical weather and demand data
- Used for analysis and model training

## Configuration

All settings are managed in `core/config.py` and loaded from environment variables:

- `DEBUG` - Enable debug mode (default: False)
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - Application secret key
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `CORS_ORIGINS` - Comma-separated list of CORS origins
- `LOG_LEVEL` - Logging level (default: INFO)

## Database Migration (Future)

Alembic migrations will be set up for schema management:

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Background Tasks

The scheduler runs background tasks like:
- Periodic data updates (placeholder)
- Scheduled forecasting (placeholder)

Configure in `tasks/scheduler.py`.

## Development Workflow

1. **Create virtual environment** (one-time)
2. **Install dependencies** (one-time or when updated)
3. **Configure `.env`** with your database and settings
4. **Run the server** in development mode with `--reload`
5. **Make changes** - the server auto-reloads
6. **Test endpoints** via Swagger docs at http://localhost:8000/docs

## Performance Considerations

- **Async endpoints**: FastAPI uses async/await for non-blocking I/O
- **Connection pooling**: SQLAlchemy manages database connections efficiently
- **Lazy loading**: Relationships are lazy-loaded by default
- **Pagination**: Large result sets should be paginated

## Deployment

For production deployment:
1. Set `DEBUG=False`
2. Update `SECRET_KEY` to a secure random value
3. Configure PostgreSQL instead of SQLite
4. Use `gunicorn` or similar ASGI server
5. Set up proper logging and monitoring
6. Configure `ALLOWED_HOSTS` for your domain

## Common Issues

### ImportError: No module named 'main'
- Ensure you're in the `backend_fastapi` directory
- Virtual environment must be activated

### Database connection error
- Check `DATABASE_URL` in `.env`
- Ensure database server is running
- Verify credentials

### CORS errors
- Update `CORS_ORIGINS` in `.env` to include your frontend URL

## Next Steps

1. ✅ Project structure created
2. ⬜ Set up database migration system (Alembic)
3. ⬜ Implement admin panel (fastapi-amis-admin)
4. ⬜ Migrate scheduled tasks from Django management commands
5. ⬜ Complete stats and visualization endpoints
6. ⬜ Add authentication if needed
7. ⬜ Set up comprehensive logging and monitoring

## License

Same as parent project
