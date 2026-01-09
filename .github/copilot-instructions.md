# Copilot Instructions for Agile Predict

## Project Overview

Agile Predict is a Django-based web application that forecasts Octopus Agile electricity prices up to 14 days in advance using Machine Learning models. The project uses XGBoost trained on data from the Balancing Mechanism Reporting System (BMRS), National Grid Electricity Supply Operator (NG ESO), and weather data from open-meteo.com.

## Technology Stack

- **Framework**: Django 4.2.11
- **Language**: Python 3.12
- **Database**: PostgreSQL (configured via DATABASE_URL environment variable)
- **Machine Learning**: XGBoost, scikit-learn, pandas, numpy
- **API**: Django REST Framework
- **Frontend**: Django templates with Bootstrap (crispy-bootstrap5)
- **Deployment**: Docker, Gunicorn, Fly.io

## Project Structure

- `api/` - REST API views and serializers
- `prices/` - Main Django app containing models, views, and management commands
- `prices/management/commands/` - Custom Django management commands for data processing and ML model training
- `config/` - Django project settings and configuration
- `templates/` - HTML templates
- `home_assistant/` - Home Assistant integration
- `requirements.txt` - Python dependencies
- `manage.py` - Django management script

## Development Setup

### Environment Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```

2. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate` (or `.venv\Scripts\activate.bat`)
   - Unix/macOS: `source .venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables in `.env` file:
   - `SECRET_KEY` - Django secret key
   - `DEBUG` - Set to True for development
   - `DATABASE_URL` - PostgreSQL connection string
   - `ALLOWED_HOSTS` - Comma-separated list of allowed hosts

### Running the Application

```bash
python manage.py runserver
```

### Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Custom Management Commands

The project includes several custom management commands in `prices/management/commands/`:
- `update.py` - Updates ML model and generates forecasts
- `latest_agile.py` - Fetches latest Agile prices
- `full_hist.py` - Populates historical data
- `clean_forecasts.py` - Cleans old forecast data
- `national_agile.py` - Processes national Agile data

Run commands with:
```bash
python manage.py <command_name>
```

## Coding Conventions

### General Python Style

- Follow PEP 8 conventions
- Use meaningful variable names
- Add docstrings to functions and classes where functionality is not obvious

### Django Specifics

- Use Django's ORM for database operations
- Define models in `models.py` with proper field types and relationships
- Use Django's URL routing system in `urls.py`
- Leverage Django's built-in authentication and admin features
- Use environment variables for configuration (via `environs` package)

### API Development

- Use Django REST Framework's generic views (e.g., `ListAPIView`)
- Define serializers in `serializers.py`
- Return appropriate HTTP status codes
- Use query parameters for filtering and pagination

### Machine Learning Code

- Store ML models in the database or cache
- Use logging for ML training progress and metrics
- Handle missing data appropriately
- Use vectorized operations with numpy/pandas for efficiency
- Configure matplotlib to use 'Agg' backend for non-interactive plotting

### Database Models

- Use appropriate field types (CharField, FloatField, DateTimeField, etc.)
- Define relationships using ForeignKey with proper `on_delete` behavior
- Use `related_name` for reverse relationships
- Add `__str__` methods to models for better admin interface

### Logging

- Use Python's `logging` module
- Configure file handlers to write to `logs/` directory
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Log important events, errors, and ML training metrics

### Error Handling

- Use try-except blocks for operations that may fail
- Provide meaningful error messages
- Log exceptions with full tracebacks

## Testing

- Test files are located alongside their respective apps (e.g., `api/tests.py`, `prices/tests.py`)
- Use Django's TestCase for writing tests
- Run tests with: `python manage.py test`

## Docker Deployment

- The project uses a multi-stage Dockerfile
- Base image: Python 3.12-slim
- Exposed port: 8000
- Production server: Gunicorn with 2 workers
- Static files are collected during build

Build and run:
```bash
docker build -t agile_predict .
docker run -p 8000:8000 agile_predict
```

## Security Considerations

- Never commit secrets or API keys to version control
- Use environment variables for sensitive configuration
- Keep dependencies up to date
- Use Django's CSRF protection
- Validate and sanitize user inputs
- Use parameterized queries (Django ORM handles this)

## Dependencies Management

- All Python dependencies are listed in `requirements.txt`
- Update dependencies carefully, ensuring compatibility
- Test after updating dependencies
- Consider using `pip freeze` to lock versions

## Files to Ignore

The following should not be committed (already in `.gitignore`):
- `__pycache__/`
- `.venv/`
- `.local/`
- `*.sqlite3`
- `.env`
- `logs/`
- `static/` (generated by collectstatic)
- `plots/` (generated plots)

## Additional Notes

- The project uses `environs` for environment variable management
- Static files are served using WhiteNoise in production
- PostgreSQL is used via `psycopg2-binary`
- The application forecasts electricity prices for multiple regions (identified by region codes)
- Price predictions include mean, low, and high estimates
