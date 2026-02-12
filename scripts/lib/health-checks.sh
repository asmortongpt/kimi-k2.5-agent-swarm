#!/bin/bash
# ============================================================================
# Health Check Utility Library
# Reusable health check functions for deployment scripts
# ============================================================================

# Colors for output (can be overridden)
RED="${RED:-\033[0;31m}"
GREEN="${GREEN:-\033[0;32m}"
YELLOW="${YELLOW:-\033[1;33m}"
BLUE="${BLUE:-\033[0;34m}"
NC="${NC:-\033[0m}" # No Color

# Default timeouts (can be overridden)
DEFAULT_HTTP_TIMEOUT="${DEFAULT_HTTP_TIMEOUT:-60}"
DEFAULT_CHECK_INTERVAL="${DEFAULT_CHECK_INTERVAL:-2}"

# ============================================================================
# HTTP Health Check
# ============================================================================
# Checks if an HTTP endpoint is responding
# Usage: wait_for_http_endpoint URL SERVICE_NAME [TIMEOUT] [INTERVAL]
# Returns: 0 on success, 1 on failure
wait_for_http_endpoint() {
  local url="$1"
  local service_name="$2"
  local timeout="${3:-$DEFAULT_HTTP_TIMEOUT}"
  local interval="${4:-$DEFAULT_CHECK_INTERVAL}"

  local max_attempts=$((timeout / interval))
  local attempt=1

  echo -e "${BLUE}[HEALTH] Checking $service_name at $url${NC}"
  echo -e "${BLUE}[HEALTH] Timeout: ${timeout}s, Interval: ${interval}s${NC}"

  while [ $attempt -le $max_attempts ]; do
    # Try HTTP request with curl
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
      echo -e "${GREEN}[HEALTH] ✅ $service_name is healthy (${attempt}s elapsed)${NC}"
      return 0
    fi

    # Show progress every 5 attempts
    if [ $((attempt % 5)) -eq 0 ]; then
      echo -e "${BLUE}[HEALTH] ⏳ Still waiting for $service_name... (${attempt}s/${timeout}s)${NC}"
    fi

    sleep "$interval"
    ((attempt++))
  done

  echo -e "${RED}[HEALTH] ❌ $service_name failed health check after ${timeout}s${NC}"
  return 1
}

# ============================================================================
# Docker Container Health Check
# ============================================================================
# Checks if a Docker container is healthy using a custom command
# Usage: wait_for_docker_container CONTAINER_NAME CHECK_COMMAND SERVICE_NAME [TIMEOUT] [INTERVAL]
# Returns: 0 on success, 1 on failure
wait_for_docker_container() {
  local container_name="$1"
  local check_command="$2"
  local service_name="$3"
  local timeout="${4:-60}"
  local interval="${5:-2}"

  local max_attempts=$((timeout / interval))
  local attempt=1

  echo -e "${BLUE}[HEALTH] Checking Docker container $service_name ($container_name)${NC}"

  # First check if container exists and is running
  if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
    echo -e "${RED}[HEALTH] ❌ Container $container_name is not running${NC}"
    return 1
  fi

  while [ $attempt -le $max_attempts ]; do
    # Execute health check command in container
    if eval "$check_command" &>/dev/null; then
      echo -e "${GREEN}[HEALTH] ✅ $service_name is healthy (${attempt}s elapsed)${NC}"
      return 0
    fi

    # Show progress
    if [ $((attempt % 10)) -eq 0 ]; then
      echo -e "${BLUE}[HEALTH] ⏳ Still waiting for $service_name... (${attempt}s/${timeout}s)${NC}"
    fi

    sleep "$interval"
    ((attempt++))
  done

  echo -e "${RED}[HEALTH] ❌ $service_name failed health check after ${timeout}s${NC}"
  echo -e "${YELLOW}[HEALTH] Check logs: docker logs $container_name${NC}"
  return 1
}

# ============================================================================
# Docker Compose Service Health Check
# ============================================================================
# Waits for a docker-compose service to be healthy
# Usage: wait_for_compose_service SERVICE_NAME [TIMEOUT] [INTERVAL]
# Returns: 0 on success, 1 on failure
wait_for_compose_service() {
  local service_name="$1"
  local timeout="${2:-60}"
  local interval="${3:-2}"

  local max_attempts=$((timeout / interval))
  local attempt=1

  echo -e "${BLUE}[HEALTH] Checking docker-compose service $service_name${NC}"

  while [ $attempt -le $max_attempts ]; do
    # Check service health status
    local health_status=$(docker-compose ps --format json "$service_name" 2>/dev/null | \
      grep -o '"Health":"[^"]*"' | cut -d'"' -f4)

    if [ "$health_status" = "healthy" ]; then
      echo -e "${GREEN}[HEALTH] ✅ $service_name is healthy${NC}"
      return 0
    fi

    # Also accept "running" for services without healthchecks
    local state=$(docker-compose ps --format json "$service_name" 2>/dev/null | \
      grep -o '"State":"[^"]*"' | cut -d'"' -f4)

    if [ "$state" = "running" ] && [ -z "$health_status" ]; then
      echo -e "${GREEN}[HEALTH] ✅ $service_name is running${NC}"
      return 0
    fi

    if [ $((attempt % 10)) -eq 0 ]; then
      echo -e "${BLUE}[HEALTH] ⏳ Service status: $state, Health: ${health_status:-none} (${attempt}s/${timeout}s)${NC}"
    fi

    sleep "$interval"
    ((attempt++))
  done

  echo -e "${RED}[HEALTH] ❌ $service_name failed to become healthy after ${timeout}s${NC}"
  return 1
}

# ============================================================================
# TCP Port Health Check
# ============================================================================
# Checks if a TCP port is accepting connections
# Usage: wait_for_tcp_port HOST PORT SERVICE_NAME [TIMEOUT] [INTERVAL]
# Returns: 0 on success, 1 on failure
wait_for_tcp_port() {
  local host="$1"
  local port="$2"
  local service_name="$3"
  local timeout="${4:-60}"
  local interval="${5:-2}"

  local max_attempts=$((timeout / interval))
  local attempt=1

  echo -e "${BLUE}[HEALTH] Checking TCP connection to $service_name ($host:$port)${NC}"

  while [ $attempt -le $max_attempts ]; do
    # Try to connect to port using timeout command
    if timeout 1 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null; then
      echo -e "${GREEN}[HEALTH] ✅ $service_name port is open${NC}"
      return 0
    fi

    if [ $((attempt % 10)) -eq 0 ]; then
      echo -e "${BLUE}[HEALTH] ⏳ Still waiting for port $port... (${attempt}s/${timeout}s)${NC}"
    fi

    sleep "$interval"
    ((attempt++))
  done

  echo -e "${RED}[HEALTH] ❌ Port $port not accessible after ${timeout}s${NC}"
  return 1
}

# ============================================================================
# Process Health Check
# ============================================================================
# Checks if a process is running by PID
# Usage: check_process_health PID SERVICE_NAME
# Returns: 0 if running, 1 if not
check_process_health() {
  local pid="$1"
  local service_name="$2"

  if kill -0 "$pid" 2>/dev/null; then
    echo -e "${GREEN}[HEALTH] ✅ $service_name is running (PID: $pid)${NC}"
    return 0
  else
    echo -e "${RED}[HEALTH] ❌ $service_name is not running (PID: $pid)${NC}"
    return 1
  fi
}

# ============================================================================
# PostgreSQL Health Check
# ============================================================================
# Checks if PostgreSQL is ready to accept connections
# Usage: wait_for_postgres CONTAINER_NAME [USERNAME] [TIMEOUT] [INTERVAL]
# Returns: 0 on success, 1 on failure
wait_for_postgres() {
  local container_name="$1"
  local username="${2:-postgres}"
  local timeout="${3:-60}"
  local interval="${4:-2}"

  local check_cmd="docker exec $container_name pg_isready -U $username"
  wait_for_docker_container "$container_name" "$check_cmd" "PostgreSQL" "$timeout" "$interval"
}

# ============================================================================
# Redis Health Check
# ============================================================================
# Checks if Redis is ready to accept connections
# Usage: wait_for_redis CONTAINER_NAME [TIMEOUT] [INTERVAL]
# Returns: 0 on success, 1 on failure
wait_for_redis() {
  local container_name="$1"
  local timeout="${2:-60}"
  local interval="${3:-2}"

  local check_cmd="docker exec $container_name redis-cli ping"
  wait_for_docker_container "$container_name" "$check_cmd" "Redis" "$timeout" "$interval"
}

# ============================================================================
# Comprehensive Health Check
# ============================================================================
# Runs multiple health checks and reports overall status
# Usage: run_health_checks "check1_function arg1 arg2" "check2_function arg1" ...
# Returns: 0 if all pass, 1 if any fail
run_health_checks() {
  local checks=("$@")
  local failed=0
  local passed=0

  echo -e "${BLUE}[HEALTH] Running ${#checks[@]} health checks...${NC}"
  echo ""

  for check in "${checks[@]}"; do
    if eval "$check"; then
      ((passed++))
    else
      ((failed++))
    fi
    echo ""
  done

  echo -e "${BLUE}════════════════════════════════════════${NC}"
  echo -e "${BLUE}[HEALTH] Summary: $passed passed, $failed failed${NC}"
  echo -e "${BLUE}════════════════════════════════════════${NC}"

  if [ $failed -gt 0 ]; then
    echo -e "${RED}[HEALTH] ❌ Some health checks failed${NC}"
    return 1
  else
    echo -e "${GREEN}[HEALTH] ✅ All health checks passed${NC}"
    return 0
  fi
}

# ============================================================================
# Health Check with Retry
# ============================================================================
# Retries a health check function multiple times
# Usage: retry_health_check FUNCTION_NAME MAX_RETRIES [RETRY_DELAY] [ARGS...]
# Returns: 0 on success, 1 on failure
retry_health_check() {
  local function_name="$1"
  local max_retries="$2"
  local retry_delay="${3:-5}"
  shift 3
  local args=("$@")

  local retry=1

  echo -e "${BLUE}[HEALTH] Attempting health check with up to $max_retries retries${NC}"

  while [ $retry -le $max_retries ]; do
    echo -e "${BLUE}[HEALTH] Attempt $retry/$max_retries${NC}"

    if "$function_name" "${args[@]}"; then
      return 0
    fi

    if [ $retry -lt $max_retries ]; then
      echo -e "${YELLOW}[HEALTH] Retrying in ${retry_delay}s...${NC}"
      sleep "$retry_delay"
    fi

    ((retry++))
  done

  echo -e "${RED}[HEALTH] ❌ All retry attempts failed${NC}"
  return 1
}

# ============================================================================
# Export Functions
# ============================================================================
# Make all functions available to sourcing scripts
export -f wait_for_http_endpoint
export -f wait_for_docker_container
export -f wait_for_compose_service
export -f wait_for_tcp_port
export -f check_process_health
export -f wait_for_postgres
export -f wait_for_redis
export -f run_health_checks
export -f retry_health_check

# Indicate library is loaded
echo -e "${GREEN}[HEALTH] Health check library loaded${NC}"
