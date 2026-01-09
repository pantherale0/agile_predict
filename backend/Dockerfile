# Dockerfile for Agile Predict Backend
# Django + Gunicorn application for Manchester VPS
# Connects to PostgreSQL and Redis via Zerotier

ARG PYTHON_VERSION=3.12-slim

FROM python:${PYTHON_VERSION} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

# Copy and install requirements
COPY requirements/ ./requirements/
RUN pip install --user --no-warn-script-location -r requirements/common.in


# Stage 2: Runtime
FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN addgroup --gid 1000 app && \
    adduser --uid 1000 --gid 1000 --disabled-password --gecos '' app

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder --chown=app:app /root/.local /home/app/.local

# Copy application code
COPY --chown=app:app . .

USER app

ENV PATH=/home/app/.local/bin:$PATH

# Collect static files (requires SECRET_KEY)
RUN python manage.py collectstatic --noinput --clear || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/stats/ || exit 1

EXPOSE 8000

CMD ["gunicorn", \
     "--bind=0.0.0.0:8000", \
     "--workers=4", \
     "--worker-class=sync", \
     "--worker-tmp-dir=/dev/shm", \
     "--max-requests=1000", \
     "--max-requests-jitter=100", \
     "--timeout=60", \
     "--access-logfile=-", \
     "--error-logfile=-", \
     "config.wsgi"]
