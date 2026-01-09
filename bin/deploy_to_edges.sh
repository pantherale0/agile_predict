#!/bin/bash

# Edge Node Deployment Script
# Deploys frontend build to multiple edge nodes
# Usage: ./bin/deploy_to_edges.sh [build_dir]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BUILD_DIR="${1:-$FRONTEND_DIR/build}"

# Edge node configuration
# Format: "hostname:user:deploy_path"
EDGE_NODES=(
  "usa-edge.internal:deploy:/srv/frontend"
  "london-edge.internal:deploy:/srv/frontend"
  "sg-edge.internal:deploy:/srv/frontend"
)

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

# Check if build directory exists
if [ ! -d "$BUILD_DIR" ]; then
  log_error "Build directory not found: $BUILD_DIR"
  log_info "Please run './bin/deploy_frontend.sh' first to build the frontend"
  exit 1
fi

log_info "Starting edge node deployment"
log_info "Source: $BUILD_DIR"
log_info "Build size: $(du -sh "$BUILD_DIR" | cut -f1)"

# Deploy to each edge node
FAILED_NODES=()
SUCCESSFUL_NODES=()

for node_config in "${EDGE_NODES[@]}"; do
  IFS=':' read -r hostname user deploy_path <<< "$node_config"
  
  log_info "Deploying to $hostname..."
  
  # Check SSH connectivity
  if ! ssh-keyscan "$hostname" >/dev/null 2>&1; then
    log_error "Cannot reach $hostname"
    FAILED_NODES+=("$hostname")
    continue
  fi
  
  # Create deploy directory if it doesn't exist
  ssh "$user@$hostname" "mkdir -p '$deploy_path' && echo 'Directory ready'" > /dev/null 2>&1 || {
    log_error "Cannot access/create deploy directory on $hostname"
    FAILED_NODES+=("$hostname")
    continue
  }
  
  # Rsync the build
  if rsync -avz --delete --progress "$BUILD_DIR/" "$user@$hostname:$deploy_path/" > /tmp/rsync_$hostname.log 2>&1; then
    log_success "Deployed to $hostname"
    SUCCESSFUL_NODES+=("$hostname")
    
    # Verify deployment
    if ssh "$user@$hostname" "[ -f '$deploy_path/index.html' ]" > /dev/null 2>&1; then
      log_success "Verified index.html on $hostname"
    else
      log_warn "Could not verify index.html on $hostname"
    fi
    
    # Reload Caddy on edge node
    if ssh "$user@$hostname" "sudo systemctl reload caddy" > /dev/null 2>&1; then
      log_success "Caddy reloaded on $hostname"
    else
      log_warn "Could not reload Caddy on $hostname (may need manual restart)"
    fi
  else
    log_error "Failed to deploy to $hostname"
    log_info "Check /tmp/rsync_$hostname.log for details"
    FAILED_NODES+=("$hostname")
  fi
done

# Summary
echo ""
log_info "Deployment Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ${#SUCCESSFUL_NODES[@]} -gt 0 ]; then
  echo -e "${GREEN}Successful (${#SUCCESSFUL_NODES[@]}):${NC}"
  for node in "${SUCCESSFUL_NODES[@]}"; do
    echo "  ✓ $node"
  done
fi

if [ ${#FAILED_NODES[@]} -gt 0 ]; then
  echo -e "${RED}Failed (${#FAILED_NODES[@]}):${NC}"
  for node in "${FAILED_NODES[@]}"; do
    echo "  ✗ $node"
  done
fi

if [ ${#FAILED_NODES[@]} -eq 0 ]; then
  log_success "All edge nodes deployed successfully"
  exit 0
else
  log_error "Some edge nodes failed to deploy"
  exit 1
fi
