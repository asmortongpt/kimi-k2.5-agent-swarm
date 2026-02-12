#!/bin/bash
# ============================================================================
# Azure Agent Deployment Script with Comprehensive Health Checks
# Production-ready deployment with health verification and cleanup
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="${PROJECT_DIR:-/Users/andrewmorton/Documents/GitHub/kimi}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
API_PORT="${API_PORT:-3001}"
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-60}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-2}"
PID_DIR="/tmp/kimi-pids"
LOG_DIR="/tmp/kimi-logs"

# Ensure directories exist
mkdir -p "$PID_DIR"
mkdir -p "$LOG_DIR"

# ============================================================================
# Cleanup Function
# ============================================================================
cleanup() {
  local exit_code=$?
  echo ""
  echo -e "${YELLOW}[CLEANUP] Stopping background processes...${NC}"

  # Kill processes tracked in PID files
  for pid_file in "$PID_DIR"/*.pid; do
    if [ -f "$pid_file" ]; then
      local pid=$(cat "$pid_file" 2>/dev/null || echo "")
      local service=$(basename "$pid_file" .pid)

      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo -e "${BLUE}  Stopping $service (PID: $pid)...${NC}"
        kill "$pid" 2>/dev/null || true
        sleep 1

        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
          echo -e "${YELLOW}  Force stopping $service...${NC}"
          kill -9 "$pid" 2>/dev/null || true
        fi
      fi

      rm -f "$pid_file"
    fi
  done

  # Cleanup old log files (keep last 10)
  find "$LOG_DIR" -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true

  echo -e "${GREEN}[CLEANUP] Complete${NC}"

  # Exit with original code
  exit $exit_code
}

# Register cleanup on exit, interrupt, and termination
trap cleanup EXIT INT TERM

# ============================================================================
# Logging Functions
# ============================================================================
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Health Check Function
# ============================================================================
wait_for_service() {
  local url="$1"
  local service_name="$2"
  local timeout="${3:-$HEALTH_CHECK_TIMEOUT}"
  local interval="${4:-$HEALTH_CHECK_INTERVAL}"

  local max_attempts=$((timeout / interval))
  local attempt=1

  log_info "Waiting for $service_name to be ready at $url..."
  log_info "Timeout: ${timeout}s, Check interval: ${interval}s"

  while [ $attempt -le $max_attempts ]; do
    # Try to connect with curl, suppress output
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
      log_success "$service_name is ready (attempt $attempt/$max_attempts)"
      return 0
    fi

    # Check if process is still running
    local pid_file="$PID_DIR/${service_name}.pid"
    if [ -f "$pid_file" ]; then
      local pid=$(cat "$pid_file")
      if ! kill -0 "$pid" 2>/dev/null; then
        log_error "$service_name process died (PID: $pid)"
        log_error "Check logs: $LOG_DIR/${service_name}.log"
        return 1
      fi
    fi

    echo -ne "${BLUE}  Attempt $attempt/$max_attempts...${NC}\r"
    sleep "$interval"
    ((attempt++))
  done

  echo "" # New line after progress
  log_error "$service_name failed to start after ${timeout}s"
  log_error "Check logs: $LOG_DIR/${service_name}.log"
  return 1
}

# ============================================================================
# Service Health Check with Retry
# ============================================================================
check_service_health() {
  local url="$1"
  local service_name="$2"

  log_info "Performing health check on $service_name..."

  local response=$(curl -sf --max-time 5 "$url" 2>&1)
  local exit_code=$?

  if [ $exit_code -eq 0 ]; then
    log_success "$service_name health check passed"
    return 0
  else
    log_warning "$service_name health check failed (exit code: $exit_code)"
    return 1
  fi
}

# ============================================================================
# Start Service with PID Tracking
# ============================================================================
start_service() {
  local service_name="$1"
  local command="$2"
  local working_dir="$3"

  log_info "Starting $service_name..."

  local pid_file="$PID_DIR/${service_name}.pid"
  local log_file="$LOG_DIR/${service_name}.log"

  # Check if service is already running
  if [ -f "$pid_file" ]; then
    local old_pid=$(cat "$pid_file")
    if kill -0 "$old_pid" 2>/dev/null; then
      log_warning "$service_name already running (PID: $old_pid)"
      return 0
    else
      rm -f "$pid_file"
    fi
  fi

  # Start service in background
  cd "$working_dir"

  # Create timestamped log
  echo "=== $service_name started at $(date) ===" >> "$log_file"

  # Execute command and capture PID
  eval "$command" >> "$log_file" 2>&1 &
  local pid=$!

  # Save PID
  echo "$pid" > "$pid_file"

  # Verify process started
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    log_success "$service_name started (PID: $pid)"
    log_info "Logs: $log_file"
    return 0
  else
    log_error "$service_name failed to start"
    rm -f "$pid_file"
    return 1
  fi
}

# ============================================================================
# Main Deployment Flow
# ============================================================================

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Azure Agent Deployment - Kimi K2.5 Fleet System          ║${NC}"
echo -e "${BLUE}║  Production-ready with Health Checks & Monitoring         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd "$PROJECT_DIR"

# Step 1: Pre-flight checks
log_info "Step 1/7: Running pre-flight checks..."

if [ ! -f "package.json" ]; then
  log_error "package.json not found in $PROJECT_DIR"
  exit 1
fi

if [ ! -d "node_modules" ]; then
  log_warning "node_modules not found, running npm install..."
  npm install --legacy-peer-deps || {
    log_error "npm install failed"
    exit 1
  }
fi

log_success "Pre-flight checks passed"
echo ""

# Step 2: Check database connectivity
log_info "Step 2/7: Checking database connectivity..."

if command -v docker &> /dev/null; then
  if docker ps | grep -q "fleet-postgres"; then
    log_success "PostgreSQL container is running"
  else
    log_warning "PostgreSQL container not running"
    log_info "Starting PostgreSQL container..."

    docker start fleet-postgres 2>/dev/null || {
      log_info "Creating new PostgreSQL container..."
      docker run -d --name fleet-postgres \
        -e POSTGRES_DB=fleet_db \
        -e POSTGRES_USER=fleet_user \
        -e POSTGRES_PASSWORD=fleet_password \
        -p 5432:5432 \
        postgres:16-alpine || {
        log_error "Failed to start PostgreSQL"
        exit 1
      }
    }

    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    local attempt=1
    while [ $attempt -le 30 ]; do
      if docker exec fleet-postgres pg_isready -U fleet_user &>/dev/null; then
        log_success "PostgreSQL is ready"
        break
      fi
      sleep 1
      ((attempt++))
    done

    if [ $attempt -gt 30 ]; then
      log_error "PostgreSQL failed to start"
      exit 1
    fi
  fi
else
  log_warning "Docker not found, skipping database check"
fi

echo ""

# Step 3: Start API server
log_info "Step 3/7: Starting API server..."

if [ -d "api-standalone" ]; then
  start_service "api" "DB_HOST=localhost npm start" "$PROJECT_DIR/api-standalone" || {
    log_error "Failed to start API server"
    exit 1
  }

  # Wait for API to be ready
  if ! wait_for_service "http://localhost:$API_PORT/api/health" "api" 60 2; then
    log_error "API server health check failed"
    log_info "Showing last 20 lines of API logs:"
    tail -20 "$LOG_DIR/api.log"
    exit 1
  fi
else
  log_warning "api-standalone directory not found, skipping API server"
fi

echo ""

# Step 4: Start frontend development server
log_info "Step 4/7: Starting frontend development server..."

start_service "frontend" "npm run dev" "$PROJECT_DIR" || {
  log_error "Failed to start frontend server"
  exit 1
}

# Wait for frontend to be ready
if ! wait_for_service "http://localhost:$FRONTEND_PORT" "frontend" 60 2; then
  log_error "Frontend server health check failed"
  log_info "Showing last 20 lines of frontend logs:"
  tail -20 "$LOG_DIR/frontend.log"
  exit 1
fi

echo ""

# Step 5: Verify service health
log_info "Step 5/7: Verifying service health..."

# Check API health endpoint
if check_service_health "http://localhost:$API_PORT/api/health" "api"; then
  log_success "API health check passed"
else
  log_warning "API health endpoint not responding, but service is running"
fi

# Check frontend
if check_service_health "http://localhost:$FRONTEND_PORT" "frontend"; then
  log_success "Frontend health check passed"
fi

echo ""

# Step 6: Start optional services (if configured)
log_info "Step 6/7: Starting optional services..."

# Start Ollama if available
if command -v ollama &> /dev/null; then
  if ! pgrep -x "ollama" > /dev/null; then
    log_info "Starting Ollama service..."
    start_service "ollama" "ollama serve" "$PROJECT_DIR" || {
      log_warning "Failed to start Ollama (optional service)"
    }

    # Wait for Ollama
    if wait_for_service "http://localhost:11434/api/tags" "ollama" 30 2; then
      log_success "Ollama is ready"
    else
      log_warning "Ollama health check failed (optional service)"
    fi
  else
    log_success "Ollama already running"
  fi
else
  log_info "Ollama not installed, skipping"
fi

echo ""

# Step 7: Display deployment summary
log_info "Step 7/7: Deployment summary"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅  All Services Deployed Successfully                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🚀 Services Running:${NC}"
echo -e "   • Frontend:      http://localhost:$FRONTEND_PORT"
echo -e "   • API Server:    http://localhost:$API_PORT"
echo -e "   • API Health:    http://localhost:$API_PORT/api/health"
if command -v ollama &> /dev/null && pgrep -x "ollama" > /dev/null; then
  echo -e "   • Ollama:        http://localhost:11434"
fi
echo ""
echo -e "${BLUE}📊 Process Information:${NC}"
for pid_file in "$PID_DIR"/*.pid; do
  if [ -f "$pid_file" ]; then
    local service=$(basename "$pid_file" .pid)
    local pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      echo -e "   • $service: PID $pid"
    fi
  fi
done
echo ""
echo -e "${BLUE}📝 Logs Location:${NC}"
echo -e "   $LOG_DIR/"
echo ""
echo -e "${BLUE}🛠️  Management Commands:${NC}"
echo -e "   • View logs:     tail -f $LOG_DIR/<service>.log"
echo -e "   • Stop all:      kill \$(cat $PID_DIR/*.pid)"
echo -e "   • Restart:       $0"
echo ""
echo -e "${BLUE}🔍 Health Check Commands:${NC}"
echo -e "   • API:           curl http://localhost:$API_PORT/api/health"
echo -e "   • Frontend:      curl http://localhost:$FRONTEND_PORT"
echo ""
echo -e "${GREEN}✅ Deployment complete - Press Ctrl+C to stop all services${NC}"
echo ""

# Keep script running to maintain cleanup trap
# This allows Ctrl+C to trigger cleanup
while true; do
  sleep 60

  # Periodic health checks
  for pid_file in "$PID_DIR"/*.pid; do
    if [ -f "$pid_file" ]; then
      local service=$(basename "$pid_file" .pid)
      local pid=$(cat "$pid_file")

      if ! kill -0 "$pid" 2>/dev/null; then
        log_error "$service died unexpectedly (PID: $pid)"
        log_info "Check logs: $LOG_DIR/${service}.log"
        exit 1
      fi
    fi
  done
done
