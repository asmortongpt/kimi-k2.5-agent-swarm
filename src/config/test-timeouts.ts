/**
 * Centralized Test Timeout Configuration
 *
 * This module provides environment-configurable timeout values for all tests.
 * Timeouts can be adjusted based on CI/CD environment performance characteristics.
 *
 * Environment Variables:
 * - TEST_TIMEOUT_NAVIGATION: Time to wait for page navigation (default: 5000ms)
 * - TEST_TIMEOUT_ANIMATION: Time to wait for animations to complete (default: 1500ms)
 * - TEST_TIMEOUT_STABILIZATION: Time to wait for UI to stabilize (default: 2000ms)
 * - TEST_TIMEOUT_API: Time to wait for API calls (default: 3000ms)
 * - TEST_TIMEOUT_LONG: Time to wait for long operations (default: 10000ms)
 * - TEST_TIMEOUT_SSO_LOGIN: Time to wait for manual SSO login (default: 300000ms / 5 min)
 */

/**
 * Parse timeout from environment variable with fallback
 */
function parseTimeout(envVar: string, defaultValue: number): number {
  const value = process.env[envVar];
  if (!value) return defaultValue;

  const parsed = parseInt(value, 10);
  if (isNaN(parsed) || parsed <= 0) {
    console.warn(`Invalid timeout value for ${envVar}: ${value}, using default: ${defaultValue}ms`);
    return defaultValue;
  }

  return parsed;
}

/**
 * Centralized timeout configuration object
 */
export const TIMEOUTS = {
  /**
   * Navigation timeout - time to wait for page navigation to complete
   * Use for: page.goto(), navigation events
   */
  navigation: parseTimeout('TEST_TIMEOUT_NAVIGATION', 5000),

  /**
   * Animation timeout - time to wait for CSS animations/transitions
   * Use for: UI transitions, modal animations, slide-in effects
   */
  animation: parseTimeout('TEST_TIMEOUT_ANIMATION', 1500),

  /**
   * Stabilization timeout - time to wait for UI to stabilize after interactions
   * Use for: After clicks, form submissions, state changes
   */
  stabilization: parseTimeout('TEST_TIMEOUT_STABILIZATION', 2000),

  /**
   * API call timeout - time to wait for API requests to complete
   * Use for: Waiting for API responses, data loading
   */
  apiCall: parseTimeout('TEST_TIMEOUT_API', 3000),

  /**
   * Long operation timeout - time to wait for complex operations
   * Use for: Large data processing, report generation, bulk operations
   */
  longOperation: parseTimeout('TEST_TIMEOUT_LONG', 10000),

  /**
   * SSO Login timeout - time to wait for manual SSO login completion
   * Use for: Interactive testing where human needs to complete SSO
   */
  ssoLogin: parseTimeout('TEST_TIMEOUT_SSO_LOGIN', 300000),
} as const;

/**
 * Playwright-specific timeout configuration
 * These can be used with test.setTimeout() or page.setDefaultTimeout()
 */
export const PLAYWRIGHT_TIMEOUTS = {
  /**
   * Default test timeout - maximum time for a single test
   */
  test: parseTimeout('TEST_TIMEOUT_TEST', 30000),

  /**
   * Navigation timeout for Playwright page operations
   */
  navigation: TIMEOUTS.navigation,

  /**
   * Action timeout for Playwright actions (click, fill, etc.)
   */
  action: parseTimeout('TEST_TIMEOUT_ACTION', 5000),
} as const;

/**
 * Get a timeout multiplier based on CI environment
 * CI environments often run slower than local development
 */
export function getTimeoutMultiplier(): number {
  if (process.env.CI === 'true') {
    return parseFloat(process.env.TEST_TIMEOUT_MULTIPLIER || '2');
  }
  return 1;
}

/**
 * Apply multiplier to a timeout value
 * Useful for CI environments that need longer timeouts
 */
export function applyMultiplier(timeout: number): number {
  return Math.round(timeout * getTimeoutMultiplier());
}

/**
 * Helper to get timeout with optional multiplier
 */
export function getTimeout(timeoutType: keyof typeof TIMEOUTS, useMultiplier = false): number {
  const timeout = TIMEOUTS[timeoutType];
  return useMultiplier ? applyMultiplier(timeout) : timeout;
}

// Log configuration on import (useful for debugging)
if (process.env.NODE_ENV !== 'production') {
  console.log('[Test Timeouts] Configuration loaded:', {
    ...TIMEOUTS,
    multiplier: getTimeoutMultiplier(),
    isCI: process.env.CI === 'true',
  });
}

export default TIMEOUTS;
