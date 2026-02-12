#!/bin/bash
# Stop all services

echo "Stopping all services..."

if [ -f .pids/kimi-api.pid ]; then
  kill $(cat .pids/kimi-api.pid) 2>/dev/null && echo "OK: Stopped Kimi API"
  rm .pids/kimi-api.pid
fi

if [ -f .pids/kimi-mcp.pid ]; then
  kill $(cat .pids/kimi-mcp.pid) 2>/dev/null && echo "OK: Stopped Kimi MCP"
  rm .pids/kimi-mcp.pid
fi

if [ -f .pids/browser-mcp.pid ]; then
  kill $(cat .pids/browser-mcp.pid) 2>/dev/null && echo "OK: Stopped Browser MCP"
  rm .pids/browser-mcp.pid
fi

echo "All services stopped"
