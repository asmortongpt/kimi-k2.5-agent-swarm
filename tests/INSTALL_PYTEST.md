# Installing pytest for Integration Tests

## Current Status

✅ **Test file created and validated**
- Location: `/Users/andrewmorton/Documents/GitHub/kimi/tests/test_integration.py`
- Syntax: Valid
- Tests: 9 comprehensive integration tests

✅ **httpx installed**
- Version: 0.28.1

⚠️ **pytest needs installation**

## Installation Instructions

### Option 1: Install in Virtual Environment (Recommended)
```bash
cd /Users/andrewmorton/Documents/GitHub/kimi
source .venv/bin/activate
pip install pytest pytest-asyncio
```

### Option 2: Install from requirements.txt
```bash
cd /Users/andrewmorton/Documents/GitHub/kimi
source .venv/bin/activate
pip install -r requirements.txt
```

### Option 3: Manual Installation (if venv has issues)
```bash
# Recreate virtual environment
cd /Users/andrewmorton/Documents/GitHub/kimi
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Verify Installation

After installing pytest, verify with:
```bash
python tests/validate_test_setup.py
```

Expected output:
```
✅ pytest: Available
✅ pytest_asyncio: Available
✅ httpx: Available
✅ test_integration.py: Syntax valid
✅ ALL CHECKS PASSED - Ready to run tests
```

## Run Tests

Once pytest is installed:

1. **Start all services** (in separate terminals):
```bash
# Terminal 1: Kimi API
cd /Users/andrewmorton/Documents/GitHub/kimi
source .venv/bin/activate
python server/api/main.py

# Terminal 2: Kimi MCP
python server/mcp_toolhost.py

# Terminal 3: Browser MCP
python server/browser_mcp.py
```

2. **Run tests** (in a 4th terminal):
```bash
cd /Users/andrewmorton/Documents/GitHub/kimi
source .venv/bin/activate
pytest tests/test_integration.py -v -s
```

## Troubleshooting

### Issue: "No module named 'pytest'"
**Solution**: Run the installation commands above

### Issue: pip hangs or takes very long
**Solution**:
```bash
pip install --no-cache-dir pytest pytest-asyncio
```

### Issue: Virtual environment corrupted
**Solution**: Recreate venv (see Option 3 above)

### Issue: Permission denied
**Solution**: Make sure you're in the virtual environment:
```bash
source .venv/bin/activate
which python  # Should show path with .venv
```

## Quick Start (All-in-One)

```bash
cd /Users/andrewmorton/Documents/GitHub/kimi
source .venv/bin/activate
pip install pytest pytest-asyncio
python tests/validate_test_setup.py
pytest tests/test_integration.py -v
```

## Dependencies in requirements.txt

The following are already specified in `requirements.txt`:
```
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov==4.1.0
httpx>=0.27.0
```

So running `pip install -r requirements.txt` should install everything needed.
