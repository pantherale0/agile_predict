#!/bin/bash

# Docker build and push script
# Builds and pushes Docker images to registry
# Usage: ./bin/docker_build.sh [registry] [tag]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REGISTRY="${1:-docker.io}"
TAG="${2:-latest}"
GIT_COMMIT=$(cd "$PROJECT_ROOT" && git rev-parse --short HEAD)
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
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

cd "$PROJECT_ROOT"

log_info "Building Docker images"
log_info "Registry: $REGISTRY"
log_info "Tag: $TAG"
log_info "Git Commit: $GIT_COMMIT"

# Build frontend image
log_info "Building frontend image..."
docker build \
  -f frontend/Dockerfile \
  -t "$REGISTRY/agile-predict-frontend:$TAG" \
  -t "$REGISTRY/agile-predict-frontend:latest" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg GIT_COMMIT="$GIT_COMMIT" \
  --label "org.opencontainers.image.created=$BUILD_DATE" \
  --label "org.opencontainers.image.revision=$GIT_COMMIT" \
  frontend/

if [ $? -ne 0 ]; then
  log_error "Frontend image build failed"
  exit 1
fi
log_success "Frontend image built"

# Build backend image
log_info "Building backend image..."
docker build \
  -f backend/Dockerfile \
  -t "$REGISTRY/agile-predict-backend:$TAG" \
  -t "$REGISTRY/agile-predict-backend:latest" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg GIT_COMMIT="$GIT_COMMIT" \
  --label "org.opencontainers.image.created=$BUILD_DATE" \
  --label "org.opencontainers.image.revision=$GIT_COMMIT" \
  backend/

if [ $? -ne 0 ]; then
  log_error "Backend image build failed"
  exit 1
fi
log_success "Backend image built"

# List built images
log_info "Built images:"
docker images | grep agile-predict

log_success "All images built successfully"
echo ""
echo "To push images to registry, run:"
echo "  docker push $REGISTRY/agile-predict-frontend:$TAG"
echo "  docker push $REGISTRY/agile-predict-backend:$TAG"
