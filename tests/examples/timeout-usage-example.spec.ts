/**
 * Example Test File Demonstrating Timeout Configuration Usage
 *
 * This file shows best practices for using the centralized timeout system.
 * Copy these patterns to your own test files.
 */

import { test, expect } from '@playwright/test';
import { TIMEOUTS, PLAYWRIGHT_TIMEOUTS, getTimeout, applyMultiplier } from '../../src/config/test-timeouts';

test.describe('Timeout Configuration Examples', () => {

  /**
   * Example 1: Basic test with explicit timeout
   */
  test('Example 1: Fleet Dashboard loads with proper timeouts', async ({ page }) => {
    // Set test timeout to ensure enough time for all operations
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

    // Navigate to page
    await page.goto('http://localhost:5173/fleet', {
      timeout: TIMEOUTS.navigation,
    });

    // Wait for API data to load
    await page.waitForSelector('[data-loaded="true"]', {
      timeout: TIMEOUTS.apiCall,
    });

    // Wait for animations to complete
    await page.waitForTimeout(TIMEOUTS.animation);

    // Verify content loaded
    const vehicleCount = await page.locator('[data-testid="vehicle-card"]').count();
    expect(vehicleCount).toBeGreaterThan(0);
  });

  /**
   * Example 2: Modal interactions with stabilization timeout
   */
  test('Example 2: Vehicle detail modal with stabilization', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

    await page.goto('http://localhost:5173/fleet');

    // Click to open modal
    await page.click('[data-testid="vehicle-card"]:first-child', {
      timeout: PLAYWRIGHT_TIMEOUTS.action,
    });

    // Wait for modal animation
    await page.waitForSelector('[role="dialog"]', {
      timeout: TIMEOUTS.animation,
    });

    // Wait for UI to stabilize after animation
    await page.waitForTimeout(TIMEOUTS.stabilization);

    // Take screenshot
    await page.screenshot({
      path: 'test-results/vehicle-detail-modal.png',
      fullPage: true,
    });
  });

  /**
   * Example 3: Long operation with custom timeout
   */
  test('Example 3: Report generation with long timeout', async ({ page }) => {
    // Extend test timeout for long operation
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test * 2);

    await page.goto('http://localhost:5173/reports');

    // Click generate report button
    await page.click('[data-testid="generate-report"]');

    // Wait for long operation to complete
    await page.waitForSelector('[data-testid="report-ready"]', {
      timeout: TIMEOUTS.longOperation,
    });

    // Verify report was generated
    const reportTitle = await page.locator('[data-testid="report-title"]').textContent();
    expect(reportTitle).toBeTruthy();
  });

  /**
   * Example 4: Using timeout multiplier for CI environments
   */
  test('Example 4: CI-aware timeout', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

    // This will automatically use multiplied timeout in CI
    const apiTimeout = getTimeout('apiCall', true);

    await page.goto('http://localhost:5173/fleet');
    await page.waitForSelector('[data-loaded="true"]', {
      timeout: apiTimeout,
    });

    console.log(`Using API timeout: ${apiTimeout}ms (CI multiplier: ${process.env.CI === 'true' ? 'active' : 'inactive'})`);
  });

  /**
   * Example 5: Multiple API calls with sequential loading
   */
  test('Example 5: Sequential API loading', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

    await page.goto('http://localhost:5173/dashboard');

    // Wait for initial data load
    await page.waitForSelector('[data-vehicles-loaded="true"]', {
      timeout: TIMEOUTS.apiCall,
    });

    // Wait for drivers data
    await page.waitForSelector('[data-drivers-loaded="true"]', {
      timeout: TIMEOUTS.apiCall,
    });

    // Wait for analytics data (may take longer)
    await page.waitForSelector('[data-analytics-loaded="true"]', {
      timeout: TIMEOUTS.longOperation,
    });

    // Verify all data is present
    const vehicleCount = await page.locator('[data-testid="vehicle-count"]').textContent();
    const driverCount = await page.locator('[data-testid="driver-count"]').textContent();
    expect(vehicleCount).toBeTruthy();
    expect(driverCount).toBeTruthy();
  });

  /**
   * Example 6: Form submission with validation
   */
  test('Example 6: Form submission with proper waits', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

    await page.goto('http://localhost:5173/drivers/new');

    // Fill form
    await page.fill('[name="firstName"]', 'John', {
      timeout: PLAYWRIGHT_TIMEOUTS.action,
    });
    await page.fill('[name="lastName"]', 'Doe', {
      timeout: PLAYWRIGHT_TIMEOUTS.action,
    });

    // Submit
    await page.click('[type="submit"]');

    // Wait for submission animation
    await page.waitForTimeout(TIMEOUTS.animation);

    // Wait for success message
    await page.waitForSelector('[data-testid="success-message"]', {
      timeout: TIMEOUTS.apiCall,
    });

    // Wait for UI to stabilize before screenshot
    await page.waitForTimeout(TIMEOUTS.stabilization);

    await page.screenshot({
      path: 'test-results/form-submitted.png',
    });
  });

  /**
   * Example 7: Interactive SSO login (for manual testing)
   */
  test('Example 7: Interactive SSO login', async ({ page }) => {
    // Set very long timeout for manual SSO completion
    test.setTimeout(TIMEOUTS.ssoLogin + 10000);

    console.log('🔐 Opening browser for SSO login...');
    console.log(`⏳ You have ${TIMEOUTS.ssoLogin / 60000} minutes to complete login`);

    await page.goto('http://localhost:5173');

    // Wait for user to complete SSO
    await page.waitForTimeout(TIMEOUTS.ssoLogin);

    // Verify login successful
    const userName = await page.locator('[data-testid="user-name"]').textContent();
    expect(userName).toBeTruthy();
  });

  /**
   * Example 8: Performance testing with timing measurements
   */
  test('Example 8: Performance measurement', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

    const startTime = Date.now();

    await page.goto('http://localhost:5173/fleet', {
      waitUntil: 'networkidle',
    });

    const loadTime = Date.now() - startTime;

    console.log(`Page load time: ${loadTime}ms`);
    console.log(`Navigation timeout: ${TIMEOUTS.navigation}ms`);

    // Verify performance is acceptable
    expect(loadTime).toBeLessThan(TIMEOUTS.navigation);
  });
});

/**
 * Example Test Suite with Custom Configuration
 */
test.describe('Custom Timeout Configuration', () => {

  // Set default timeout for all tests in this suite
  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(PLAYWRIGHT_TIMEOUTS.action);
  });

  test('Uses suite-level timeout config', async ({ page }) => {
    // All page actions will use PLAYWRIGHT_TIMEOUTS.action by default
    await page.goto('http://localhost:5173');
    await page.click('[data-testid="menu-button"]');
    await page.waitForSelector('[role="menu"]');
  });
});

/**
 * Example: Anti-patterns to AVOID
 */
test.describe('Anti-patterns (DO NOT USE)', () => {

  test.skip('❌ BAD: Hardcoded timeout', async ({ page }) => {
    await page.goto('http://localhost:5173');
    await page.waitForTimeout(2000); // ❌ What does 2000 mean? Not configurable!
  });

  test.skip('❌ BAD: No test timeout', async ({ page }) => {
    // ❌ Missing test.setTimeout() - may timeout unexpectedly
    await page.goto('http://localhost:5173');
    // ... complex operations
  });

  test.skip('❌ BAD: Arbitrary timeout value', async ({ page }) => {
    await page.goto('http://localhost:5173');
    await page.waitForTimeout(1500); // ❌ Why 1500? Should be semantic
  });
});

/**
 * Example: Best Practices ✅
 */
test.describe('Best Practices', () => {

  test('✅ GOOD: Semantic timeouts', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

    await page.goto('http://localhost:5173');

    // Clear intent: waiting for animation to complete
    await page.waitForTimeout(TIMEOUTS.animation);

    // Clear intent: waiting for API response
    await page.waitForSelector('[data-loaded="true"]', {
      timeout: TIMEOUTS.apiCall,
    });
  });

  test('✅ GOOD: Prefer waitForSelector over waitForTimeout', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

    await page.goto('http://localhost:5173');

    // ✅ Better: Wait for specific element
    await page.waitForSelector('.modal', {
      timeout: TIMEOUTS.animation,
    });

    // ⚠️ OK when element selectors are unreliable
    await page.waitForTimeout(TIMEOUTS.stabilization);
  });

  test('✅ GOOD: CI-aware timeouts', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);

    // Automatically adjusts for CI environment
    const timeout = getTimeout('apiCall', true);

    await page.goto('http://localhost:5173');
    await page.waitForSelector('[data-loaded="true"]', { timeout });
  });
});
