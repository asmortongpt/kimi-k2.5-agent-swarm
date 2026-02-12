#!/bin/bash
# Start all Kimi + CLAWS.BOT services

cd "$(dirname "$0")"
source .venv/bin/activate

echo "Starting Kimi + CLAWS.BOT Integration..."
echo ""

# Kill any existing processes on these ports
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8010 | xargs kill -9 2>/dev/null || true
lsof -ti:8011 | xargs kill -9 2>/dev/null || true

# Start Kimi API (port 8000)
echo "Starting Kimi API (port 8000)..."
python server/api/main.py > logs/kimi-api.log 2>&1 &
KIMI_API_PID=$!
echo $KIMI_API_PID > .pids/kimi-api.pid

sleep 2

# Start Kimi MCP Toolhost (port 8010)
echo "Starting Kimi MCP Toolhost (port 8010)..."
python -m uvicorn server.mcp_toolhost:app --port 8010 > logs/kimi-mcp.log 2>&1 &
KIMI_MCP_PID=$!
echo $KIMI_MCP_PID > .pids/kimi-mcp.pid

# Start Browser MCP (port 8011)
echo "Starting Browser MCP (port 8011)..."
python -m uvicorn server.browser_mcp:app --port 8011 > logs/browser-mcp.log 2>&1 &
BROWSER_MCP_PID=$!
echo $BROWSER_MCP_PID > .pids/browser-mcp.pid

sleep 3

# Check health
echo ""
echo "Checking services..."
curl -s http://localhost:8000/api/health > /dev/null && echo "OK: Kimi API is running" || echo "FAIL: Kimi API failed"
curl -s http://localhost:8010/health > /dev/null && echo "OK: Kimi MCP is running" || echo "FAIL: Kimi MCP failed"
curl -s http://localhost:8011/health > /dev/null && echo "OK: Browser MCP is running" || echo "FAIL: Browser MCP failed"

echo ""
echo "All services started!"
echo ""
echo "Logs: logs/"
echo "PIDs: .pids/"
echo ""
echo "To use CLAWS.BOT:"
echo "  export KIMI_BASE_URL=http://localhost:8000"
echo "  export DEFAULT_MODEL=kimi-k2.5"
echo "  cd ../CLAWD.BOT && npx tsx claws-cli.ts \"Your task\""
