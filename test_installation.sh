#!/bin/bash
# Quick installation test script

echo "🧪 Testing Kimi K2.5 Installation"
echo "=================================="
echo ""

# Test 1: Check if Ollama is installed
echo "Test 1: Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is installed: $(which ollama)"
else
    echo "❌ Ollama not found. Please install: https://ollama.com"
    exit 1
fi
echo ""

# Test 2: Check if Ollama is running
echo "Test 2: Checking Ollama service..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama service is running"
else
    echo "⚠️  Ollama service not running. Starting..."
    ollama serve &
    sleep 2
fi
echo ""

# Test 3: Check if Kimi model is installed
echo "Test 3: Checking Kimi K2.5 model..."
if ollama list | grep -q "kimi-k2.5:cloud"; then
    echo "✅ Kimi K2.5 model is installed"
else
    echo "⚠️  Kimi K2.5 not found. Downloading..."
    ollama pull kimi-k2.5:cloud
fi
echo ""

# Test 4: Test basic query
echo "Test 4: Testing basic query..."
response=$(curl -s http://localhost:11434/api/generate -d '{
  "model": "kimi-k2.5:cloud",
  "prompt": "Say only: Kimi K2.5 is working!",
  "stream": false
}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('response', 'No response'))" 2>/dev/null)

if [ -n "$response" ] && [ "$response" != "No response" ]; then
    echo "✅ Basic query successful!"
    echo "   Response: ${response:0:100}..."
else
    echo "❌ Basic query failed"
    exit 1
fi
echo ""

# Test 5: Python dependencies
echo "Test 5: Checking Python dependencies..."
if python3 -c "import httpx; import dotenv" 2>/dev/null; then
    echo "✅ Python dependencies installed"
else
    echo "⚠️  Installing Python dependencies..."
    pip3 install -q -r requirements.txt
    echo "✅ Python dependencies installed"
fi
echo ""

# Test 6: Run Python installation test
echo "Test 6: Running Python installation test..."
echo "-------------------------------------------"
python3 test_installation.py
echo ""

# Summary
echo "=================================="
echo "✅ Installation Test Complete!"
echo "=================================="
echo ""
echo "🚀 You're ready to use Kimi K2.5!"
echo ""
echo "Try these commands:"
echo "  • Interactive chat: ollama run kimi-k2.5:cloud"
echo "  • Python client: python3 kimi_client.py"
echo "  • Code analysis: python3 examples/code_analysis_swarm.py"
echo ""
echo "📖 Documentation:"
echo "  • Quick Start: cat QUICKSTART.md"
echo "  • Full Guide: cat README.md"
echo ""
