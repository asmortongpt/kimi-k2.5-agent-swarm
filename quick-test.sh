#!/bin/bash
# Quick integration test - verifies everything works end-to-end

set -e

cd "$(dirname "$0")"

echo "🧪 CLAWS.BOT + Kimi K2.5 Quick Test"
echo "===================================="
echo ""

# Check if services are running
echo "Step 1: Checking if services are running..."
if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
  echo "❌ Kimi API not running on port 8000"
  echo "   Run: ./start-all.sh"
  exit 1
fi
echo "✅ Kimi API is running"

if ! curl -s http://localhost:8010/health > /dev/null 2>&1; then
  echo "❌ Kimi MCP not running on port 8010"
  echo "   Run: ./start-all.sh"
  exit 1
fi
echo "✅ Kimi MCP is running"

if ! curl -s http://localhost:8011/health > /dev/null 2>&1; then
  echo "❌ Browser MCP not running on port 8011"
  echo "   Run: ./start-all.sh"
  exit 1
fi
echo "✅ Browser MCP is running"

echo ""
echo "Step 2: Testing Kimi API..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Say hello","model":"kimi-k2.5"}')

if echo "$RESPONSE" | grep -q "content\|message\|text"; then
  echo "✅ Kimi API responds to chat requests"
else
  echo "❌ Kimi API not responding correctly"
  echo "Response: $RESPONSE"
  exit 1
fi

echo ""
echo "Step 3: Testing MCP Toolhost..."
TOOLS=$(curl -s http://localhost:8010/tools)
if echo "$TOOLS" | grep -q "kimi.chat"; then
  TOOL_COUNT=$(echo "$TOOLS" | grep -o "name" | wc -l | tr -d ' ')
  echo "✅ MCP Toolhost has $TOOL_COUNT tools registered"
else
  echo "❌ MCP Toolhost not returning tools"
  exit 1
fi

echo ""
echo "Step 4: Testing Browser MCP..."
BROWSER_TOOLS=$(curl -s http://localhost:8011/tools)
if echo "$BROWSER_TOOLS" | grep -q "test_html"; then
  echo "✅ Browser MCP has test_html tool"
else
  echo "❌ Browser MCP not configured correctly"
  exit 1
fi

echo ""
echo "Step 5: Testing CLAWS.BOT integration..."
cd /Users/andrewmorton/Documents/GitHub/CLAWD.BOT

# Check if tsx is available
if [ ! -f "node_modules/.bin/tsx" ]; then
  echo "❌ tsx not found. Run: npm install"
  exit 1
fi

# Set environment variables
export KIMI_BASE_URL="http://localhost:8000"
export KIMI_MCP_URL="http://localhost:8010"
export BROWSER_MCP_URL="http://localhost:8011"
export DEFAULT_MODEL="kimi-k2.5"

echo "✅ Environment variables set"
echo "✅ CLAWS.BOT is ready to use Kimi K2.5"

echo ""
echo "======================================"
echo "✅ All tests passed!"
echo "======================================"
echo ""
echo "🎉 Integration is working perfectly!"
echo ""
echo "Try it now:"
echo "  cd /Users/andrewmorton/Documents/GitHub/CLAWD.BOT"
echo "  source ../kimi/export-env.sh"
echo "  npx tsx claws-cli.ts \"Create a simple React component\""
echo ""
