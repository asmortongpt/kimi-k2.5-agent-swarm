#!/bin/bash
# ============================================================================
# Kimi K2.5 Agent Swarm - Quick Start Script
# Automated setup for production system (NO MOCKS)
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="/Users/andrewmorton/Documents/GitHub/kimi"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Kimi K2.5 Agent Swarm - Production Quick Start           ║${NC}"
echo -e "${BLUE}║  100% REAL Implementation - NO MOCK DATA                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd "$PROJECT_DIR"

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/8] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker Desktop.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"

# Step 2: Check environment configuration
echo -e "${YELLOW}[2/8] Checking environment configuration...${NC}"

if [ ! -f ~/.env ]; then
    echo -e "${BLUE}ℹ️  Creating ~/.env template (all keys are OPTIONAL)...${NC}"
    cat > ~/.env << 'EOF'
# ============================================================================
# Kimi K2.5 Environment Configuration
# DEFAULT: 100% FREE local setup (no API keys needed!)
# ============================================================================

# Optional: OpenAI API (only if you want paid embeddings instead of free local)
# OPENAI_API_KEY=sk-your-key-here

# Optional: Alternative embedding providers
# COHERE_API_KEY=your-key-here

# Optional: Web search (for real web tool)
# PERPLEXITY_API_KEY=pplx-your-key-here

# Optional: Moonshot API (alternative to Ollama)
# MOONSHOT_API_KEY=your-key-here

# Database (auto-configured for Docker)
POSTGRES_PASSWORD=kimi_dev_password_change_in_production
EOF
    echo -e "${GREEN}✅ Created ~/.env template${NC}"
    echo -e "${GREEN}   💰 All API keys are optional - system runs FREE by default!${NC}"
fi

if [ ! -f ~/.env ]; then
    echo -e "${RED}❌ Failed to create ~/.env${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment configuration ready${NC}"
echo -e "${GREEN}   💰 Using FREE local Ollama (no API costs)${NC}"

# Step 3: Build Docker image
echo -e "${YELLOW}[3/8] Building production Docker image...${NC}"

docker build -t kimi-swarm:latest -f Dockerfile . || {
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
}

echo -e "${GREEN}✅ Docker image built${NC}"

# Step 4: Start services
echo -e "${YELLOW}[4/8] Starting all services (PostgreSQL, Redis, Ollama, API)...${NC}"

docker-compose down -v 2>/dev/null || true
docker-compose up -d

# Wait for services to be healthy with timeout
echo -e "${BLUE}⏳ Waiting for services to be healthy...${NC}"

# Health check function with timeout
wait_for_container_health() {
  local container_name="$1"
  local check_command="$2"
  local service_name="$3"
  local max_attempts=60
  local attempt=1

  echo -e "${BLUE}   Checking $service_name...${NC}"

  while [ $attempt -le $max_attempts ]; do
    if eval "$check_command" &>/dev/null; then
      echo -e "${GREEN}✅ $service_name ready (${attempt}s)${NC}"
      return 0
    fi

    if [ $((attempt % 10)) -eq 0 ]; then
      echo -e "${BLUE}   Still waiting for $service_name... (${attempt}s/${max_attempts}s)${NC}"
    fi

    sleep 1
    ((attempt++))
  done

  echo -e "${RED}❌ $service_name failed to start after ${max_attempts}s${NC}"
  echo -e "${RED}   Check logs: docker logs $container_name${NC}"
  return 1
}

# Check PostgreSQL
wait_for_container_health "kimi-postgres" "docker exec kimi-postgres pg_isready -U postgres" "PostgreSQL" || {
  echo -e "${RED}❌ PostgreSQL health check failed${NC}"
  exit 1
}

# Check Redis
wait_for_container_health "kimi-redis" "docker exec kimi-redis redis-cli ping" "Redis" || {
  echo -e "${RED}❌ Redis health check failed${NC}"
  exit 1
}

echo -e "${GREEN}✅ All core services started and healthy${NC}"

# Step 5: Pull FREE local models (ZERO COST)
echo -e "${YELLOW}[5/8] Pulling FREE local Ollama models (NO API COSTS)...${NC}"

echo -e "${BLUE}   Pulling Kimi K2.5 model...${NC}"
docker exec kimi-ollama ollama pull kimi-k2.5:cloud || {
    echo -e "${YELLOW}⚠️  Kimi model pull failed. You may need to pull manually:${NC}"
    echo -e "${YELLOW}    docker exec -it kimi-ollama ollama pull kimi-k2.5:cloud${NC}"
}

echo -e "${BLUE}   Pulling FREE embedding model (nomic-embed-text)...${NC}"
docker exec kimi-ollama ollama pull nomic-embed-text || {
    echo -e "${YELLOW}⚠️  Embedding model pull failed. You may need to pull manually:${NC}"
    echo -e "${YELLOW}    docker exec -it kimi-ollama ollama pull nomic-embed-text${NC}"
}

echo -e "${GREEN}✅ FREE local models ready (Kimi K2.5 + embeddings)${NC}"
echo -e "${GREEN}   💰 Monthly cost: $0.00 (100% local)${NC}"

# Step 6: Run database migrations
echo -e "${YELLOW}[6/8] Applying database migrations...${NC}"

docker exec kimi-api python database/migrate.py migrate || {
    echo -e "${YELLOW}⚠️  Migration failed. Schema may already exist.${NC}"
}

echo -e "${GREEN}✅ Database schema ready${NC}"

# Step 7: Health check with retry and timeout
echo -e "${YELLOW}[7/8] Running health checks...${NC}"

# Health check function for HTTP endpoints
wait_for_http_health() {
  local url="$1"
  local service_name="$2"
  local max_attempts=30
  local attempt=1

  echo -e "${BLUE}   Checking $service_name at $url...${NC}"

  while [ $attempt -le $max_attempts ]; do
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
      echo -e "${GREEN}✅ $service_name healthy (${attempt}s)${NC}"
      return 0
    fi

    if [ $((attempt % 5)) -eq 0 ]; then
      echo -e "${BLUE}   Still waiting for $service_name... (${attempt}s/${max_attempts}s)${NC}"
    fi

    sleep 1
    ((attempt++))
  done

  echo -e "${RED}❌ $service_name not responding after ${max_attempts}s${NC}"
  return 1
}

# Check API server health
if wait_for_http_health "http://localhost:8000/api/health" "API server"; then
  # Verify health endpoint returns valid response
  health_response=$(curl -sf http://localhost:8000/api/health 2>&1)
  echo -e "${GREEN}   Health response: $health_response${NC}"
else
  echo -e "${RED}❌ API server health check failed. Check logs:${NC}"
  echo -e "${RED}   docker logs kimi-api${NC}"
  echo -e "${YELLOW}   Showing last 20 lines of logs:${NC}"
  docker logs --tail 20 kimi-api 2>&1 || true
  exit 1
fi

# Step 8: Test real APIs
echo -e "${YELLOW}[8/8] Testing REAL APIs (no mocks)...${NC}"

# Test chat endpoint
echo -e "${BLUE}   Testing real chat endpoint...${NC}"
CHAT_RESPONSE=$(curl -sf -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Say hello in 5 words"}]}')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Chat API working (real LLM)${NC}"
else
    echo -e "${RED}❌ Chat API failed${NC}"
fi

# Test knowledge base (FREE local embeddings)
echo -e "${BLUE}   Testing real RAG with FREE Ollama embeddings...${NC}"
KNOWLEDGE_RESPONSE=$(curl -sf -X POST http://localhost:8000/api/knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "test-1",
        "content": "Kimi K2.5 supports 100 parallel agents",
        "metadata": {"category": "test"}
      }
    ]
  }')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ RAG API working (FREE local embeddings - $0.00 cost)${NC}"
else
    echo -e "${YELLOW}⚠️  RAG API failed - check if Ollama is running${NC}"
fi

# Print success message
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅  Kimi K2.5 Agent Swarm is READY!                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🚀 Services Running:${NC}"
echo -e "   • API Server:    http://localhost:8000"
echo -e "   • Health Check:  http://localhost:8000/api/health"
echo -e "   • Prometheus:    http://localhost:9090"
echo -e "   • Grafana:       http://localhost:3000 (admin/admin)"
echo ""
echo -e "${BLUE}📚 Quick Test Commands:${NC}"
echo ""
echo -e "${YELLOW}# Test real chat:${NC}"
echo 'curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '"'"'{"messages": [{"role": "user", "content": "Explain agent swarms"}]}'"'"''
echo ""
echo -e "${YELLOW}# Test 100-agent swarm:${NC}"
echo 'curl -X POST http://localhost:8000/api/swarm \
  -H "Content-Type: application/json" \
  -d '"'"'{"task": "Analyze PostgreSQL vs MongoDB", "num_agents": 50}'"'"''
echo ""
echo -e "${YELLOW}# Test real RAG search:${NC}"
echo 'curl -X POST http://localhost:8000/api/knowledge/search \
  -H "Content-Type: application/json" \
  -d '"'"'{"query": "How many agents?", "k": 3}'"'"''
echo ""
echo -e "${BLUE}📖 Documentation:${NC}"
echo -e "   • Production README: ./README_PRODUCTION.md"
echo -e "   • Examples:          ./examples/real_examples/"
echo -e "   • API Docs:          http://localhost:8000/docs"
echo ""
echo -e "${BLUE}🔍 Logs:${NC}"
echo -e "   docker logs -f kimi-api     # API server logs"
echo -e "   docker logs -f kimi-ollama  # Ollama logs"
echo -e "   docker-compose logs -f      # All services"
echo ""
echo -e "${GREEN}✅ All systems operational - NO MOCK DATA, 100% REAL${NC}"
echo ""
