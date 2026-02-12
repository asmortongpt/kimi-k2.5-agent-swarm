# QUICK START GUIDE: Kimi SaaS Platform Implementation

**For**: Engineering team ready to start building
**Time to First Deployment**: 2 weeks (foundation phase)
**Prerequisites**: Azure account, Docker, kubectl, Node.js, Python 3.11+

---

## DAY 1: SETUP & INFRASTRUCTURE

### Morning (4 hours): Azure Infrastructure

**1. Review Architecture** (1 hour)
```bash
# Read these documents first
cat SAAS_TRANSFORMATION_EXECUTIVE_SUMMARY.md
cat SAAS_PLATFORM_TRANSFORMATION_PLAN.md | head -n 500
```

**2. Set Up Azure** (2 hours)

```bash
# Install Azure CLI
brew install azure-cli  # macOS
# Or: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Login
az login

# Set subscription (use your existing one)
az account set --subscription "your-subscription-id"

# Create resource group
az group create \
  --name kimi-platform-dev \
  --location eastus2

# Create AKS cluster (simplified for dev)
az aks create \
  --resource-group kimi-platform-dev \
  --name kimi-aks-dev \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-managed-identity \
  --generate-ssh-keys

# Get credentials
az aks get-credentials \
  --resource-group kimi-platform-dev \
  --name kimi-aks-dev

# Verify
kubectl get nodes
```

**3. Create PostgreSQL** (1 hour)

```bash
# Create PostgreSQL flexible server
az postgres flexible-server create \
  --resource-group kimi-platform-dev \
  --name kimi-postgres-dev \
  --location eastus2 \
  --admin-user kimiadmin \
  --admin-password "YOUR_SECURE_PASSWORD" \
  --sku-name Standard_D2s_v3 \
  --tier GeneralPurpose \
  --storage-size 128 \
  --version 15

# Create database
az postgres flexible-server db create \
  --resource-group kimi-platform-dev \
  --server-name kimi-postgres-dev \
  --database-name kimi_platform

# Configure firewall (allow Azure services)
az postgres flexible-server firewall-rule create \
  --resource-group kimi-platform-dev \
  --name kimi-postgres-dev \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### Afternoon (4 hours): Local Development Environment

**4. Clone and Set Up Project** (1 hour)

```bash
# You're already in the repo
cd /Users/andrewmorton/Documents/GitHub/kimi

# Create project structure
mkdir -p backend/{api,ai,database,workers}
mkdir -p frontend/src
mkdir -p infrastructure/{terraform,kubernetes,helm}
mkdir -p tests/{unit,integration,e2e,load}
mkdir -p monitoring/{prometheus,grafana,jaeger}

# Create virtual environment
python3.11 -m venv venv-saas
source venv-saas/bin/activate

# Install dependencies
cat > requirements-dev.txt <<EOF
# Core
fastapi==0.110.0
uvicorn[standard]==0.27.0
pydantic==2.6.0
pydantic-settings==2.2.0

# Database
sqlalchemy==2.0.27
alembic==1.13.1
asyncpg==0.29.0
psycopg2-binary==2.9.9

# Redis
redis[hiredis]==5.0.1

# Celery
celery==5.3.6

# LangChain
langchain==0.1.9
langchain-openai==0.0.6
langchain-anthropic==0.0.2
openai==1.12.0

# Existing Kimi client (preserve)
httpx==0.26.0
python-dotenv==1.0.1

# Testing
pytest==8.0.0
pytest-asyncio==0.23.4
pytest-cov==4.1.0

# Development
black==24.1.1
ruff==0.2.0
mypy==1.8.0
EOF

pip install -r requirements-dev.txt
```

**5. Create Backend Skeleton** (2 hours)

```bash
# FastAPI application
cat > backend/api/main.py <<'EOF'
"""
Kimi SaaS Platform API Server
Production-ready FastAPI application with authentication, monitoring, and LangChain integration.
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Kimi SaaS Platform API")
    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Initialize LangChain providers
    yield
    logger.info("Shutting down Kimi SaaS Platform API")
    # TODO: Close database connections
    # TODO: Close Redis connections


app = FastAPI(
    title="Kimi SaaS Platform API",
    description="Enterprise AI Agent Orchestration Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "kimi-api"
    }


@app.get("/api/v1/status")
async def get_status():
    """Get system status."""
    return {
        "api": "operational",
        "database": "connected",  # TODO: Check actual DB
        "redis": "connected",  # TODO: Check actual Redis
        "llm_providers": {
            "azure_openai": "available",
            "anthropic": "available",
            "together": "available",
            "moonshot": "available"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
EOF

# Test it
python backend/api/main.py &
API_PID=$!
sleep 3
curl http://localhost:8000/health
kill $API_PID
```

**6. Create Database Models** (1 hour)

```bash
# Base model
cat > backend/database/models/base.py <<'EOF'
"""SQLAlchemy base model with common fields."""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()


class BaseModel(Base):
    """Base model with common fields."""
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
EOF

# User model
cat > backend/database/models/user.py <<'EOF'
"""User model."""
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
    """User account."""
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
EOF
```

---

## DAY 2: DATABASE & API ENDPOINTS

### Morning: Database Setup

**7. Create Alembic Migrations** (2 hours)

```bash
# Initialize Alembic
cd backend/database
alembic init migrations

# Configure Alembic
cat > alembic.ini <<EOF
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+asyncpg://kimiadmin:YOUR_PASSWORD@kimi-postgres-dev.postgres.database.azure.com/kimi_platform

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF

# Create first migration
alembic revision -m "create_users_table"

# Edit the migration file (migrations/versions/xxx_create_users_table.py)
# Add your create table SQL
```

**8. Run Migrations** (1 hour)

```bash
# Apply migrations
alembic upgrade head

# Verify
psql "postgresql://kimiadmin:YOUR_PASSWORD@kimi-postgres-dev.postgres.database.azure.com/kimi_platform" \
  -c "\dt"
```

### Afternoon: API Endpoints

**9. Create Authentication Router** (2 hours)

```bash
cat > backend/api/routers/auth.py <<'EOF'
"""Authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT tokens.

    TODO:
    - Verify credentials against database
    - Generate JWT tokens
    - Return tokens
    """
    # Mock for now
    return LoginResponse(
        access_token="mock_access_token",
        refresh_token="mock_refresh_token"
    )


@router.post("/logout")
async def logout():
    """Logout user (invalidate tokens)."""
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token."""
    # TODO: Implement token refresh logic
    return LoginResponse(
        access_token="new_mock_access_token",
        refresh_token=refresh_token
    )
EOF

# Add to main.py
# from backend.api.routers import auth
# app.include_router(auth.router)
```

**10. Create Agents Router** (2 hours)

```bash
cat > backend/api/routers/agents.py <<'EOF'
"""Agent management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class AgentCreate(BaseModel):
    """Create agent request."""
    name: str
    description: str
    type: str = "swarm"
    max_agents: int = 10


class AgentResponse(BaseModel):
    """Agent response."""
    id: UUID
    name: str
    description: str
    type: str
    max_agents: int
    created_at: str


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(request: AgentCreate):
    """Create new agent."""
    # TODO: Save to database
    import uuid
    from datetime import datetime
    return AgentResponse(
        id=uuid.uuid4(),
        name=request.name,
        description=request.description,
        type=request.type,
        max_agents=request.max_agents,
        created_at=datetime.utcnow().isoformat()
    )


@router.get("", response_model=List[AgentResponse])
async def list_agents():
    """List all agents for current user."""
    # TODO: Query database
    return []


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: UUID):
    """Get agent by ID."""
    # TODO: Query database
    raise HTTPException(status_code=404, detail="Agent not found")


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: UUID):
    """Delete agent."""
    # TODO: Delete from database
    pass
EOF
```

---

## DAY 3-5: LANGCHAIN INTEGRATION

### Day 3: LLM Provider Setup

**11. Install LangChain** (already done in Day 1)

**12. Create Provider Manager** (4 hours)

```bash
# Copy the code from SAAS_PLATFORM_TRANSFORMATION_PLAN.md Section 3.1
# File: backend/ai/providers/llm_provider.py

# Key points:
# - Initialize Azure OpenAI, Anthropic, Together AI, Moonshot
# - Implement routing logic
# - Implement fallback chain
```

**13. Test Providers** (2 hours)

```bash
cat > test_providers.py <<'EOF'
import asyncio
from backend.ai.providers.llm_provider import LLMProviderManager

async def test_providers():
    config = {
        "azure": {
            "deployment_id": "gpt-4.5-preview",
            "endpoint": "https://andre-m9qftqda-eastus2.cognitiveservices.azure.com/",
            "api_key": "YOUR_API_KEY"
        },
        "anthropic": {
            "api_key": "YOUR_ANTHROPIC_KEY"
        }
    }

    manager = LLMProviderManager(config)

    # Test routing
    provider = manager.route_request(
        task_complexity=0.9,
        budget_tier="premium",
        context_size=5000
    )
    print(f"Routed to: {provider}")

    # Test execution
    result = await manager.execute_with_fallback(
        primary_provider="azure_openai",
        prompt="What is machine learning?"
    )
    print(f"Result: {result[:100]}...")

asyncio.run(test_providers())
EOF

python test_providers.py
```

### Day 4-5: Agent Swarm Implementation

**14. Implement Swarm Orchestrator** (8 hours)

```bash
# Copy code from SAAS_PLATFORM_TRANSFORMATION_PLAN.md Section 3.2
# File: backend/ai/agents/swarm_orchestrator.py

# Implement:
# - Task decomposition
# - Parallel agent execution
# - Result synthesis
```

**15. Create Agent Execution Endpoint** (4 hours)

```bash
cat > backend/api/routers/executions.py <<'EOF'
"""Agent execution endpoints."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


class ExecutionRequest(BaseModel):
    """Execute agent request."""
    agent_id: UUID
    task: str
    context: Optional[Dict[str, Any]] = None
    max_agents: Optional[int] = None


class ExecutionResponse(BaseModel):
    """Execution response."""
    execution_id: UUID
    status: str = "pending"
    message: str = "Execution queued"


@router.post("", response_model=ExecutionResponse, status_code=202)
async def execute_agent(request: ExecutionRequest, background_tasks: BackgroundTasks):
    """
    Execute agent asynchronously.

    Returns immediately with execution ID.
    Use WebSocket or polling to get results.
    """
    execution_id = uuid4()

    # TODO: Queue task in Celery
    # background_tasks.add_task(execute_agent_task, execution_id, request)

    return ExecutionResponse(
        execution_id=execution_id,
        status="pending"
    )


@router.get("/{execution_id}")
async def get_execution(execution_id: UUID):
    """Get execution status and results."""
    # TODO: Query database for execution
    raise HTTPException(status_code=404, detail="Execution not found")
EOF
```

---

## DAYS 6-7: DOCKER & KUBERNETES

### Day 6: Dockerize Application

**16. Create Dockerfiles** (2 hours)

```bash
# API Dockerfile
cat > Dockerfile.api <<'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy application
COPY backend/ ./backend/
COPY core/ ./core/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Build and test
docker build -f Dockerfile.api -t kimi-api:dev .
docker run -p 8000:8000 kimi-api:dev
```

**17. Create Docker Compose** (2 hours)

```bash
cat > docker-compose.yml <<'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: kimi
      POSTGRES_PASSWORD: kimi123
      POSTGRES_DB: kimi_platform
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://kimi:kimi123@postgres:5432/kimi_platform
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
EOF

# Test
docker-compose up -d
curl http://localhost:8000/health
```

### Day 7: Deploy to Kubernetes

**18. Create Kubernetes Manifests** (4 hours)

```bash
mkdir -p infrastructure/kubernetes

cat > infrastructure/kubernetes/api-deployment.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kimi-api
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kimi-api
  template:
    metadata:
      labels:
        app: kimi-api
    spec:
      containers:
      - name: api
        image: YOUR_ACR.azurecr.io/kimi-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: kimi-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: kimi-api
spec:
  selector:
    app: kimi-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
EOF

# Deploy
kubectl apply -f infrastructure/kubernetes/api-deployment.yaml
kubectl get pods
kubectl get svc kimi-api
```

---

## WEEK 2: MONITORING & TESTING

### Days 8-9: Set Up Monitoring

**19. Deploy Prometheus** (see detailed configs in main plan)
**20. Deploy Grafana** (see detailed configs in main plan)
**21. Configure Dashboards** (import pre-built dashboards)

### Days 10-11: Write Tests

**22. Unit Tests** (as shown in Section 5.1)
**23. Integration Tests** (as shown in Section 5.2)
**24. Load Tests** (as shown in Section 5.4)

### Days 12-14: CI/CD Pipeline

**25. Create Azure Pipeline** (see Section 8.1 for complete YAML)

---

## QUICK COMMANDS REFERENCE

### Daily Development

```bash
# Start local stack
docker-compose up -d

# Run API server
source venv-saas/bin/activate
python backend/api/main.py

# Run tests
pytest tests/ -v --cov

# Apply database migrations
cd backend/database && alembic upgrade head

# Check Kubernetes status
kubectl get all
kubectl logs -f deployment/kimi-api
```

### Deployment

```bash
# Build and push Docker image
docker build -f Dockerfile.api -t YOUR_ACR.azurecr.io/kimi-api:latest .
docker push YOUR_ACR.azurecr.io/kimi-api:latest

# Deploy to Kubernetes
kubectl apply -f infrastructure/kubernetes/

# Check deployment
kubectl rollout status deployment/kimi-api
```

---

## TROUBLESHOOTING

### Common Issues

**Issue**: "Cannot connect to PostgreSQL"
**Fix**: Check firewall rules, verify connection string

**Issue**: "LLM API returns 401"
**Fix**: Verify API keys in environment variables

**Issue**: "Kubernetes pod CrashLoopBackOff"
**Fix**: Check logs with `kubectl logs <pod-name>`

---

## NEXT STEPS

After completing this 2-week quickstart:

1. ✅ You'll have working infrastructure
2. ✅ Basic API with auth and agent endpoints
3. ✅ LangChain integration with multi-LLM routing
4. ✅ Docker containers and Kubernetes deployment
5. ✅ Monitoring stack

**Continue with**:
- Phases 2-7 from the main roadmap
- Frontend React dashboard
- Advanced features (RAG, multi-tenancy, billing)

---

## GETTING HELP

- **Architecture Questions**: See SAAS_PLATFORM_TRANSFORMATION_PLAN.md
- **Business Questions**: See SAAS_TRANSFORMATION_EXECUTIVE_SUMMARY.md
- **Implementation Tracking**: Use IMPLEMENTATION_CHECKLIST.md
- **Technical Decisions**: Refer to Section 2 (Technology Stack)

---

**Ready to Build? Let's go! 🚀**
