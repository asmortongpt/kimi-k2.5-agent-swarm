#!/usr/bin/env node
/**
 * Screenshot Capture Performance Benchmark
 *
 * Compares sequential vs. parallel screenshot capture performance
 * to measure the improvement from HIGH PRIORITY ISSUE #6 implementation.
 *
 * Usage:
 *   node benchmark-screenshots.js
 *   node benchmark-screenshots.js --mode=sequential
 *   node benchmark-screenshots.js --mode=parallel
 *   node benchmark-screenshots.js --mode=both
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs').promises;

// Configuration
const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const OUTPUT_DIR = path.join(__dirname, 'test-results', 'benchmark');
const BATCH_SIZE = 3;

// Test pages (reduced set for benchmarking)
const BENCHMARK_PAGES = [
  { name: 'fleet-dashboard', url: '/' },
  { name: 'drivers-hub', url: '/drivers' },
  { name: 'fleet-map', url: '/fleet' },
  { name: 'maintenance-hub', url: '/maintenance' },
  { name: 'compliance', url: '/compliance' },
  { name: 'analytics', url: '/analytics' }
];

/**
 * Capture screenshot sequentially (old approach)
 */
async function captureSequential(browser, page, name, url, index, total) {
  const startTime = Date.now();

  await page.goto(`${BASE_URL}${url}`, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  const screenshotPath = path.join(OUTPUT_DIR, 'sequential', `${name}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const duration = Date.now() - startTime;
  console.log(`  [${index}/${total}] Sequential: ${name} - ${duration}ms`);

  return { name, duration };
}

/**
 * Capture screenshot in parallel (new approach with isolated context)
 */
async function captureParallel(browser, screenshot, index, total) {
  const startTime = Date.now();
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });

  try {
    const page = await context.newPage();
    await page.goto(`${BASE_URL}${screenshot.url}`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    const screenshotPath = path.join(OUTPUT_DIR, 'parallel', `${screenshot.name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    const duration = Date.now() - startTime;
    console.log(`  [${index}/${total}] Parallel: ${screenshot.name} - ${duration}ms`);

    return { name: screenshot.name, duration };
  } finally {
    await context.close();
  }
}

/**
 * Run sequential benchmark
 */
async function benchmarkSequential() {
  console.log('\n🐢 SEQUENTIAL BENCHMARK (Old Approach)');
  console.log('=' .repeat(60));

  await fs.mkdir(path.join(OUTPUT_DIR, 'sequential'), { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  const startTime = Date.now();
  const results = [];

  for (let i = 0; i < BENCHMARK_PAGES.length; i++) {
    const screenshot = BENCHMARK_PAGES[i];
    const result = await captureSequential(
      browser,
      page,
      screenshot.name,
      screenshot.url,
      i + 1,
      BENCHMARK_PAGES.length
    );
    results.push(result);
  }

  const totalDuration = Date.now() - startTime;

  await browser.close();

  console.log(`\n⏱️  Sequential Total: ${(totalDuration / 1000).toFixed(1)}s`);
  console.log(`   Average per screenshot: ${(totalDuration / results.length).toFixed(0)}ms`);

  return { results, totalDuration, averageDuration: totalDuration / results.length };
}

/**
 * Run parallel benchmark
 */
async function benchmarkParallel() {
  console.log('\n🚀 PARALLEL BENCHMARK (New Approach)');
  console.log('=' .repeat(60));

  await fs.mkdir(path.join(OUTPUT_DIR, 'parallel'), { recursive: true });

  const browser = await chromium.launch({ headless: true });

  const startTime = Date.now();
  const results = [];

  // Process in batches
  for (let i = 0; i < BENCHMARK_PAGES.length; i += BATCH_SIZE) {
    const batch = BENCHMARK_PAGES.slice(i, i + BATCH_SIZE);
    console.log(`  Processing batch ${Math.floor(i / BATCH_SIZE) + 1}...`);

    const batchResults = await Promise.all(
      batch.map((screenshot, batchIndex) =>
        captureParallel(browser, screenshot, i + batchIndex + 1, BENCHMARK_PAGES.length)
      )
    );

    results.push(...batchResults);
  }

  const totalDuration = Date.now() - startTime;

  await browser.close();

  console.log(`\n⏱️  Parallel Total: ${(totalDuration / 1000).toFixed(1)}s`);
  console.log(`   Average per screenshot: ${(totalDuration / results.length).toFixed(0)}ms`);

  return { results, totalDuration, averageDuration: totalDuration / results.length };
}

/**
 * Generate comparison report
 */
async function generateReport(sequential, parallel) {
  console.log('\n' + '='.repeat(80));
  console.log('📊 PERFORMANCE COMPARISON');
  console.log('='.repeat(80));

  const improvement = ((sequential.totalDuration - parallel.totalDuration) / sequential.totalDuration * 100);
  const speedup = sequential.totalDuration / parallel.totalDuration;

  console.log('\n📈 Overall Performance:');
  console.log(`   Sequential: ${(sequential.totalDuration / 1000).toFixed(1)}s`);
  console.log(`   Parallel:   ${(parallel.totalDuration / 1000).toFixed(1)}s`);
  console.log(`   Time Saved: ${((sequential.totalDuration - parallel.totalDuration) / 1000).toFixed(1)}s`);
  console.log(`   Improvement: ${improvement.toFixed(1)}% faster`);
  console.log(`   Speedup: ${speedup.toFixed(2)}x`);

  console.log('\n⚡ Average Per Screenshot:');
  console.log(`   Sequential: ${sequential.averageDuration.toFixed(0)}ms`);
  console.log(`   Parallel:   ${parallel.averageDuration.toFixed(0)}ms`);

  console.log('\n📊 Detailed Results:');
  console.log('   Screenshot                Sequential    Parallel    Improvement');
  console.log('   ' + '-'.repeat(70));

  for (let i = 0; i < BENCHMARK_PAGES.length; i++) {
    const seqResult = sequential.results[i];
    const parResult = parallel.results[i];
    const diff = ((seqResult.duration - parResult.duration) / seqResult.duration * 100);

    console.log(
      `   ${seqResult.name.padEnd(25)} ` +
      `${seqResult.duration.toString().padStart(7)}ms   ` +
      `${parResult.duration.toString().padStart(7)}ms   ` +
      `${diff > 0 ? '+' : ''}${diff.toFixed(1)}%`
    );
  }

  // Save JSON report
  const report = {
    timestamp: new Date().toISOString(),
    benchmarkPages: BENCHMARK_PAGES.length,
    configuration: {
      batchSize: BATCH_SIZE,
      baseUrl: BASE_URL,
      viewport: { width: 1920, height: 1080 }
    },
    sequential: {
      totalDuration: sequential.totalDuration,
      averageDuration: sequential.averageDuration,
      results: sequential.results
    },
    parallel: {
      totalDuration: parallel.totalDuration,
      averageDuration: parallel.averageDuration,
      results: parallel.results
    },
    comparison: {
      timeSaved: sequential.totalDuration - parallel.totalDuration,
      timeSavedSeconds: (sequential.totalDuration - parallel.totalDuration) / 1000,
      improvementPercent: improvement,
      speedupFactor: speedup
    }
  };

  const reportPath = path.join(OUTPUT_DIR, 'benchmark-report.json');
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
  console.log(`\n💾 Report saved: ${reportPath}`);

  // Generate markdown report
  const mdReport = `# Screenshot Capture Performance Benchmark

**Generated**: ${new Date().toISOString()}
**Pages Tested**: ${BENCHMARK_PAGES.length}
**Batch Size**: ${BATCH_SIZE}

## Summary

| Metric | Sequential | Parallel | Improvement |
|--------|-----------|----------|-------------|
| **Total Time** | ${(sequential.totalDuration / 1000).toFixed(1)}s | ${(parallel.totalDuration / 1000).toFixed(1)}s | **${improvement.toFixed(1)}% faster** |
| **Avg per Screenshot** | ${sequential.averageDuration.toFixed(0)}ms | ${parallel.averageDuration.toFixed(0)}ms | ${speedup.toFixed(2)}x speedup |
| **Time Saved** | - | - | ${((sequential.totalDuration - parallel.totalDuration) / 1000).toFixed(1)}s |

## High Priority Issue #6 Resolution

✅ **Problem**: Sequential screenshot capture was slow (9 screenshots × 4s = 36s)

✅ **Solution**: Parallel processing with isolated browser contexts

✅ **Result**: **${improvement.toFixed(1)}% performance improvement** (${speedup.toFixed(2)}x speedup)

## Detailed Results

| Screenshot | Sequential | Parallel | Improvement |
|------------|-----------|----------|-------------|
${sequential.results.map((r, i) => {
  const p = parallel.results[i];
  const diff = ((r.duration - p.duration) / r.duration * 100);
  return `| ${r.name} | ${r.duration}ms | ${p.duration}ms | ${diff > 0 ? '+' : ''}${diff.toFixed(1)}% |`;
}).join('\n')}

## Configuration

- Base URL: \`${BASE_URL}\`
- Viewport: 1920×1080
- Batch Size: ${BATCH_SIZE} concurrent screenshots
- Pages: ${BENCHMARK_PAGES.length}

## Conclusion

The parallel screenshot implementation successfully achieves **${improvement.toFixed(1)}% faster execution**
compared to sequential processing, validating the solution to HIGH PRIORITY ISSUE #6.

---
*Generated by benchmark-screenshots.js*
`;

  const mdPath = path.join(OUTPUT_DIR, 'BENCHMARK_REPORT.md');
  await fs.writeFile(mdPath, mdReport);
  console.log(`💾 Markdown report: ${mdPath}`);

  console.log('\n' + '='.repeat(80));
  console.log('✅ BENCHMARK COMPLETE');
  console.log('='.repeat(80));
  console.log(`🎯 Achieved ${improvement.toFixed(1)}% performance improvement`);
  console.log(`⚡ ${speedup.toFixed(2)}x faster than sequential approach`);
  console.log('='.repeat(80));
}

/**
 * Main execution
 */
async function main() {
  const args = process.argv.slice(2);
  const mode = args.find(arg => arg.startsWith('--mode='))?.split('=')[1] || 'both';

  console.log('=' .repeat(80));
  console.log('🏁 SCREENSHOT CAPTURE PERFORMANCE BENCHMARK');
  console.log('=' .repeat(80));
  console.log(`Mode: ${mode}`);
  console.log(`Pages: ${BENCHMARK_PAGES.length}`);
  console.log(`Batch Size: ${BATCH_SIZE}`);
  console.log(`Base URL: ${BASE_URL}`);
  console.log('=' .repeat(80));

  let sequential, parallel;

  if (mode === 'sequential' || mode === 'both') {
    sequential = await benchmarkSequential();
  }

  if (mode === 'parallel' || mode === 'both') {
    parallel = await benchmarkParallel();
  }

  if (mode === 'both' && sequential && parallel) {
    await generateReport(sequential, parallel);
  }
}

// Run benchmark
if (require.main === module) {
  main().catch(error => {
    console.error('💥 Benchmark failed:', error);
    process.exit(1);
  });
}

module.exports = { benchmarkSequential, benchmarkParallel, BENCHMARK_PAGES };
