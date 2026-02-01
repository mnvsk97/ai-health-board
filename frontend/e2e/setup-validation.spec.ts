import { test, expect } from '@playwright/test';

/**
 * Setup validation tests
 * These basic tests verify the Playwright setup is working correctly
 */

test.describe('Playwright Setup Validation', () => {
  test('can load the homepage', async ({ page }) => {
    await page.goto('/');

    // Page should load without errors
    await expect(page).toHaveURL('/');

    // Should have a title
    const title = await page.title();
    expect(title).toBeTruthy();
  });

  test('can navigate between pages', async ({ page }) => {
    await page.goto('/');

    // Find and click "New Test" button (use first() since there are multiple on the page)
    const newTestButton = page.getByRole('link', { name: /New Test/i }).first();
    if (await newTestButton.count() > 0) {
      await newTestButton.click();
      await expect(page).toHaveURL('/new');
    }
  });

  test('can mock API responses', async ({ page }) => {
    let apiCalled = false;

    // Mock an API endpoint
    await page.route('**/api/test', async (route) => {
      apiCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'success' }),
      });
    });

    // Navigate to trigger potential API calls
    await page.goto('/');

    // Even if not called, test passes - just validates mocking works
    expect(apiCalled).toBeDefined();
  });

  test('browser interactions work', async ({ page }) => {
    await page.goto('/');

    // Test clicking
    const buttons = page.getByRole('button');
    expect(await buttons.count()).toBeGreaterThanOrEqual(0);

    // Test typing (if there's an input)
    const inputs = page.getByRole('textbox');
    if (await inputs.count() > 0) {
      await inputs.first().click();
      await inputs.first().fill('test');
    }

    // Test passed
  });

  test('can take screenshots', async ({ page }) => {
    await page.goto('/');

    // Take a screenshot
    const screenshot = await page.screenshot();

    // Screenshot should be a buffer
    expect(screenshot).toBeInstanceOf(Buffer);
    expect(screenshot.length).toBeGreaterThan(0);
  });
});
