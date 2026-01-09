#!/bin/bash

# Frontend Deployment Script
# Builds React app for edge node deployment
# Usage: ./bin/deploy_frontend.sh [environment]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BUILD_DIR="$FRONTEND_DIR/build"

ENVIRONMENT="${1:-production}"
EDGE_NODES=${EDGE_NODES:-"usa-edge london-edge sg-edge"}

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
  log_error "Node.js is not installed"
  exit 1
fi

log_info "Starting frontend deployment for $ENVIRONMENT environment"

# Navigate to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  log_info "Installing dependencies..."
  npm install
fi

# Run tests
log_info "Running tests..."
if ! npm test -- --coverage --watchAll=false 2>&1 | head -20; then
  log_error "Tests failed. Continuing with build anyway..."
fi

# Build the React app
log_info "Building React app for $ENVIRONMENT..."
REACT_APP_ENV=$ENVIRONMENT npm run build

if [ ! -d "$BUILD_DIR" ]; then
  log_error "Build directory not created. Build may have failed."
  exit 1
fi

log_success "React app built successfully"
log_info "Build output: $BUILD_DIR"
log_info "Build size: $(du -sh "$BUILD_DIR" | cut -f1)"

# Create deployment metadata
DEPLOY_METADATA="$BUILD_DIR/.deploy.json"
cat > "$DEPLOY_METADATA" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "$ENVIRONMENT",
  "git_commit": "$(cd "$PROJECT_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo 'unknown')",
  "git_branch": "$(cd "$PROJECT_ROOT" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')",
  "node_version": "$(node --version)",
  "npm_version": "$(npm --version)"
}
EOF

log_success "Deployment metadata created: $DEPLOY_METADATA"

# Instructions for deployment to edge nodes
echo ""
log_info "Next steps to deploy to edge nodes:"
echo "  1. Review the build in: $BUILD_DIR"
echo "  2. For each edge node, run:"
echo "     rsync -avz --delete $BUILD_DIR/ user@edge-node:/srv/frontend/"
echo ""
echo "  Or use the edge deployment script:"
echo "     ./bin/deploy_to_edges.sh"
echo ""

log_success "Frontend build complete and ready for edge deployment"
