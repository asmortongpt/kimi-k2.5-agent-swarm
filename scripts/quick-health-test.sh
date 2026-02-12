#!/bin/bash
# ============================================================================
# Quick Health Check Test
# Simplified test to verify basic functionality
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Source health check library
source "$SCRIPT_DIR/lib/health-checks.sh"

echo ""
echo -e "${BLUE}Quick Health Check Test${NC}"
echo -e "${BLUE}═══════════════════════${NC}"
echo ""

# Test 1: HTTP endpoint success
echo -e "${YELLOW}Test 1: HTTP endpoint health check${NC}"
python3 -m http.server 9999 > /dev/null 2>&1 &
HTTP_PID=$!
sleep 2

if wait_for_http_endpoint "http://localhost:9999" "test-server" 10 1; then
  echo -e "${GREEN}✅ Test 1 PASSED${NC}"
else
  echo -e "${RED}❌ Test 1 FAILED${NC}"
fi
kill $HTTP_PID 2>/dev/null || true
echo ""

# Test 2: HTTP endpoint failure (should timeout quickly)
echo -e "${YELLOW}Test 2: HTTP endpoint failure detection${NC}"
if wait_for_http_endpoint "http://localhost:19999" "nonexistent" 5 1; then
  echo -e "${RED}❌ Test 2 FAILED (should have failed)${NC}"
else
  echo -e "${GREEN}✅ Test 2 PASSED (correctly detected failure)${NC}"
fi
echo ""

# Test 3: Process health check
echo -e "${YELLOW}Test 3: Process health check${NC}"
sleep 60 &
PROC_PID=$!
sleep 1

if check_process_health $PROC_PID "test-process"; then
  echo -e "${GREEN}✅ Test 3 PASSED${NC}"
else
  echo -e "${RED}❌ Test 3 FAILED${NC}"
fi
kill $PROC_PID 2>/dev/null || true
echo ""

# Test 4: Timeout enforcement
echo -e "${YELLOW}Test 4: Timeout enforcement (5 seconds)${NC}"
START=$(date +%s)
wait_for_http_endpoint "http://localhost:19998" "timeout-test" 5 1 || true
END=$(date +%s)
ELAPSED=$((END - START))

if [ $ELAPSED -ge 4 ] && [ $ELAPSED -le 7 ]; then
  echo -e "${GREEN}✅ Test 4 PASSED (timeout enforced: ${ELAPSED}s)${NC}"
else
  echo -e "${RED}❌ Test 4 FAILED (timeout not enforced: ${ELAPSED}s)${NC}"
fi
echo ""

echo -e "${BLUE}═══════════════════════${NC}"
echo -e "${GREEN}✅ Quick health check tests complete${NC}"
echo ""
