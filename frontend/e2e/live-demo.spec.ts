import { test, expect } from '@playwright/test';

/**
 * Live E2E Demo Test
 *
 * This test runs against real servers (API, Agent, Frontend) and demonstrates:
 * 1. Navigate to dashboard
 * 2. Check scenarios list
 * 3. Start a new batch test
 * 4. View runs and grading results
 * 5. Check compliance page
 */

test.describe('Live E2E Demo', () => {
  test.setTimeout(120000); // 2 minute timeout for real API calls

  test('complete workflow: dashboard → scenarios → batch test → view results', async ({ page }) => {
    // Step 1: Navigate to Dashboard
    console.log('Step 1: Navigating to Dashboard...');
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Take screenshot
    await page.screenshot({ path: '/tmp/screenshots/01-dashboard.png', fullPage: true });

    // Verify dashboard loads
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    console.log('✓ Dashboard loaded');

    // Step 2: Navigate to Scenarios page
    console.log('Step 2: Checking Scenarios...');
    await page.getByRole('link', { name: /Scenarios/i }).click();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: '/tmp/screenshots/02-scenarios.png', fullPage: true });

    // Check scenarios are listed
    await expect(page.getByRole('heading', { name: 'Scenarios', exact: true })).toBeVisible();
    console.log('✓ Scenarios page loaded');

    // Step 3: Navigate to Runs page
    console.log('Step 3: Checking Runs...');
    await page.getByRole('link', { name: /Runs/i }).first().click();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: '/tmp/screenshots/03-runs.png', fullPage: true });

    await expect(page.getByRole('heading', { name: 'Test Runs' })).toBeVisible();
    console.log('✓ Runs page loaded');

    // Step 4: Navigate to New Test page
    console.log('Step 4: Starting new test...');
    await page.getByRole('link', { name: /New Test/i }).first().click();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: '/tmp/screenshots/04-new-test.png', fullPage: true });

    await expect(page.getByRole('heading', { name: /New Test/i })).toBeVisible();
    console.log('✓ New Test page loaded');

    // Step 5: Enable batch mode and configure
    console.log('Step 5: Configuring batch test...');
    const batchToggle = page.locator('#batch-mode');
    if (await batchToggle.isVisible()) {
      await batchToggle.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: '/tmp/screenshots/05-batch-mode.png', fullPage: true });
      console.log('✓ Batch mode enabled');
    }

    // Step 6: Navigate to Compliance page
    console.log('Step 6: Checking Compliance...');
    await page.getByRole('link', { name: /Compliance/i }).click();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: '/tmp/screenshots/06-compliance.png', fullPage: true });

    await expect(page.getByRole('heading', { name: 'Compliance', exact: true })).toBeVisible();
    console.log('✓ Compliance page loaded');

    // Step 7: Navigate to Batches page
    console.log('Step 7: Checking Batches...');
    await page.getByRole('link', { name: /Batch/i }).click();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: '/tmp/screenshots/07-batches.png', fullPage: true });

    await expect(page.getByRole('heading', { name: 'Batch Runs' })).toBeVisible();
    console.log('✓ Batches page loaded');

    console.log('\n✅ All UI pages verified successfully!');
  });

  test('start batch test and monitor progress', async ({ page }) => {
    // Navigate to new test page
    console.log('Starting batch test...');
    await page.goto('/new');
    await page.waitForLoadState('networkidle');

    // Enable batch mode
    const batchToggle = page.locator('#batch-mode');
    if (await batchToggle.isVisible()) {
      await batchToggle.click();
      await page.waitForTimeout(500);
    }

    // Start the batch test
    const startButton = page.getByRole('button', { name: /Start Batch Testing/i });
    if (await startButton.isVisible()) {
      await startButton.click();
      console.log('Batch test started');

      // Wait for redirect to batch detail page
      await page.waitForTimeout(2000);
      await page.screenshot({ path: '/tmp/screenshots/08-batch-started.png', fullPage: true });

      // Check if we're on batch detail page
      const url = page.url();
      console.log(`Redirected to: ${url}`);

      if (url.includes('/batches/')) {
        console.log('✓ Batch created and redirected to detail page');

        // Wait and take another screenshot to see progress
        await page.waitForTimeout(5000);
        await page.screenshot({ path: '/tmp/screenshots/09-batch-progress.png', fullPage: true });
      }
    }

    console.log('✅ Batch test workflow completed');
  });
});
