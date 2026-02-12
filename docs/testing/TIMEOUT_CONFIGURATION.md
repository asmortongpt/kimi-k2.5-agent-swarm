# Test Timeout Configuration Guide

## Overview

This document explains the centralized timeout configuration system for all tests in the CTAFleet project. The system provides:

1. **Semantic timeout names** - Use meaningful names like `animation`, `stabilization`, `apiCall` instead of hardcoded millisecond values
2. **Environment configurability** - Adjust timeouts via environment variables without code changes
3. **CI/CD optimization** - Automatic timeout multipliers for slower CI environments
4. **Consistency** - Single source of truth for all timeout values across the test suite

## Configuration File

All timeout configuration is managed in:

```
/src/config/test-timeouts.ts
```

This TypeScript module exports timeout constants that should be used in all test files.

## Available Timeouts

### Standard Timeouts

| Timeout Name | Default | Environment Variable | Use Case |
|--------------|---------|---------------------|----------|
| `navigation` | 5000ms | `TEST_TIMEOUT_NAVIGATION` | Page navigation, route changes |
| `animation` | 1500ms | `TEST_TIMEOUT_ANIMATION` | CSS animations, transitions, modal open/close |
| `stabilization` | 2000ms | `TEST_TIMEOUT_STABILIZATION` | UI stabilization after clicks, form submissions |
| `apiCall` | 3000ms | `TEST_TIMEOUT_API` | API requests, data loading |
| `longOperation` | 10000ms | `TEST_TIMEOUT_LONG` | Complex operations, report generation, bulk updates |
| `ssoLogin` | 300000ms | `TEST_TIMEOUT_SSO_LOGIN` | Manual SSO login (5 minutes) |

### Playwright-Specific Timeouts

| Timeout Name | Default | Environment Variable | Use Case |
|--------------|---------|---------------------|----------|
| `test` | 30000ms | `TEST_TIMEOUT_TEST` | Maximum time for a single test (`test.setTimeout()`) |
| `action` | 5000ms | `TEST_TIMEOUT_ACTION` | Playwright actions (click, fill, etc.) |

## Usage Examples

### Basic Usage in TypeScript/JavaScript Tests

```typescript
import { TIMEOUTS, PLAYWRIGHT_TIMEOUTS } from '@/config/test-timeouts';

test.describe('Fleet Dashboard Tests', () => {
  test('should load vehicles', async ({ page }) => {
    // Set test timeout
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

    // Navigate with timeout
    await page.goto('http://localhost:5173/fleet');

    // Wait for API data to load
    await page.waitForTimeout(TIMEOUTS.apiCall);

    // Wait for animations to complete
    await page.waitForTimeout(TIMEOUTS.animation);

    // Take screenshot
    await page.screenshot({ path: 'fleet-dashboard.png' });
  });

  test('should open vehicle detail modal', async ({ page }) => {
    await page.click('[data-testid="vehicle-card"]');

    // Wait for modal animation
    await page.waitForTimeout(TIMEOUTS.animation);

    // Wait for UI to stabilize
    await page.waitForTimeout(TIMEOUTS.stabilization);
  });
});
```

### Usage in Python Test Generators

When generating Playwright test scripts from Python:

```python
def create_playwright_test():
    test_script = '''
import { TIMEOUTS, PLAYWRIGHT_TIMEOUTS } from '../src/config/test-timeouts';

test('Interactive SSO Login', async ({ page }) => {
  test.setTimeout(TIMEOUTS.ssoLogin + 10000);

  await page.goto('http://localhost:5173');
  await page.waitForTimeout(TIMEOUTS.ssoLogin);

  await page.screenshot({ path: 'after-login.png' });
});
'''
    return test_script
```

### Using Timeout Multipliers (CI Environments)

The timeout system automatically detects CI environments and applies a multiplier:

```typescript
import { getTimeout, applyMultiplier } from '@/config/test-timeouts';

test('Long operation in CI', async ({ page }) => {
  // This will be 10000ms locally, 20000ms in CI (with multiplier=2)
  const timeout = getTimeout('longOperation', true);

  await page.waitForTimeout(timeout);
});
```

## Environment Configuration

### Local Development (.env)

Create a `.env` file in the project root:

```bash
# Standard timeouts
TEST_TIMEOUT_NAVIGATION=5000
TEST_TIMEOUT_ANIMATION=1500
TEST_TIMEOUT_STABILIZATION=2000
TEST_TIMEOUT_API=3000
TEST_TIMEOUT_LONG=10000
TEST_TIMEOUT_SSO_LOGIN=300000

# Playwright timeouts
TEST_TIMEOUT_TEST=30000
TEST_TIMEOUT_ACTION=5000

# CI multiplier (default: 2)
TEST_TIMEOUT_MULTIPLIER=2
```

### CI/CD Configuration

For GitHub Actions:

```yaml
env:
  CI: 'true'
  TEST_TIMEOUT_MULTIPLIER: '2.5'
  TEST_TIMEOUT_LONG: '15000'
  TEST_TIMEOUT_API: '5000'
```

For Azure Pipelines:

```yaml
variables:
  CI: 'true'
  TEST_TIMEOUT_MULTIPLIER: '2'
  TEST_TIMEOUT_NAVIGATION: '8000'
  TEST_TIMEOUT_API: '5000'
```

### Docker Test Environments

In `docker-compose.test.yml`:

```yaml
services:
  playwright-tests:
    environment:
      - CI=true
      - TEST_TIMEOUT_MULTIPLIER=3
      - TEST_TIMEOUT_API=6000
      - TEST_TIMEOUT_LONG=20000
```

## Migration Guide

### Before (Hardcoded Timeouts)

```typescript
// ❌ BAD - Hardcoded, not configurable
test('Vehicle detail page', async ({ page }) => {
  await page.goto('http://localhost:5173/fleet');
  await page.click('.vehicle-card');
  await page.waitForTimeout(2000);  // What does 2000ms represent?
  await page.screenshot({ path: 'detail.png' });
});
```

### After (Semantic Timeouts)

```typescript
// ✅ GOOD - Semantic, configurable
import { TIMEOUTS } from '@/config/test-timeouts';

test('Vehicle detail page', async ({ page }) => {
  test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

  await page.goto('http://localhost:5173/fleet');
  await page.click('.vehicle-card');

  // Clear intent: waiting for UI to stabilize
  await page.waitForTimeout(TIMEOUTS.stabilization);

  await page.screenshot({ path: 'detail.png' });
});
```

## Best Practices

### 1. Always Use Semantic Names

```typescript
// ✅ GOOD
await page.waitForTimeout(TIMEOUTS.animation);

// ❌ BAD
await page.waitForTimeout(1500);
```

### 2. Set Test Timeouts Explicitly

```typescript
// ✅ GOOD
test('Complex operation', async ({ page }) => {
  test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);
  // ... test code
});

// ❌ BAD - Relies on default timeout
test('Complex operation', async ({ page }) => {
  // ... test code might timeout unexpectedly
});
```

### 3. Use Multipliers for CI

```typescript
// ✅ GOOD - Accounts for slower CI
const timeout = getTimeout('apiCall', true);

// ❌ BAD - Same timeout everywhere
const timeout = TIMEOUTS.apiCall;
```

### 4. Prefer Specific Waits Over Generic Timeouts

```typescript
// ✅ BEST - Wait for specific element
await page.waitForSelector('.modal', { timeout: TIMEOUTS.animation });

// ⚠️ OK - When element selectors are unreliable
await page.waitForTimeout(TIMEOUTS.animation);

// ❌ BAD - Hardcoded timeout
await page.waitForTimeout(2000);
```

## Troubleshooting

### Tests Timing Out in CI

Increase the CI multiplier or specific timeouts:

```bash
TEST_TIMEOUT_MULTIPLIER=3
TEST_TIMEOUT_API=6000
```

### Tests Too Slow Locally

Decrease timeouts for faster local development:

```bash
TEST_TIMEOUT_ANIMATION=800
TEST_TIMEOUT_STABILIZATION=1000
TEST_TIMEOUT_API=2000
```

### Flaky Tests

If tests pass sometimes but fail other times:

1. Check if you're using `waitForTimeout()` instead of `waitForSelector()`
2. Increase the specific timeout that's failing
3. Add a timeout multiplier for that environment

```typescript
// Instead of:
await page.waitForTimeout(TIMEOUTS.stabilization);

// Try:
await page.waitForSelector('[data-loaded="true"]', {
  timeout: TIMEOUTS.stabilization
});
```

## Related Files

- `/src/config/test-timeouts.ts` - Main configuration file
- `/.env.example` - Environment variable template
- `/fleet_comprehensive_real_testing.py` - Python test generator (uses timeouts)
- `/kimi_interactive_visual_test.py` - Python test generator (uses timeouts)

## Additional Resources

- [Playwright Timeouts Documentation](https://playwright.dev/docs/test-timeouts)
- [Best Practices for Test Timeouts](https://playwright.dev/docs/test-timeouts#best-practices)
- CTAFleet Testing Standards (internal documentation)
