#!/bin/bash
# Quick environment setup for CLAWS.BOT + Kimi K2.5 integration
# Usage: source export-env.sh

export KIMI_BASE_URL="http://localhost:8000"
export KIMI_MCP_URL="http://localhost:8010"
export BROWSER_MCP_URL="http://localhost:8011"
export DEFAULT_MODEL="kimi-k2.5"

echo "✅ Environment variables set:"
echo "   KIMI_BASE_URL=$KIMI_BASE_URL"
echo "   KIMI_MCP_URL=$KIMI_MCP_URL"
echo "   BROWSER_MCP_URL=$BROWSER_MCP_URL"
echo "   DEFAULT_MODEL=$DEFAULT_MODEL"
echo ""
echo "🚀 Ready to use CLAWS.BOT with Kimi K2.5!"
echo ""
echo "Next steps:"
echo "  1. ./start-all.sh              # Start all services"
echo "  2. cd ../CLAWD.BOT             # Navigate to CLAWS.BOT"
echo "  3. npx tsx claws-cli.ts \"Your task\""
