#!/bin/bash
# ============================================================================
# Health Check Test Script
# Tests health check functionality with intentional failures
# ============================================================================

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Source health check library
if [ -f "$SCRIPT_DIR/lib/health-checks.sh" ]; then
  source "$SCRIPT_DIR/lib/health-checks.sh"
else
  echo -e "${RED}Error: Health check library not found${NC}"
  exit 1
fi

# Test results tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================================
# Test Helper Functions
# ============================================================================

start_test() {
  local test_name="$1"
  echo ""
  echo -e "${BLUE}════════════════════════════════════════${NC}"
  echo -e "${BLUE}TEST: $test_name${NC}"
  echo -e "${BLUE}════════════════════════════════════════${NC}"
  ((TESTS_RUN++))
}

pass_test() {
  local test_name="$1"
  echo -e "${GREEN}✅ PASS: $test_name${NC}"
  ((TESTS_PASSED++))
}

fail_test() {
  local test_name="$1"
  local reason="${2:-Unknown reason}"
  echo -e "${RED}❌ FAIL: $test_name${NC}"
  echo -e "${RED}   Reason: $reason${NC}"
  ((TESTS_FAILED++))
}

# ============================================================================
# Test 1: HTTP Endpoint - Success Case
# ============================================================================
test_http_success() {
  start_test "HTTP health check - success case"

  # Start a simple HTTP server in background
  python3 -m http.server 9999 > /dev/null 2>&1 &
  local server_pid=$!
  sleep 2

  # Test health check
  if wait_for_http_endpoint "http://localhost:9999" "test-http-server" 10 1; then
    pass_test "HTTP health check detected running server"
  else
    fail_test "HTTP health check failed to detect running server"
  fi

  # Cleanup
  kill $server_pid 2>/dev/null || true
}

# ============================================================================
# Test 2: HTTP Endpoint - Failure Case
# ============================================================================
test_http_failure() {
  start_test "HTTP health check - failure case (should timeout)"

  # Test with non-existent endpoint (short timeout)
  if wait_for_http_endpoint "http://localhost:19999" "test-nonexistent" 5 1; then
    fail_test "HTTP health check should have failed for non-existent service"
  else
    pass_test "HTTP health check correctly failed for non-existent service"
  fi
}

# ============================================================================
# Test 3: TCP Port - Success Case
# ============================================================================
test_tcp_success() {
  start_test "TCP port check - success case"

  # Start a simple server
  nc -l 8888 > /dev/null 2>&1 &
  local server_pid=$!
  sleep 1

  # Test TCP check
  if wait_for_tcp_port "localhost" 8888 "test-tcp-server" 10 1; then
    pass_test "TCP check detected listening port"
  else
    fail_test "TCP check failed to detect listening port"
  fi

  # Cleanup
  kill $server_pid 2>/dev/null || true
}

# ============================================================================
# Test 4: TCP Port - Failure Case
# ============================================================================
test_tcp_failure() {
  start_test "TCP port check - failure case (should timeout)"

  # Test with closed port (short timeout)
  if wait_for_tcp_port "localhost" 18888 "test-closed-port" 5 1; then
    fail_test "TCP check should have failed for closed port"
  else
    pass_test "TCP check correctly failed for closed port"
  fi
}

# ============================================================================
# Test 5: Process Health Check - Success
# ============================================================================
test_process_health_success() {
  start_test "Process health check - success case"

  # Start a dummy process
  sleep 300 &
  local process_pid=$!
  sleep 1

  # Test process check
  if check_process_health $process_pid "test-process"; then
    pass_test "Process health check detected running process"
  else
    fail_test "Process health check failed to detect running process"
  fi

  # Cleanup
  kill $process_pid 2>/dev/null || true
}

# ============================================================================
# Test 6: Process Health Check - Failure
# ============================================================================
test_process_health_failure() {
  start_test "Process health check - failure case"

  # Use a PID that doesn't exist
  local fake_pid=999999

  # Test process check
  if check_process_health $fake_pid "test-dead-process"; then
    fail_test "Process health check should have failed for non-existent PID"
  else
    pass_test "Process health check correctly failed for non-existent PID"
  fi
}

# ============================================================================
# Test 7: Comprehensive Health Checks
# ============================================================================
test_comprehensive_checks() {
  start_test "Comprehensive health checks"

  # Start test services
  python3 -m http.server 9998 > /dev/null 2>&1 &
  local http_pid=$!
  sleep 2

  # Run multiple checks
  if run_health_checks \
    "wait_for_http_endpoint http://localhost:9998 test-http 10 1" \
    "check_process_health $http_pid test-http-process"; then
    pass_test "Comprehensive health checks passed"
  else
    fail_test "Comprehensive health checks failed"
  fi

  # Cleanup
  kill $http_pid 2>/dev/null || true
}

# ============================================================================
# Test 8: Health Check Retry
# ============================================================================
test_retry_mechanism() {
  start_test "Health check retry mechanism"

  # Start server with delay
  (sleep 3 && python3 -m http.server 9997 > /dev/null 2>&1) &
  local delayed_pid=$!

  # Test retry (should succeed after delay)
  if retry_health_check wait_for_http_endpoint 3 2 "http://localhost:9997" "delayed-server" 5 1; then
    pass_test "Retry mechanism successfully waited for delayed service"
  else
    fail_test "Retry mechanism failed"
  fi

  # Cleanup
  pkill -P $delayed_pid 2>/dev/null || true
  kill $delayed_pid 2>/dev/null || true
}

# ============================================================================
# Test 9: Docker Container Check (if Docker available)
# ============================================================================
test_docker_health() {
  start_test "Docker container health check"

  if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  SKIP: Docker not available${NC}"
    return
  fi

  # Start a simple container
  docker run -d --name test-health-container --rm alpine sleep 30 > /dev/null 2>&1 || {
    echo -e "${YELLOW}⚠️  SKIP: Could not start test container${NC}"
    return
  }

  sleep 2

  # Test container check
  if wait_for_docker_container "test-health-container" \
    "docker exec test-health-container true" \
    "test-container" 10 1; then
    pass_test "Docker container health check succeeded"
  else
    fail_test "Docker container health check failed"
  fi

  # Cleanup
  docker stop test-health-container > /dev/null 2>&1 || true
}

# ============================================================================
# Test 10: Timeout Verification
# ============================================================================
test_timeout_enforcement() {
  start_test "Health check timeout enforcement"

  local start_time=$(date +%s)

  # Test with guaranteed failure and 5-second timeout
  wait_for_http_endpoint "http://localhost:19997" "timeout-test" 5 1 || true

  local end_time=$(date +%s)
  local elapsed=$((end_time - start_time))

  # Should timeout around 5 seconds (allow 1s margin)
  if [ $elapsed -ge 4 ] && [ $elapsed -le 7 ]; then
    pass_test "Timeout correctly enforced (${elapsed}s elapsed)"
  else
    fail_test "Timeout not properly enforced (${elapsed}s elapsed, expected ~5s)"
  fi
}

# ============================================================================
# Main Test Execution
# ============================================================================

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Health Check Test Suite                                  ║${NC}"
echo -e "${BLUE}║  Testing health check functionality with failures         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Run all tests
test_http_success
test_http_failure
test_tcp_success
test_tcp_failure
test_process_health_success
test_process_health_failure
test_comprehensive_checks
test_retry_mechanism
test_docker_health
test_timeout_enforcement

# Print summary
echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}TEST SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "Total tests run:    $TESTS_RUN"
echo -e "${GREEN}Tests passed:       $TESTS_PASSED${NC}"
echo -e "${RED}Tests failed:       $TESTS_FAILED${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

# Exit with appropriate code
if [ $TESTS_FAILED -eq 0 ]; then
  echo -e "${GREEN}✅ All tests passed!${NC}"
  exit 0
else
  echo -e "${RED}❌ Some tests failed${NC}"
  exit 1
fi
