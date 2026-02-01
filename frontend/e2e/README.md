# End-to-End Tests

This directory contains Playwright end-to-end tests for the AI Health Board frontend.

## Setup

Install dependencies and Playwright browsers:

```bash
npm install
npx playwright install chromium
```

## Running Tests

### All Tests

```bash
npm run test:e2e
```

### Interactive UI Mode (Recommended for Development)

```bash
npm run test:e2e:ui
```

This opens the Playwright Test UI where you can:
- Run individual tests
- See live test execution
- Time-travel through test steps
- Inspect DOM snapshots

### Headed Mode (See Browser)

```bash
npm run test:e2e:headed
```

### Debug Mode (Step Through Tests)

```bash
npm run test:e2e:debug
```

### Specific Test File

```bash
npx playwright test e2e/batch-testing.spec.ts
```

### View Test Report

```bash
npm run test:e2e:report
```

## Test Coverage

### Batch Testing (`batch-testing.spec.ts`)

Comprehensive tests for batch testing functionality:

1. **Batch Mode on New Test Page (/new)**
   - Toggle batch mode on/off
   - Concurrency and turns sliders visibility and interaction
   - Button text changes based on mode
   - Form submission and redirect to batch detail page

2. **Batches List Page (/batches)**
   - Page header and layout
   - Empty state display
   - Batch cards with progress bars
   - Stats display (total, completed, failed, canceled)
   - Navigation to batch detail
   - Status badges

3. **Batch Detail Page (/batches/[id])**
   - Batch ID and status display
   - Progress bar and stats cards
   - "Stop All" button for running batches
   - Timing information and duration
   - Child runs list with links
   - Agent configuration display

4. **Compliance Alert on Dashboard (/)**
   - Alert appearance for outdated compliance
   - "Start Testing Now" button
   - Alert dismissal
   - No alert when compliance is valid

5. **Guideline Update Dialog (/compliance)**
   - "Simulate Update" button triggers dialog
   - New scenario details in dialog
   - "Start Testing Now" navigation to /new
   - Dialog title and structure

6. **Sidebar Navigation**
   - "Batch Runs" nav item existence
   - Navigation to /batches

7. **Integration Tests**
   - End-to-end workflow: create → list → detail → stop

## API Mocking

Tests use Playwright's `page.route()` to mock API responses. Mock data includes:

- Scenarios
- Batch runs (running, completed, pending, failed)
- Child runs
- Compliance status
- Guidelines

## Best Practices

1. **Use Role-Based Selectors**: Prefer `getByRole()`, `getByLabel()`, and `getByText()`
2. **Wait for Network Idle**: Use `page.waitForLoadState('networkidle')` after navigation
3. **Mock API Responses**: Don't rely on backend availability
4. **Test User Behavior**: Simulate realistic interactions with appropriate delays
5. **Independent Tests**: Each test should be self-contained

## Debugging Failed Tests

1. **View Trace**: Traces are captured on first retry
   ```bash
   npx playwright show-trace trace.zip
   ```

2. **Screenshots**: Captured automatically on failure in `test-results/`

3. **Pause Test**: Add `await page.pause()` to debug interactively

4. **Console Logs**: Use `page.on('console', msg => console.log(msg.text()))`

## CI/CD

Tests can run in CI with:

```bash
CI=1 npm run test:e2e
```

This enables:
- Retries (2 attempts)
- Single worker for stability
- HTML report generation

## Writing New Tests

1. Create test file in `e2e/` directory
2. Import test utilities:
   ```typescript
   import { test, expect } from '@playwright/test';
   ```
3. Group related tests in `test.describe()` blocks
4. Use `test.beforeEach()` for common setup
5. Mock API routes as needed
6. Write descriptive test names
7. Add assertions with `expect()`

Example:

```typescript
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/endpoint', async (route) => {
      await route.fulfill({ status: 200, body: JSON.stringify(mockData) });
    });
    await page.goto('/path');
  });

  test('should do something', async ({ page }) => {
    await page.getByRole('button', { name: 'Click Me' }).click();
    await expect(page.getByText('Success')).toBeVisible();
  });
});
```

## Troubleshooting

### Port Already in Use

If port 3000 is occupied, the dev server won't start. Kill the existing process:

```bash
lsof -ti:3000 | xargs kill -9
```

### Test Timeouts

Increase timeout in `playwright.config.ts`:

```typescript
timeout: 30000, // 30 seconds per test
```

### Flaky Tests

- Add explicit waits: `await page.waitForSelector()`
- Wait for animations: `await page.waitForTimeout(300)`
- Use stable selectors: data-testid attributes
- Check for network idle: `page.waitForLoadState('networkidle')`
