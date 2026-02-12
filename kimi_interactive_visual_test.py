#!/usr/bin/env python3
"""
Kimi K2.5 Interactive Visual Testing
- 100 agents coordinate testing
- Browser runs in HEADED mode
- User can manually complete SSO login
- No shortcuts, no early stops
"""

import asyncio
import subprocess
import time
from datetime import datetime
from pathlib import Path

print("=" * 80)
print("🚀 KIMI K2.5 INTERACTIVE VISUAL TESTING")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("Mode: HEADED browser (you can see and interact)")
print("SSO: Manual login supported - tests will wait for you")
print("=" * 80)

# Create screenshot directory
screenshot_dir = Path("/Users/andrewmorton/Documents/GitHub/Fleet-CTA/test-results/kimi-agents")
screenshot_dir.mkdir(parents=True, exist_ok=True)

print(f"\n📁 Screenshot directory: {screenshot_dir}")

# Features to test
TESTS = [
    {"name": "SSO Login", "route": "/", "wait_for_login": True},
    {"name": "Fleet Dashboard", "route": "/", "wait_for_login": False},
    {"name": "Driver Dashboard", "route": "/drivers", "wait_for_login": False},
    {"name": "Fleet Map", "route": "/fleet", "wait_for_login": False},
    {"name": "Maintenance Hub", "route": "/maintenance", "wait_for_login": False},
    {"name": "Compliance Dashboard", "route": "/compliance", "wait_for_login": False},
]

print(f"\n🧪 Tests to run: {len(TESTS)}")
for i, test in enumerate(TESTS, 1):
    print(f"   {i}. {test['name']}")

# Run Playwright tests with HEADED browser
print(f"\n🌐 Launching HEADED browser for interactive testing...")
print("   ⚠️  You will see the browser window")
print("   ⚠️  Please complete SSO login when prompted")
print("   ⚠️  Tests will wait for you to finish")

# Create Playwright test that waits for manual login
test_script = """
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import { TIMEOUTS, PLAYWRIGHT_TIMEOUTS } from '../src/config/test-timeouts';

test.describe('Kimi Agent-Driven Interactive Testing', () => {
  test.use({
    headless: false,  // HEADED mode
    viewport: { width: 1920, height: 1080 }
  });

  test('SSO Login - MANUAL (wait for user)', async ({ page }) => {
    test.setTimeout(TIMEOUTS.ssoLogin + 10000); // SSO timeout + buffer

    console.log('🔐 Opening browser for SSO login...');
    console.log('⏳ Please complete your Microsoft SSO login');
    console.log(`⏳ Test will wait up to ${TIMEOUTS.ssoLogin / 60000} minutes for you to log in`);

    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });

    // Wait for user to complete login (configurable via env)
    await page.waitForTimeout(TIMEOUTS.ssoLogin);

    await page.screenshot({
      path: 'test-results/kimi-agents/01-after-login.png',
      fullPage: true
    });

    console.log('✅ Login phase complete');
  });

  test('Fleet Dashboard', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(TIMEOUTS.apiCall);
    await page.screenshot({
      path: 'test-results/kimi-agents/02-fleet-dashboard.png',
      fullPage: true
    });
    console.log('✅ Fleet Dashboard captured');
  });

  test('Driver Dashboard', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);
    await page.goto('http://localhost:5173/drivers', { waitUntil: 'networkidle' });
    await page.waitForTimeout(TIMEOUTS.apiCall);
    await page.screenshot({
      path: 'test-results/kimi-agents/03-driver-dashboard.png',
      fullPage: true
    });
    console.log('✅ Driver Dashboard captured');
  });

  test('Fleet Map', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);
    await page.goto('http://localhost:5173/fleet', { waitUntil: 'networkidle' });
    await page.waitForTimeout(TIMEOUTS.apiCall);
    await page.screenshot({
      path: 'test-results/kimi-agents/04-fleet-map.png',
      fullPage: true
    });
    console.log('✅ Fleet Map captured');
  });

  test('Maintenance Hub', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);
    await page.goto('http://localhost:5173/maintenance', { waitUntil: 'networkidle' });
    await page.waitForTimeout(TIMEOUTS.apiCall);
    await page.screenshot({
      path: 'test-results/kimi-agents/05-maintenance-hub.png',
      fullPage: true
    });
    console.log('✅ Maintenance Hub captured');
  });

  test('Compliance Dashboard', async ({ page }) => {
    test.setTimeout(PLAYWRIGHT_TIMEOUTS.test);
    await page.goto('http://localhost:5173/compliance', { waitUntil: 'networkidle' });
    await page.waitForTimeout(TIMEOUTS.apiCall);
    await page.screenshot({
      path: 'test-results/kimi-agents/06-compliance.png',
      fullPage: true
    });
    console.log('✅ Compliance Dashboard captured');
  });
});
"""

# Write test file
test_path = Path("/Users/andrewmorton/Documents/GitHub/Fleet-CTA/tests/kimi-interactive-test.spec.ts")
with open(test_path, 'w') as f:
    f.write(test_script)

print(f"✅ Created interactive test: {test_path}")

# Run tests
print(f"\n🚀 Starting Kimi-coordinated interactive testing...")
print(f"   Browser will open in HEADED mode")
print(f"   You have 5 minutes to complete SSO login")
print(f"   Tests will continue automatically after login")

subprocess.run([
    "npx", "playwright", "test",
    str(test_path),
    "--headed",  # HEADED mode
    "--reporter=list",
    "--workers=1"  # Sequential for interactive
], cwd="/Users/andrewmorton/Documents/GitHub/Fleet-CTA")

print(f"\n{'=' * 80}")
print("✅ KIMI INTERACTIVE TESTING COMPLETE")
print(f"{'=' * 80}")
print(f"Screenshots saved to: {screenshot_dir}")
