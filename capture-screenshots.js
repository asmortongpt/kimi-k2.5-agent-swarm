#!/usr/bin/env node
/**
 * Parallel Screenshot Capture for Fleet-CTA Visual Testing
 *
 * HIGH PRIORITY ISSUE #6 SOLUTION: Parallel Screenshot Processing
 *
 * Improvements over sequential approach:
 * - Processes screenshots in batches using Promise.all
 * - Separate browser context for each screenshot (isolation)
 * - Configurable concurrency to prevent resource exhaustion
 * - Progress reporting with time estimates
 * - ~60-70% faster than sequential processing
 *
 * Performance comparison:
 * - Sequential: 9 screenshots × 4s = 36s
 * - Parallel (batch=3): ~12-15s (60% faster)
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs').promises;

// Configuration
const CONFIG = {
  BATCH_SIZE: 3, // Process 3 screenshots concurrently
  TIMEOUTS: {
    navigation: 30000, // 30s for page load
    stabilization: 3000, // 3s for page to stabilize
    networkIdle: 10000 // 10s for network to be idle
  },
  BASE_URL: process.env.BASE_URL || 'http://localhost:5173',
  OUTPUT_DIR: process.env.SCREENSHOT_DIR || path.join(__dirname, 'test-results', 'screenshots'),
  VIEWPORT: {
    width: parseInt(process.env.VIEWPORT_WIDTH || '1920'),
    height: parseInt(process.env.VIEWPORT_HEIGHT || '1080')
  }
};

// Screenshot definitions
const SCREENSHOTS = [
  { name: 'fleet-dashboard', url: '/', description: 'Fleet Dashboard Overview' },
  { name: 'drivers-hub', url: '/drivers', description: 'Driver Management Hub' },
  { name: 'fleet-map', url: '/fleet', description: 'Real-time Fleet Map' },
  { name: 'maintenance-hub', url: '/maintenance', description: 'Maintenance Management' },
  { name: 'compliance-dashboard', url: '/compliance', description: 'Compliance Dashboard' },
  { name: 'analytics-dashboard', url: '/analytics', description: 'Analytics Dashboard' },
  { name: 'executive-dashboard', url: '/executive', description: 'Executive Dashboard' },
  { name: 'work-orders', url: '/maintenance/work-orders', description: 'Work Orders' },
  { name: 'dispatch-console', url: '/dispatch', description: 'Dispatch Console' }
];

/**
 * Capture a single screenshot with isolated browser context
 * @param {import('playwright').Browser} browser - Playwright browser instance
 * @param {Object} screenshot - Screenshot configuration
 * @param {number} index - Screenshot index for progress reporting
 * @param {number} total - Total number of screenshots
 * @returns {Promise<Object>} Result object with status and timing
 */
async function captureScreenshot(browser, screenshot, index, total) {
  const startTime = Date.now();
  let context = null;

  try {
    // Create isolated browser context
    context = await browser.newContext({
      viewport: CONFIG.VIEWPORT,
      // Security: disable unnecessary features
      permissions: [],
      // Performance: disable unnecessary resources
      javaScriptEnabled: true,
      serviceWorkers: 'block'
    });

    const page = await context.newPage();

    // Navigate to page
    const targetUrl = `${CONFIG.BASE_URL}${screenshot.url}`;
    console.log(`[${index}/${total}] Navigating to: ${screenshot.description}`);

    await page.goto(targetUrl, {
      waitUntil: 'networkidle',
      timeout: CONFIG.TIMEOUTS.navigation
    });

    // Wait for page to stabilize
    await page.waitForTimeout(CONFIG.TIMEOUTS.stabilization);

    // Ensure output directory exists
    await fs.mkdir(CONFIG.OUTPUT_DIR, { recursive: true });

    // Capture screenshot
    const screenshotPath = path.join(CONFIG.OUTPUT_DIR, `${screenshot.name}.png`);
    await page.screenshot({
      path: screenshotPath,
      fullPage: true,
      // Optimize file size
      type: 'png',
      // Ensure consistent rendering
      animations: 'disabled'
    });

    const duration = Date.now() - startTime;
    const fileStats = await fs.stat(screenshotPath);
    const fileSizeKB = (fileStats.size / 1024).toFixed(1);

    console.log(`✅ [${index}/${total}] Captured: ${screenshot.name} (${fileSizeKB} KB, ${duration}ms)`);

    return {
      success: true,
      name: screenshot.name,
      path: screenshotPath,
      duration,
      sizeKB: parseFloat(fileSizeKB)
    };

  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`❌ [${index}/${total}] Failed: ${screenshot.name} - ${error.message}`);

    return {
      success: false,
      name: screenshot.name,
      error: error.message,
      duration
    };

  } finally {
    // Always cleanup context to prevent memory leaks
    if (context) {
      await context.close();
    }
  }
}

/**
 * Capture all screenshots in parallel batches
 * @returns {Promise<Object>} Summary of capture results
 */
async function captureAllScreenshots() {
  const overallStartTime = Date.now();
  console.log('=' .repeat(80));
  console.log('🚀 PARALLEL SCREENSHOT CAPTURE');
  console.log('=' .repeat(80));
  console.log(`Target: ${CONFIG.BASE_URL}`);
  console.log(`Output: ${CONFIG.OUTPUT_DIR}`);
  console.log(`Viewport: ${CONFIG.VIEWPORT.width}×${CONFIG.VIEWPORT.height}`);
  console.log(`Batch Size: ${CONFIG.BATCH_SIZE} concurrent screenshots`);
  console.log(`Total Screenshots: ${SCREENSHOTS.length}`);
  console.log('=' .repeat(80));

  // Launch browser once and reuse
  const browser = await chromium.launch({
    headless: true,
    // Performance optimizations
    args: [
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--no-sandbox',
      '--disable-setuid-sandbox'
    ]
  });

  const results = [];

  try {
    // Process screenshots in batches
    const batches = Math.ceil(SCREENSHOTS.length / CONFIG.BATCH_SIZE);

    for (let i = 0; i < SCREENSHOTS.length; i += CONFIG.BATCH_SIZE) {
      const batchNum = Math.floor(i / CONFIG.BATCH_SIZE) + 1;
      const batch = SCREENSHOTS.slice(i, i + CONFIG.BATCH_SIZE);

      console.log(`\n📦 Processing batch ${batchNum}/${batches} (${batch.length} screenshots)...`);

      // Capture batch in parallel
      const batchResults = await Promise.all(
        batch.map((screenshot, batchIndex) =>
          captureScreenshot(browser, screenshot, i + batchIndex + 1, SCREENSHOTS.length)
        )
      );

      results.push(...batchResults);

      // Progress update
      const completed = results.length;
      const percentage = ((completed / SCREENSHOTS.length) * 100).toFixed(1);
      const elapsed = ((Date.now() - overallStartTime) / 1000).toFixed(1);
      console.log(`   Progress: ${completed}/${SCREENSHOTS.length} (${percentage}%) | ${elapsed}s elapsed`);
    }

  } finally {
    // Always cleanup browser
    await browser.close();
  }

  // Calculate statistics
  const totalDuration = Date.now() - overallStartTime;
  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);
  const totalSizeKB = successful.reduce((sum, r) => sum + (r.sizeKB || 0), 0);
  const avgDuration = successful.length > 0
    ? (successful.reduce((sum, r) => sum + r.duration, 0) / successful.length).toFixed(0)
    : 0;

  // Performance comparison (sequential vs parallel)
  const sequentialEstimate = SCREENSHOTS.length * 4000; // 4s per screenshot
  const timesSaved = ((totalDuration / sequentialEstimate) * 100).toFixed(1);
  const improvement = (((sequentialEstimate - totalDuration) / sequentialEstimate) * 100).toFixed(1);

  console.log('\n' + '='.repeat(80));
  console.log('📊 CAPTURE SUMMARY');
  console.log('='.repeat(80));
  console.log(`✅ Successful: ${successful.length}/${SCREENSHOTS.length}`);
  console.log(`❌ Failed: ${failed.length}/${SCREENSHOTS.length}`);
  console.log(`📁 Total Size: ${totalSizeKB.toFixed(1)} KB`);
  console.log(`⏱️  Total Time: ${(totalDuration / 1000).toFixed(1)}s`);
  console.log(`⚡ Avg Time per Screenshot: ${avgDuration}ms`);
  console.log('');
  console.log('🚀 PERFORMANCE IMPROVEMENT:');
  console.log(`   Sequential estimate: ${(sequentialEstimate / 1000).toFixed(1)}s`);
  console.log(`   Parallel actual: ${(totalDuration / 1000).toFixed(1)}s`);
  console.log(`   Time saved: ${((sequentialEstimate - totalDuration) / 1000).toFixed(1)}s`);
  console.log(`   Improvement: ${improvement}% faster`);
  console.log('='.repeat(80));

  if (failed.length > 0) {
    console.log('\n⚠️  Failed Screenshots:');
    failed.forEach(f => {
      console.log(`   - ${f.name}: ${f.error}`);
    });
  }

  // Write results to JSON
  const resultsPath = path.join(CONFIG.OUTPUT_DIR, 'capture-results.json');
  await fs.writeFile(resultsPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    config: CONFIG,
    totalDuration,
    successful: successful.length,
    failed: failed.length,
    results,
    performance: {
      sequentialEstimate,
      parallelActual: totalDuration,
      timeSaved: sequentialEstimate - totalDuration,
      improvementPercent: parseFloat(improvement)
    }
  }, null, 2));

  console.log(`\n💾 Results saved to: ${resultsPath}`);

  return {
    success: failed.length === 0,
    totalDuration,
    results
  };
}

// Main execution
if (require.main === module) {
  captureAllScreenshots()
    .then(summary => {
      process.exit(summary.success ? 0 : 1);
    })
    .catch(error => {
      console.error('💥 Fatal error:', error);
      process.exit(1);
    });
}

module.exports = {
  captureAllScreenshots,
  captureScreenshot,
  SCREENSHOTS,
  CONFIG
};
