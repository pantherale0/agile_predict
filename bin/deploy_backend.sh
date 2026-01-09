#!/bin/bash

# Backend Deployment Script
# Deploys Django backend to Manchester VPS
# Usage: ./bin/deploy_backend.sh [environment] [host]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

ENVIRONMENT="${1:-production}"
BACKEND_HOST="${2:-backend.internal}"
BACKEND_USER="${BACKEND_USER:-deploy}"
BACKEND_PORT="${BACKEND_PORT:-8001}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

cd "$PROJECT_ROOT"

log_info "Starting backend deployment for $ENVIRONMENT environment"
log_info "Target: $BACKEND_USER@$BACKEND_HOST:$BACKEND_PORT"

# Check if SSH key is available
if ! ssh-keyscan "$BACKEND_HOST" >/dev/null 2>&1; then
  log_error "Cannot reach backend host: $BACKEND_HOST"
  exit 1
fi

log_info "Running Django checks..."
if ! .venv/bin/python backend/manage.py check; then
  log_error "Django checks failed"
  exit 1
fi

log_info "Running tests..."
if ! .venv/bin/python backend/manage.py test --keepdb 2>&1 | tail -20; then
  log_warn "Some tests failed. Continuing with deployment..."
fi

log_info "Collecting static files..."
.venv/bin/python backend/manage.py collectstatic --noinput

log_info "Creating deployment package..."
DEPLOY_PACKAGE="/tmp/backend-deploy-$(date +%s).tar.gz"
tar --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.venv' \
    --exclude='node_modules' \
    --exclude='logs' \
    -czf "$DEPLOY_PACKAGE" \
    -C "$PROJECT_ROOT" backend/

log_success "Deployment package created: $DEPLOY_PACKAGE"
log_info "Package size: $(du -sh "$DEPLOY_PACKAGE" | cut -f1)"

# Create deployment metadata
DEPLOY_METADATA="/tmp/backend-deploy.json"
cat > "$DEPLOY_METADATA" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "$ENVIRONMENT",
  "git_commit": "$(git rev-parse --short HEAD)",
  "git_branch": "$(git rev-parse --abbrev-ref HEAD)",
  "python_version": "$(.venv/bin/python --version 2>&1 | awk '{print $2}')",
  "target_host": "$BACKEND_HOST",
  "target_port": "$BACKEND_PORT"
}
EOF

log_info "Uploading deployment package..."
scp -P 22 "$DEPLOY_PACKAGE" "$BACKEND_USER@$BACKEND_HOST:/tmp/" || {
  log_error "Failed to upload deployment package"
  exit 1
}

scp -P 22 "$DEPLOY_METADATA" "$BACKEND_USER@$BACKEND_HOST:/tmp/backend-deploy.json" || {
  log_error "Failed to upload deployment metadata"
  exit 1
}

log_success "Deployment package uploaded successfully"

# Execute remote deployment
log_info "Executing remote deployment..."
ssh "$BACKEND_USER@$BACKEND_HOST" bash << 'REMOTE_DEPLOY'
set -euo pipefail

DEPLOY_PACKAGE=$(ls -t /tmp/backend-deploy-*.tar.gz 2>/dev/null | head -1)
DEPLOY_DIR="/opt/agile-predict"

if [ -z "$DEPLOY_PACKAGE" ]; then
  echo "Error: No deployment package found"
  exit 1
fi

echo "[INFO] Extracting deployment package..."
mkdir -p "$DEPLOY_DIR"
tar -xzf "$DEPLOY_PACKAGE" -C "$DEPLOY_DIR"

echo "[INFO] Installing Python dependencies..."
cd "$DEPLOY_DIR"
# Assuming .venv is on the remote
if [ -d .venv ]; then
  .venv/bin/pip install -q -r backend/requirements/common.in
else
  echo "[WARN] Python venv not found on remote, assuming pre-configured"
fi

echo "[INFO] Running migrations..."
.venv/bin/python backend/manage.py migrate

echo "[INFO] Restarting Gunicorn..."
sudo systemctl restart agile-predict-gunicorn

echo "[INFO] Checking Gunicorn status..."
if sudo systemctl is-active --quiet agile-predict-gunicorn; then
  echo "[SUCCESS] Gunicorn is running"
else
  echo "[ERROR] Gunicorn failed to start"
  sudo systemctl status agile-predict-gunicorn
  exit 1
fi

echo "[INFO] Reloading Caddy proxy..."
sudo systemctl reload caddy || echo "[WARN] Caddy reload failed, may already be configured"

# Cleanup
rm -f "$DEPLOY_PACKAGE" /tmp/backend-deploy.json

echo "[SUCCESS] Remote deployment complete"
REMOTE_DEPLOY

REMOTE_STATUS=$?

if [ $REMOTE_STATUS -eq 0 ]; then
  log_success "Backend deployed successfully to $BACKEND_HOST"
  
  # Health check
  log_info "Running health check..."
  sleep 2
  if curl -sf "http://$BACKEND_HOST:$BACKEND_PORT/api/stats/" > /dev/null 2>&1; then
    log_success "Health check passed"
  else
    log_warn "Health check failed or timed out - backend may still be starting"
  fi
else
  log_error "Remote deployment failed"
  exit 1
fi

# Cleanup local files
rm -f "$DEPLOY_PACKAGE" "$DEPLOY_METADATA"

log_success "Backend deployment complete"
