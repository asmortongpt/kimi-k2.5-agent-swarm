# Kimi K2.5 Integration Test Suite

## Overview
Comprehensive integration tests for the Kimi K2.5 Agent Swarm system.

## Test Coverage

### Services Tested
1. **Kimi API Server (Port 8000)** - Main FastAPI application
2. **Kimi MCP Toolhost (Port 8010)** - Model Context Protocol server
3. **Browser MCP Server (Port 8011)** - Playwright-based visual testing

### Test Suite (`test_integration.py`)

#### Test 1: Service Health Checks
- Verifies all 3 services are running
- Checks health endpoints respond correctly
- Validates service status

#### Test 2: Kimi Chat API
- Tests `/api/chat` endpoint
- Verifies real LLM integration
- Validates response structure

#### Test 3: MCP Tools Listing
- Lists available MCP tools
- Verifies `kimi.chat` tool exists
- Checks filesystem tools (fs.read, fs.write)

#### Test 4: Browser MCP Tools
- Lists Browser MCP tools
- Verifies `test_html` tool availability
- Validates tool schema

#### Test 5: MCP Kimi Chat Tool
- End-to-end tool execution via MCP
- Tests complete pipeline: Client → MCP → Kimi API
- Validates tool call responses

#### Test 6: Browser HTML Testing
- Tests Playwright integration
- Verifies screenshot capture
- Validates visual testing pipeline

#### Test 7: Complete System Flow
- Integrates all services in one test
- Tests full system interaction
- Validates end-to-end functionality

#### Test 8: MCP Filesystem Tools
- Tests fs.read tool
- Tests fs.write tool
- Validates file operations

## Prerequisites

### Services Must Be Running
Before running tests, start all three services:

```bash
# Terminal 1: Start Kimi API Server
cd /Users/andrewmorton/Documents/GitHub/kimi
source .venv/bin/activate
python server/api/main.py

# Terminal 2: Start Kimi MCP Toolhost
python server/mcp_toolhost.py

# Terminal 3: Start Browser MCP Server
python server/browser_mcp.py
```

### Dependencies
All required dependencies are in `requirements.txt`:
```bash
pip install -r requirements.txt
```

Required packages:
- `pytest>=8.0.0`
- `pytest-asyncio>=0.23.0`
- `httpx>=0.27.0`

## Running Tests

### Run All Tests
```bash
pytest tests/test_integration.py -v
```

### Run Specific Test
```bash
pytest tests/test_integration.py::test_all_services_running -v
```

### Run with Output
```bash
pytest tests/test_integration.py -v -s
```

### Run with Coverage
```bash
pytest tests/test_integration.py --cov=server --cov-report=html
```

## Test Output

Successful test run will show:
```
✅ Kimi API (8000) is healthy
✅ Kimi MCP (8010) is healthy
✅ Browser MCP (8011) is healthy
✅ Kimi Chat Response: ...
✅ MCP Tools available: ['kimi.chat', 'kimi.swarm_review', 'fs.read', 'fs.write', ...]
✅ Browser MCP Tools available: ['test_html']
✅ MCP kimi.chat Tool Response: ...
✅ Browser MCP test_html Tool Response: 1 screenshot(s) captured
✅ Complete system flow test passed!
```

## Troubleshooting

### Services Not Running
If tests fail with connection errors:
```
Error: Connection refused on localhost:8000
```
**Solution**: Start the Kimi API server first.

### Module Not Found
If tests fail with import errors:
```
ModuleNotFoundError: No module named 'pytest'
```
**Solution**: Install requirements:
```bash
pip install -r requirements.txt
```

### Timeout Errors
If tests timeout:
```
asyncio.TimeoutError
```
**Solution**:
- Increase `TEST_TIMEOUT` in `test_integration.py`
- Check service performance
- Verify network connectivity

### Playwright Not Installed
If Browser MCP tests fail:
```
Error: Playwright not installed
```
**Solution**:
```bash
pip install playwright
playwright install chromium
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Integration Tests                         │
│                  (test_integration.py)                       │
└────────┬─────────────────┬────────────────────┬─────────────┘
         │                 │                    │
         ▼                 ▼                    ▼
    ┌─────────┐      ┌──────────┐       ┌──────────────┐
    │ Kimi API│      │ Kimi MCP │       │ Browser MCP  │
    │  :8000  │      │  :8010   │       │   :8011      │
    └────┬────┘      └────┬─────┘       └──────┬───────┘
         │                │                     │
         ▼                ▼                     ▼
    ┌─────────┐      ┌──────────┐       ┌──────────────┐
    │  Kimi   │      │   MCP    │       │  Playwright  │
    │  K2.5   │      │  Tools   │       │    Browser   │
    │   LLM   │      │          │       │              │
    └─────────┘      └──────────┘       └──────────────┘
```

## Best Practices

1. **Always start services before running tests**
2. **Run tests in order** - use `-v` flag for verbose output
3. **Check logs** - services output helpful debug information
4. **Clean state** - restart services if tests behave unexpectedly
5. **Use virtual environment** - avoid global package conflicts

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.14'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start services
        run: |
          python server/api/main.py &
          python server/mcp_toolhost.py &
          python server/browser_mcp.py &
          sleep 10
      - name: Run tests
        run: pytest tests/test_integration.py -v
```

## Contributing

When adding new integration tests:
1. Follow the existing test pattern
2. Use descriptive test names
3. Add docstrings explaining what's tested
4. Include assertion messages
5. Update this README with new test descriptions

## License
Part of Kimi K2.5 Agent Swarm - Capital Technology Alliance
