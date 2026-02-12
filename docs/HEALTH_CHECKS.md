# Health Check System Documentation

## Overview

The health check system provides comprehensive service monitoring and verification for all deployment scripts. It ensures services are properly started and responding before proceeding with deployment steps.

**Issue Fixed**: High Priority Issue #8 - No Health Checks in Deployment Scripts

## Features

- ✅ HTTP endpoint health checking with configurable timeouts
- ✅ Docker container health verification
- ✅ TCP port connectivity testing
- ✅ Process health monitoring
- ✅ Automatic retry mechanisms
- ✅ Proper timeout enforcement
- ✅ PID tracking and cleanup
- ✅ Comprehensive error reporting with log references

## Components

### 1. Health Check Library (`scripts/lib/health-checks.sh`)

Reusable shell functions for health checking:

#### Available Functions

##### `wait_for_http_endpoint URL SERVICE_NAME [TIMEOUT] [INTERVAL]`
Waits for an HTTP endpoint to respond successfully.

**Parameters:**
- `URL`: HTTP endpoint to check
- `SERVICE_NAME`: Display name for logging
- `TIMEOUT`: Maximum wait time in seconds (default: 60)
- `INTERVAL`: Time between checks in seconds (default: 2)

**Example:**
```bash
wait_for_http_endpoint "http://localhost:8000/api/health" "API Server" 60 2
```

##### `wait_for_docker_container CONTAINER_NAME CHECK_COMMAND SERVICE_NAME [TIMEOUT] [INTERVAL]`
Checks if a Docker container is healthy using a custom command.

**Example:**
```bash
wait_for_docker_container "kimi-postgres" \
  "docker exec kimi-postgres pg_isready -U postgres" \
  "PostgreSQL" 60 2
```

##### `wait_for_tcp_port HOST PORT SERVICE_NAME [TIMEOUT] [INTERVAL]`
Checks if a TCP port is accepting connections.

**Example:**
```bash
wait_for_tcp_port "localhost" 5432 "PostgreSQL" 30 2
```

##### `check_process_health PID SERVICE_NAME`
Verifies a process is still running.

**Example:**
```bash
check_process_health $API_PID "API Server"
```

##### `wait_for_postgres CONTAINER_NAME [USERNAME] [TIMEOUT] [INTERVAL]`
PostgreSQL-specific health check.

**Example:**
```bash
wait_for_postgres "kimi-postgres" "postgres" 60 2
```

##### `wait_for_redis CONTAINER_NAME [TIMEOUT] [INTERVAL]`
Redis-specific health check.

**Example:**
```bash
wait_for_redis "kimi-redis" 60 2
```

##### `run_health_checks CHECK_COMMAND1 CHECK_COMMAND2 ...`
Runs multiple health checks and reports overall status.

**Example:**
```bash
run_health_checks \
  "wait_for_http_endpoint http://localhost:8000 API 30 2" \
  "wait_for_postgres kimi-postgres postgres 30 2"
```

##### `retry_health_check FUNCTION_NAME MAX_RETRIES [RETRY_DELAY] [ARGS...]`
Retries a health check function multiple times.

**Example:**
```bash
retry_health_check wait_for_http_endpoint 3 5 \
  "http://localhost:8000/api/health" "API" 30 2
```

### 2. Azure Agent Deployment Script (`azure-agent-deployment.sh`)

Production-ready deployment script with comprehensive health checks.

**Features:**
- PID tracking in `/tmp/kimi-pids/`
- Log collection in `/tmp/kimi-logs/`
- Automatic cleanup on exit/interrupt/termination
- Health checks for all services
- Periodic health monitoring
- Detailed error reporting

**Usage:**
```bash
./azure-agent-deployment.sh
```

**Environment Variables:**
- `PROJECT_DIR`: Project root directory (default: /Users/andrewmorton/Documents/GitHub/kimi)
- `FRONTEND_PORT`: Frontend server port (default: 5173)
- `API_PORT`: API server port (default: 3001)
- `HEALTH_CHECK_TIMEOUT`: Default health check timeout in seconds (default: 60)
- `HEALTH_CHECK_INTERVAL`: Health check interval in seconds (default: 2)

**Services Started:**
1. PostgreSQL (Docker container)
2. API Server (Node.js)
3. Frontend Dev Server (Vite)
4. Ollama (optional)

**Health Check Flow:**
1. Database connectivity verification
2. API server startup with health endpoint check
3. Frontend server startup
4. Optional services (Ollama)
5. Comprehensive health verification
6. Periodic health monitoring (every 60s)

### 3. Enhanced Quickstart Script (`scripts/quickstart.sh`)

Docker Compose deployment with health checks.

**Improvements:**
- Container health checking with timeouts
- HTTP endpoint verification
- Detailed error logging
- Service-specific health check functions

**Usage:**
```bash
./scripts/quickstart.sh
```

### 4. Docker Compose Configuration (`docker-compose.yml`)

Enhanced with healthcheck configurations for all services:

#### PostgreSQL
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
```

#### Redis
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

#### Ollama
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
  interval: 15s
  timeout: 10s
  retries: 3
  start_period: 20s
```

#### API Server
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

#### Qdrant
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s
```

## Testing

### Quick Test
Run basic health check tests:
```bash
./scripts/quick-health-test.sh
```

**Tests:**
1. HTTP endpoint success detection
2. HTTP endpoint failure detection
3. Process health monitoring
4. Timeout enforcement

### Comprehensive Test Suite
Run full test suite with intentional failures:
```bash
./scripts/test-health-checks.sh
```

**Tests:**
1. HTTP endpoint success/failure cases
2. TCP port success/failure cases
3. Process health success/failure cases
4. Comprehensive multi-check scenarios
5. Retry mechanism testing
6. Docker container health (if Docker available)
7. Timeout enforcement verification

## Usage Examples

### Basic Usage in Deployment Scripts

```bash
#!/bin/bash
set -euo pipefail

# Source health check library
source "$(dirname $0)/lib/health-checks.sh"

# Start service
npm run dev > /tmp/service.log 2>&1 &
SERVICE_PID=$!
echo $SERVICE_PID > /tmp/service.pid

# Wait for service to be ready
if wait_for_http_endpoint "http://localhost:5173" "Frontend" 60 2; then
  echo "Service started successfully"
else
  echo "Service failed to start"
  tail -20 /tmp/service.log
  exit 1
fi

# Continue with deployment...
```

### Docker Compose Health Checks

```bash
# Wait for PostgreSQL
wait_for_postgres "kimi-postgres" "postgres" 60 2 || {
  echo "PostgreSQL failed to start"
  docker logs kimi-postgres
  exit 1
}

# Wait for Redis
wait_for_redis "kimi-redis" 60 2 || {
  echo "Redis failed to start"
  docker logs kimi-redis
  exit 1
}
```

### Multiple Service Checks

```bash
# Run all health checks together
run_health_checks \
  "wait_for_postgres kimi-postgres postgres 60 2" \
  "wait_for_redis kimi-redis 60 2" \
  "wait_for_http_endpoint http://localhost:8000/api/health API 60 2" \
  "wait_for_http_endpoint http://localhost:5173 Frontend 60 2"
```

### Retry on Transient Failures

```bash
# Retry health check up to 3 times with 5s delay
retry_health_check wait_for_http_endpoint 3 5 \
  "http://localhost:8000/api/health" "API Server" 30 2
```

## Best Practices

### 1. Always Set Timeouts
Never wait indefinitely - always specify reasonable timeouts:
```bash
# Good - 60 second timeout
wait_for_http_endpoint "http://localhost:8000" "API" 60 2

# Bad - could wait forever
while ! curl -f http://localhost:8000; do sleep 1; done
```

### 2. Use Appropriate Intervals
Balance responsiveness with resource usage:
```bash
# Fast services (1-2 seconds)
wait_for_http_endpoint "http://localhost:8000" "API" 30 1

# Slow services (2-5 seconds)
wait_for_http_endpoint "http://localhost:8000" "API" 60 5
```

### 3. Store PIDs for Cleanup
Always track process IDs for proper cleanup:
```bash
npm start &
PID=$!
echo $PID > /tmp/service.pid

# Cleanup function
cleanup() {
  kill $(cat /tmp/service.pid) 2>/dev/null || true
  rm -f /tmp/service.pid
}
trap cleanup EXIT
```

### 4. Check Logs on Failure
Always provide log references when health checks fail:
```bash
if ! wait_for_http_endpoint "http://localhost:8000" "API" 60 2; then
  echo "API failed to start. Last 20 log lines:"
  tail -20 /tmp/api.log
  exit 1
fi
```

### 5. Use Service-Specific Functions
Use specialized functions when available:
```bash
# Good - uses PostgreSQL-specific function
wait_for_postgres "kimi-postgres" "postgres"

# Less ideal - generic approach
wait_for_docker_container "kimi-postgres" \
  "docker exec kimi-postgres pg_isready -U postgres" \
  "PostgreSQL"
```

## Monitoring

### View Service Status
```bash
# Check all running services
for pid_file in /tmp/kimi-pids/*.pid; do
  service=$(basename "$pid_file" .pid)
  pid=$(cat "$pid_file")
  if kill -0 "$pid" 2>/dev/null; then
    echo "✅ $service running (PID: $pid)"
  else
    echo "❌ $service stopped (PID: $pid)"
  fi
done
```

### View Service Logs
```bash
# View logs
tail -f /tmp/kimi-logs/api.log
tail -f /tmp/kimi-logs/frontend.log
tail -f /tmp/kimi-logs/ollama.log
```

### Manual Health Checks
```bash
# API health
curl http://localhost:3001/api/health

# Frontend
curl http://localhost:5173

# Ollama
curl http://localhost:11434/api/tags

# PostgreSQL
docker exec fleet-postgres pg_isready -U fleet_user

# Redis
docker exec kimi-redis redis-cli ping
```

## Troubleshooting

### Health Check Fails Immediately
**Symptom**: Health check fails instantly without waiting

**Solution**: Check if the service actually started:
```bash
# Check if process is running
ps aux | grep <service-name>

# Check process by PID
kill -0 $PID && echo "Running" || echo "Dead"

# View logs
tail -50 /tmp/kimi-logs/<service>.log
```

### Health Check Timeout
**Symptom**: Health check waits full timeout and fails

**Causes**:
1. Service takes longer to start than timeout allows
2. Service failed to start but process is running
3. Wrong URL/endpoint
4. Network/firewall issues

**Solutions**:
```bash
# Increase timeout
wait_for_http_endpoint "http://localhost:8000" "API" 120 2

# Check if service is listening
lsof -i :8000

# Test endpoint manually
curl -v http://localhost:8000/api/health
```

### PID File Issues
**Symptom**: Cleanup fails or can't find process

**Solution**:
```bash
# Ensure PID directory exists
mkdir -p /tmp/kimi-pids

# Check PID file permissions
ls -la /tmp/kimi-pids/

# Manual cleanup
rm -f /tmp/kimi-pids/*.pid
killall node  # Careful - kills all node processes
```

### Docker Container Health Issues
**Symptom**: Container health checks fail

**Solutions**:
```bash
# Check container status
docker ps -a

# View container logs
docker logs <container-name>

# Check container health
docker inspect <container-name> | grep -A 10 Health

# Restart container
docker restart <container-name>
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Deploy with Health Checks
  run: |
    ./azure-agent-deployment.sh
  timeout-minutes: 10
```

### Azure DevOps Example
```yaml
- script: |
    ./azure-agent-deployment.sh
  displayName: 'Deploy with Health Checks'
  timeoutInMinutes: 10
```

## Security Considerations

1. **PID Files**: Stored in `/tmp` - ensure proper permissions
2. **Log Files**: May contain sensitive data - rotate and clean regularly
3. **Health Endpoints**: Should not expose sensitive system information
4. **Process Cleanup**: Always cleanup PIDs on exit to prevent orphaned processes

## Performance Impact

- **HTTP Checks**: Minimal overhead (~10ms per check)
- **Docker Checks**: Slight overhead from `docker exec` (~50ms)
- **TCP Checks**: Minimal overhead (~5ms per check)
- **Recommended Check Interval**: 1-5 seconds based on service

## Future Enhancements

Potential improvements:
- [ ] Kubernetes readiness/liveness probe integration
- [ ] Prometheus metrics export
- [ ] Health check result caching
- [ ] Parallel health checking
- [ ] Custom health check plugins
- [ ] Email/Slack notifications on failures

## References

- Docker Healthcheck Documentation: https://docs.docker.com/engine/reference/builder/#healthcheck
- Kubernetes Probes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
- Production Health Checks Best Practices: https://12factor.net/

## Support

For issues or questions:
1. Check logs in `/tmp/kimi-logs/`
2. Run health check tests: `./scripts/quick-health-test.sh`
3. Review this documentation
4. Open an issue with logs and error messages
