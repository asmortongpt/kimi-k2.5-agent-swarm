# Parallel Screenshot Capture - Quick Start Guide

> **High Priority Issue #6 Resolution**: Parallel Screenshot Processing
>
> **Performance**: 60-70% faster than sequential processing
>
> **Status**: ✅ Production Ready

---

## What's New?

This system replaces slow sequential screenshot capture with **parallel batch processing**:

- **Before**: 9 screenshots × 4s = 36 seconds
- **After**: 9 screenshots in batches of 3 = ~12-15 seconds
- **Improvement**: **60-70% faster**

---

## Quick Start (3 Options)

### Option 1: JavaScript Standalone (Recommended)

```bash
# Run parallel screenshot capture
node capture-screenshots.js

# Output: test-results/screenshots/
```

**Features**:
- ✅ No dependencies beyond Playwright
- ✅ Works standalone or as module
- ✅ JSON output for automation
- ✅ Configurable via environment variables

### Option 2: Playwright TypeScript Tests

```bash
# Install dependencies (one-time)
npm install -D @playwright/test

# Run parallel tests
npx playwright test tests/parallel-visual.spec.ts --workers=3

# Output: test-results/parallel-screenshots/
```

**Features**:
- ✅ Full Playwright integration
- ✅ Multiple viewport support
- ✅ Automatic retries
- ✅ Built-in reporting

### Option 3: Python Orchestration

```bash
# Run orchestrated testing
./fleet_parallel_visual_test.py

# Or with Python
python3 fleet_parallel_visual_test.py

# Output: test-results/parallel-screenshots/
```

**Features**:
- ✅ Dependency checking
- ✅ Progress monitoring
- ✅ Comprehensive reports
- ✅ Integration with existing Python tests

---

## Performance Benchmark

Compare sequential vs. parallel performance:

```bash
# Run benchmark
node benchmark-screenshots.js

# Expected output:
# Sequential: ~24s
# Parallel:   ~8-10s
# Improvement: ~60-70% faster
```

---

## Configuration

### Environment Variables

```bash
# Customize behavior
export BASE_URL=http://localhost:5173
export SCREENSHOT_DIR=./my-screenshots
export VIEWPORT_WIDTH=1920
export VIEWPORT_HEIGHT=1080
export BATCH_SIZE=3  # Concurrent screenshots

# Run with custom config
node capture-screenshots.js
```

### Add Screenshots

Edit screenshot definitions in `capture-screenshots.js`:

```javascript
const SCREENSHOTS = [
  { name: 'my-page', url: '/my-page', description: 'My Custom Page' },
  // Add more here
];
```

---

## Files Created

| File | Purpose |
|------|---------|
| `capture-screenshots.js` | Standalone parallel capture script |
| `tests/parallel-visual.spec.ts` | Playwright TypeScript tests |
| `fleet_parallel_visual_test.py` | Python orchestration script |
| `benchmark-screenshots.js` | Performance benchmark tool |
| `PARALLEL_SCREENSHOT_SYSTEM.md` | Full documentation |

---

## Common Commands

```bash
# Basic screenshot capture
node capture-screenshots.js

# Benchmark performance
node benchmark-screenshots.js

# Run Playwright tests
npx playwright test tests/parallel-visual.spec.ts --workers=3

# Python orchestration
./fleet_parallel_visual_test.py

# Custom viewport
VIEWPORT_WIDTH=1366 VIEWPORT_HEIGHT=768 node capture-screenshots.js

# Debug mode
DEBUG=pw:api node capture-screenshots.js
```

---

## Troubleshooting

### Screenshots timeout?
```javascript
// Increase timeout in capture-screenshots.js
TIMEOUTS: {
  navigation: 60000,  // 60s instead of 30s
}
```

### Out of memory?
```bash
# Reduce batch size
BATCH_SIZE=1 node capture-screenshots.js

# Or increase Node memory
NODE_OPTIONS="--max-old-space-size=4096" node capture-screenshots.js
```

### Flaky tests?
```bash
# Enable retries in Playwright
npx playwright test --retries=2
```

---

## Integration Examples

### GitHub Actions

```yaml
- name: Visual Tests
  run: node capture-screenshots.js

- name: Upload Screenshots
  uses: actions/upload-artifact@v3
  with:
    name: screenshots
    path: test-results/screenshots/
```

### npm scripts

```json
{
  "scripts": {
    "test:visual": "node capture-screenshots.js",
    "test:visual:benchmark": "node benchmark-screenshots.js",
    "test:visual:playwright": "playwright test tests/parallel-visual.spec.ts"
  }
}
```

### Docker

```dockerfile
FROM mcr.microsoft.com/playwright:v1.40.0-focal

WORKDIR /app
COPY . .

RUN npm install

CMD ["node", "capture-screenshots.js"]
```

---

## Performance Tips

1. **Batch Size**: Start with 3, adjust based on your machine
   - Low resources: `BATCH_SIZE=1`
   - High resources: `BATCH_SIZE=5`

2. **Network Idle**: Good for dynamic pages
   ```javascript
   waitUntil: 'networkidle'
   ```

3. **Disable Animations**: Faster and more consistent
   ```javascript
   animations: 'disabled'
   ```

4. **Resource Limits**: Prevent browser bloat
   ```javascript
   serviceWorkers: 'block',
   permissions: []
   ```

---

## Next Steps

1. ✅ Run `node benchmark-screenshots.js` to see performance gains
2. ✅ Customize screenshots in `capture-screenshots.js`
3. ✅ Integrate into CI/CD pipeline
4. ✅ Add visual regression testing (compare against baseline)
5. ✅ Read full docs: `PARALLEL_SCREENSHOT_SYSTEM.md`

---

## Support

- **Full Documentation**: `PARALLEL_SCREENSHOT_SYSTEM.md`
- **Playwright Docs**: https://playwright.dev/
- **Issue Tracker**: Report issues via project repository

---

**Version**: 1.0.0
**Last Updated**: 2026-02-08
**High Priority Issue #6**: ✅ Resolved
