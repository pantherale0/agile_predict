#!/bin/bash

# Health Check Script
# Verifies deployment status of frontend and backend
# Usage: ./bin/health_check.sh

set -euo pipefail

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

# Configuration
BACKEND_HOST="${BACKEND_HOST:-backend.internal}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
EDGE_NODES=(
  "usa-edge.internal"
  "london-edge.internal"
  "sg-edge.internal"
)

TIMEOUT=5

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              Agile Predict Health Check                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Backend health check
log_info "Checking backend at $BACKEND_HOST:$BACKEND_PORT"
if timeout $TIMEOUT curl -sf "http://$BACKEND_HOST:$BACKEND_PORT/api/stats/" > /dev/null 2>&1; then
  log_success "Backend API responding"
  
  # Get some stats
  if STATS=$(timeout $TIMEOUT curl -s "http://$BACKEND_HOST:$BACKEND_PORT/api/stats/" 2>/dev/null); then
    FORECAST_COUNT=$(echo "$STATS" | jq -r '.forecast_count // "unknown"' 2>/dev/null || echo "unknown")
    log_info "Active forecasts: $FORECAST_COUNT"
  fi
else
  log_error "Backend API not responding"
fi

echo ""

# Edge node health checks
log_info "Checking edge nodes (frontend)"
echo ""

HEALTHY_EDGES=0
UNHEALTHY_EDGES=0

for node in "${EDGE_NODES[@]}"; do
  if timeout $TIMEOUT ssh -o ConnectTimeout=3 "deploy@$node" "curl -sf http://localhost:3000 > /dev/null 2>&1" > /dev/null 2>&1; then
    log_success "$node is healthy"
    HEALTHY_EDGES=$((HEALTHY_EDGES + 1))
  else
    log_warn "$node is unreachable or unhealthy"
    UNHEALTHY_EDGES=$((UNHEALTHY_EDGES + 1))
  fi
done

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                      Summary                                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

if timeout $TIMEOUT curl -sf "http://$BACKEND_HOST:$BACKEND_PORT/api/stats/" > /dev/null 2>&1; then
  echo -e "${GREEN}Backend: HEALTHY${NC}"
else
  echo -e "${RED}Backend: UNHEALTHY${NC}"
fi

echo "Edge Nodes: $HEALTHY_EDGES/$((HEALTHY_EDGES + UNHEALTHY_EDGES)) healthy"

if [ $UNHEALTHY_EDGES -eq 0 ] && timeout $TIMEOUT curl -sf "http://$BACKEND_HOST:$BACKEND_PORT/api/stats/" > /dev/null 2>&1; then
  echo ""
  echo -e "${GREEN}✓ All systems operational${NC}"
  exit 0
else
  echo ""
  echo -e "${YELLOW}⚠ Some systems may need attention${NC}"
  exit 1
fi
