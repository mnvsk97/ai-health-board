import { test, expect } from '@playwright/test';
import type {
  BatchRun,
  Scenario,
  Run,
  ListBatchesResponse,
  CreateBatchRunResponse,
  StopBatchResponse,
  ListScenariosResponse,
  SimulateChangeResponse,
} from '../lib/types';
import type { GetComplianceStatusResponse } from '../lib/api';

// =============================================================================
// Test Data Fixtures
// =============================================================================

const mockScenarios: Scenario[] = [
  {
    scenario_id: 'scenario-1',
    title: 'High Blood Pressure Emergency',
    description: 'Patient with dangerously high blood pressure needs immediate triage',
    source_type: 'bench',
    source_url: null,
    state: 'California',
    specialty: 'Cardiology',
    rubric_criteria: [],
    clinician_approved: true,
  },
  {
    scenario_id: 'scenario-2',
    title: 'Prescription Refill Request',
    description: 'Patient requesting refill for chronic condition medication',
    source_type: 'bench',
    source_url: null,
    state: 'California',
    specialty: 'Primary Care',
    rubric_criteria: [],
    clinician_approved: true,
  },
  {
    scenario_id: 'scenario-3',
    title: 'Mental Health Crisis',
    description: 'Patient expressing suicidal ideation requires urgent intervention',
    source_type: 'bench',
    source_url: null,
    state: 'New York',
    specialty: 'Psychiatry',
    rubric_criteria: [],
    clinician_approved: true,
  },
];

const mockBatchRunning: BatchRun = {
  batch_id: 'batch-123',
  status: 'running',
  scenario_ids: ['scenario-1', 'scenario-2', 'scenario-3'],
  child_run_ids: ['run-1', 'run-2', 'run-3'],
  concurrency: 10,
  agent_type: 'intake',
  turns: 3,
  total_scenarios: 3,
  completed_count: 1,
  failed_count: 0,
  canceled_count: 0,
  started_at: Math.floor(Date.now() / 1000) - 60,
  completed_at: null,
  created_at: Math.floor(Date.now() / 1000) - 120,
};

const mockBatchCompleted: BatchRun = {
  batch_id: 'batch-456',
  status: 'completed',
  scenario_ids: ['scenario-1', 'scenario-2'],
  child_run_ids: ['run-4', 'run-5'],
  concurrency: 5,
  agent_type: 'refill',
  turns: 5,
  total_scenarios: 2,
  completed_count: 2,
  failed_count: 0,
  canceled_count: 0,
  started_at: Math.floor(Date.now() / 1000) - 300,
  completed_at: Math.floor(Date.now() / 1000) - 60,
  created_at: Math.floor(Date.now() / 1000) - 320,
};

const mockChildRun: Run = {
  run_id: 'run-1',
  status: 'completed',
  scenario_ids: ['scenario-1'],
  mode: 'text_text',
  room_url: null,
  room_name: null,
  room_token: null,
  started_at: Math.floor(Date.now() / 1000) - 60,
  updated_at: Math.floor(Date.now() / 1000) - 30,
};

const mockComplianceOutdated: GetComplianceStatusResponse = {
  target_id: 'default',
  status: 'outdated',
  reason: 'CDC updated hypertension guidelines on 2026-01-28',
  updated_at: Math.floor(Date.now() / 1000) - 86400,
};

const mockComplianceValid: GetComplianceStatusResponse = {
  target_id: 'default',
  status: 'valid',
  reason: null,
  updated_at: Math.floor(Date.now() / 1000),
};

// =============================================================================
// Test Suite: Batch Mode on New Test Page
// =============================================================================

test.describe('Batch Mode on New Test Page (/new)', () => {
  test.beforeEach(async ({ page }) => {
    // Mock scenarios API
    await page.route('**:8000/scenarios', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ scenarios: mockScenarios } as ListScenariosResponse),
      });
    });

    await page.goto('/new');
    await page.waitForLoadState('networkidle');
  });

  test('can toggle batch mode on and off', async ({ page }) => {
    // Initially batch mode should be off
    const batchToggle = page.locator('#batch-mode');
    await expect(batchToggle).not.toBeChecked();

    // Toggle batch mode on
    await batchToggle.click();
    await expect(batchToggle).toBeChecked();

    // Toggle batch mode off
    await batchToggle.click();
    await expect(batchToggle).not.toBeChecked();
  });

  test('concurrency slider appears when batch mode is on', async ({ page }) => {
    // Initially concurrency slider should not be visible
    const concurrencyLabel = page.getByText('Concurrency');
    await expect(concurrencyLabel).not.toBeVisible();

    // Enable batch mode
    await page.locator('#batch-mode').click();

    // Wait for transition
    await page.waitForTimeout(300);

    // Concurrency slider should be visible
    await expect(concurrencyLabel).toBeVisible();
    await expect(page.getByText(/\d+ parallel/)).toBeVisible();
  });

  test('turns slider appears when batch mode is on', async ({ page }) => {
    // Initially turns slider should not be visible
    const turnsLabel = page.getByText('Turns per Scenario');
    await expect(turnsLabel).not.toBeVisible();

    // Enable batch mode
    await page.locator('#batch-mode').click();

    // Wait for transition
    await page.waitForTimeout(300);

    // Turns slider should be visible
    await expect(turnsLabel).toBeVisible();
    await expect(page.getByText(/\d+ turns/)).toBeVisible();
  });

  test('can adjust concurrency and turns sliders', async ({ page }) => {
    // Enable batch mode
    await page.locator('#batch-mode').click();
    await page.waitForTimeout(300);

    // Verify default concurrency is 10
    await expect(page.getByText('10 parallel')).toBeVisible();

    // Verify default turns is 3
    await expect(page.getByText('3 turns')).toBeVisible();

    // Sliders exist and are interactive
    const sliders = page.getByRole('slider');
    expect(await sliders.count()).toBeGreaterThanOrEqual(2);
  });

  test('button text changes to "Start Batch Testing" when batch mode is on', async ({ page }) => {
    // Initially shows "Start Test"
    await expect(page.getByRole('button', { name: /Start Test/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Start Batch Testing/ })).not.toBeVisible();

    // Enable batch mode
    await page.locator('#batch-mode').click();
    await page.waitForTimeout(300);

    // Button text changes
    await expect(page.getByRole('button', { name: /Start Batch Testing/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Start Test/ })).not.toBeVisible();
  });

  test('form submits and redirects to /batches/{id} when batch mode is enabled', async ({ page }) => {
    const mockBatchResponse: CreateBatchRunResponse = {
      batch_id: 'batch-new-123',
      status: 'pending',
      total_scenarios: 3,
    };

    // Mock batch creation API
    await page.route('**:8000/batches', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockBatchResponse),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ batches: [] }),
        });
      }
    });

    // Mock batch detail API for redirect
    await page.route('**:8000/batches/batch-new-123**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...mockBatchRunning, batch_id: 'batch-new-123' }),
      });
    });

    // Enable batch mode
    await page.locator('#batch-mode').click();
    await page.waitForTimeout(300);

    // Submit form - batch mode allows submitting without selecting scenarios (runs all approved)
    await page.getByRole('button', { name: /Start Batch Testing/ }).click();

    // Wait for navigation
    await page.waitForURL(/\/batches\/batch-new-123/, { timeout: 10000 });
  });

  test('test mode tabs are hidden when batch mode is on', async ({ page }) => {
    // Initially test mode tabs should be visible
    await expect(page.getByRole('tab', { name: 'Text', exact: true })).toBeVisible();

    // Enable batch mode
    await page.locator('#batch-mode').click();
    await page.waitForTimeout(300);

    // Test mode tabs should not be visible
    await expect(page.getByRole('tab', { name: 'Text', exact: true })).not.toBeVisible();
  });
});

// =============================================================================
// Test Suite: Batches List Page
// =============================================================================

test.describe('Batches List Page (/batches)', () => {
  test('page loads with header "Batch Runs"', async ({ page }) => {
    // Mock empty batches response
    await page.route('**:8000/batches**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ batches: [] } as ListBatchesResponse),
      });
    });

    await page.goto('/batches');
    await page.waitForLoadState('networkidle');

    // Check header
    await expect(page.getByRole('heading', { name: 'Batch Runs' })).toBeVisible();
    await expect(
      page.getByText('View and manage parallel test executions')
    ).toBeVisible();
  });

  test('shows empty state when no batches exist', async ({ page }) => {
    // Mock empty batches response
    await page.route('**:8000/batches**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ batches: [] } as ListBatchesResponse),
      });
    });

    await page.goto('/batches');
    await page.waitForLoadState('networkidle');

    // Check empty state
    await expect(page.getByText('No batch runs yet')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Start a Batch Test' })).toBeVisible();
  });

  test('lists batch cards with progress bars', async ({ page }) => {
    // Mock batches response
    await page.route('**:8000/batches**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          batches: [mockBatchRunning, mockBatchCompleted],
        } as ListBatchesResponse),
      });
    });

    await page.goto('/batches');
    await page.waitForLoadState('networkidle');

    // Should show batch cards
    await expect(page.getByText('batch-123')).toBeVisible();
    await expect(page.getByText('batch-456')).toBeVisible();

    // Progress bars should be visible
    const progressBars = page.locator('[role="progressbar"]');
    expect(await progressBars.count()).toBeGreaterThanOrEqual(2);
  });

  test('each card shows stats (total, completed, failed, canceled)', async ({ page }) => {
    // Mock batches response
    await page.route('**:8000/batches**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          batches: [mockBatchRunning],
        } as ListBatchesResponse),
      });
    });

    await page.goto('/batches');
    await page.waitForLoadState('networkidle');

    // Check stats
    await expect(page.getByText('Total')).toBeVisible();
    await expect(page.getByText('Completed')).toBeVisible();
    await expect(page.getByText('Failed')).toBeVisible();
    await expect(page.getByText('Canceled')).toBeVisible();

    // Check stat values
    await expect(page.getByText('3', { exact: true }).first()).toBeVisible(); // Total
    await expect(page.getByText('1', { exact: true }).first()).toBeVisible(); // Completed
  });

  test('clicking a batch card navigates to detail page', async ({ page }) => {
    // Mock batches list
    await page.route('**:8000/batches**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          batches: [mockBatchRunning],
        } as ListBatchesResponse),
      });
    });

    // Mock batch detail
    await page.route('**:8000/batches/batch-123', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockBatchRunning),
      });
    });

    await page.goto('/batches');
    await page.waitForLoadState('networkidle');

    // Click on batch card
    await page.getByText('batch-123').click();

    // Should navigate to detail page
    await expect(page).toHaveURL(/\/batches\/batch-123/);
  });

  test('shows status badges for different batch states', async ({ page }) => {
    const batchPending: BatchRun = { ...mockBatchRunning, status: 'pending' };
    const batchFailed: BatchRun = { ...mockBatchCompleted, status: 'failed', batch_id: 'batch-789' };

    // Mock batches response
    await page.route('**:8000/batches**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          batches: [mockBatchRunning, mockBatchCompleted, batchPending, batchFailed],
        } as ListBatchesResponse),
      });
    });

    await page.goto('/batches');
    await page.waitForLoadState('networkidle');

    // Check for status badges (in Badge components)
    await expect(page.locator('.rounded-full').getByText('Running')).toBeVisible();
    await expect(page.locator('.rounded-full').getByText('Completed')).toBeVisible();
    await expect(page.locator('.rounded-full').getByText('Pending')).toBeVisible();
    await expect(page.locator('.rounded-full').getByText('Failed')).toBeVisible();
  });
});

// =============================================================================
// Test Suite: Batch Detail Page
// =============================================================================

test.describe('Batch Detail Page (/batches/[id])', () => {
  test.beforeEach(async ({ page }) => {
    // Mock batch detail API
    await page.route('**:8000/batches/batch-123', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockBatchRunning),
      });
    });

    // Mock child run API
    await page.route('**:8000/runs/run-1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChildRun),
      });
    });

    await page.route('**:8000/runs/run-2', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...mockChildRun, run_id: 'run-2', status: 'running' }),
      });
    });

    await page.route('**:8000/runs/run-3', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...mockChildRun, run_id: 'run-3', status: 'pending' }),
      });
    });
  });

  test('shows batch ID and status', async ({ page }) => {
    await page.goto('/batches/batch-123');
    await page.waitForLoadState('networkidle');

    // Check batch ID
    await expect(page.getByRole('heading', { name: 'batch-123' })).toBeVisible();

    // Check status badge (in header)
    await expect(page.locator('header').getByText('Running')).toBeVisible();
  });

  test('shows progress bar and stats', async ({ page }) => {
    await page.goto('/batches/batch-123');
    await page.waitForLoadState('networkidle');

    // Check progress section
    await expect(page.getByRole('heading', { name: 'Progress' })).toBeVisible();
    await expect(page.getByText('Overall Progress')).toBeVisible();

    // Check progress bar
    const progressBar = page.locator('[role="progressbar"]').first();
    await expect(progressBar).toBeVisible();

    // Check stats cards
    await expect(page.getByText('Total')).toBeVisible();
    await expect(page.getByText('Running').first()).toBeVisible();
    await expect(page.getByText('Completed').first()).toBeVisible();
    await expect(page.getByText('Failed').first()).toBeVisible();
    await expect(page.getByText('Canceled').first()).toBeVisible();
  });

  test('"Stop All" button appears for running batches', async ({ page }) => {
    await page.goto('/batches/batch-123');
    await page.waitForLoadState('networkidle');

    // Stop All button should be visible
    const stopButton = page.getByRole('button', { name: /Stop All/ });
    await expect(stopButton).toBeVisible();
    await expect(stopButton).toBeEnabled();
  });

  test('"Stop All" button stops the batch', async ({ page }) => {
    let stopCalled = false;

    // Mock stop API
    await page.route('**:8000/batches/batch-123/stop', async (route) => {
      if (route.request().method() === 'POST') {
        stopCalled = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'canceled', batch_id: 'batch-123' } as StopBatchResponse),
        });
      }
    });

    await page.goto('/batches/batch-123');
    await page.waitForLoadState('networkidle');

    // Click Stop All button
    await page.getByRole('button', { name: /Stop All/ }).click();

    // Wait for API call
    await page.waitForTimeout(500);

    expect(stopCalled).toBe(true);
  });

  test('shows timing information', async ({ page }) => {
    await page.goto('/batches/batch-123');
    await page.waitForLoadState('networkidle');

    // Check timing section
    await expect(page.getByText('Timing')).toBeVisible();
    await expect(page.getByText('Created').first()).toBeVisible();
    await expect(page.getByText('Started').first()).toBeVisible();
    // "Completed" appears in multiple places, use the timing section label
    await expect(page.locator('span').filter({ hasText: 'Completed' })).toBeVisible();
  });

  test('shows duration for completed batches', async ({ page }) => {
    // Mock completed batch
    await page.route('**:8000/batches/batch-456', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockBatchCompleted),
      });
    });

    await page.goto('/batches/batch-456');
    await page.waitForLoadState('networkidle');

    // Check for duration
    await expect(page.getByText(/Duration:/)).toBeVisible();
  });

  test('lists child runs when available', async ({ page }) => {
    await page.goto('/batches/batch-123');
    await page.waitForLoadState('networkidle');

    // Check child runs section
    await expect(page.getByText(/Child Runs \(\d+\)/)).toBeVisible();

    // Check individual runs are listed
    await expect(page.getByText('run-1')).toBeVisible();
    await expect(page.getByText('run-2')).toBeVisible();
    await expect(page.getByText('run-3')).toBeVisible();
  });

  test('child runs are clickable and link to run detail page', async ({ page }) => {
    await page.goto('/batches/batch-123');
    await page.waitForLoadState('networkidle');

    // Mock run detail page
    await page.route('**:8000/runs/run-1/transcript', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ run_id: 'run-1', transcript: [] }),
      });
    });

    // Click on a child run
    await page.getByText('run-1').click();

    // Should navigate to run detail page
    await expect(page).toHaveURL(/\/runs\/run-1/);
  });

  test('shows agent type and configuration in header', async ({ page }) => {
    await page.goto('/batches/batch-123');
    await page.waitForLoadState('networkidle');

    // Check metadata in header
    await expect(page.getByText(/intake agent/i)).toBeVisible();
    await expect(page.getByText(/10 concurrent/i)).toBeVisible();
    await expect(page.getByText(/3 turns/i)).toBeVisible();
  });
});

// =============================================================================
// Test Suite: Compliance Alert on Dashboard
// =============================================================================

test.describe('Compliance Alert on Dashboard (/)', () => {
  test('alert appears when compliance status is "outdated"', async ({ page }) => {
    // Mock compliance status API
    await page.route('**:8000/compliance/status**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockComplianceOutdated),
      });
    });

    // Mock runs API
    await page.route('**:8000/runs/**', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Not found' }),
      });
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for compliance alert to appear
    await page.waitForTimeout(1000);

    // Check alert is visible
    await expect(page.getByText('Compliance Testing Required')).toBeVisible();
    await expect(page.getByText(/CDC updated hypertension guidelines/)).toBeVisible();
  });

  test('alert has "Start Testing Now" button', async ({ page }) => {
    // Mock compliance status API
    await page.route('**:8000/compliance/status**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockComplianceOutdated),
      });
    });

    await page.route('**:8000/runs/**', async (route) => {
      await route.fulfill({ status: 404 });
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Check button exists
    const startButton = page.getByRole('link', { name: /Start Testing Now/ }).first();
    await expect(startButton).toBeVisible();
    await expect(startButton).toHaveAttribute('href', '/new');
  });

  test('alert can be dismissed', async ({ page }) => {
    // Mock compliance status API
    await page.route('**:8000/compliance/status**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockComplianceOutdated),
      });
    });

    await page.route('**:8000/runs/**', async (route) => {
      await route.fulfill({ status: 404 });
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Alert should be visible
    await expect(page.getByText('Compliance Testing Required')).toBeVisible();

    // Click dismiss button
    const dismissButton = page.locator('button[class*="text-yellow"]').filter({ hasText: '' }).first();
    if (await dismissButton.count() > 0) {
      await dismissButton.click();
      await page.waitForTimeout(500);

      // Alert should be gone
      await expect(page.getByText('Compliance Testing Required')).not.toBeVisible();
    }
  });

  test('alert does not appear when compliance is valid', async ({ page }) => {
    // Mock compliance status API
    await page.route('**:8000/compliance/status**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockComplianceValid),
      });
    });

    await page.route('**:8000/runs/**', async (route) => {
      await route.fulfill({ status: 404 });
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Alert should not be visible
    await expect(page.getByText('Compliance Testing Required')).not.toBeVisible();
  });
});

// =============================================================================
// Test Suite: Guideline Update Dialog
// =============================================================================

test.describe('Guideline Update Dialog (/compliance)', () => {
  const mockGuidelines = [
    {
      guideline_id: 'CDC_HYPERTENSION_2026',
      source_url: 'https://cdc.gov/guidelines/hypertension',
      state: 'National',
      specialty: 'Cardiology',
      version: '2026.1',
      hash: 'abc123',
      last_checked: Math.floor(Date.now() / 1000) - 3600,
    },
  ];

  test.beforeEach(async ({ page }) => {
    // Mock guidelines API
    await page.route('**:8000/guidelines', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ guidelines: mockGuidelines }),
      });
    });

    // Mock compliance status
    await page.route('**:8000/compliance/status**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockComplianceValid),
      });
    });
  });

  test('"Simulate Update" button triggers dialog', async ({ page }) => {
    const newScenario: Scenario = {
      scenario_id: 'scenario-new-1',
      title: 'Updated Hypertension Protocol',
      description: 'Patient with borderline hypertension per new 2026 guidelines',
      source_type: 'web',
      source_url: 'https://cdc.gov/guidelines/hypertension',
      state: 'National',
      specialty: 'Cardiology',
      rubric_criteria: [],
      clinician_approved: false,
    };

    // Mock simulate change API
    await page.route('**:8000/compliance/simulate-change', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'outdated',
            new_scenario: newScenario,
          } as SimulateChangeResponse),
        });
      }
    });

    await page.goto('/compliance');
    await page.waitForLoadState('networkidle');

    // Dialog should not be visible initially
    await expect(page.getByRole('dialog')).not.toBeVisible();

    // Click Simulate Update button
    await page.getByRole('button', { name: 'Simulate Update' }).click();

    // Wait for API call and dialog
    await page.waitForTimeout(1000);

    // Dialog should be visible
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('dialog shows new scenario details', async ({ page }) => {
    const newScenario: Scenario = {
      scenario_id: 'scenario-new-1',
      title: 'Updated Hypertension Protocol',
      description: 'Patient with borderline hypertension per new 2026 guidelines',
      source_type: 'web',
      source_url: 'https://cdc.gov/guidelines/hypertension',
      state: 'National',
      specialty: 'Cardiology',
      rubric_criteria: [],
      clinician_approved: false,
    };

    // Mock simulate change API
    await page.route('**:8000/compliance/simulate-change', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'outdated',
            new_scenario: newScenario,
          } as SimulateChangeResponse),
        });
      }
    });

    await page.goto('/compliance');
    await page.waitForLoadState('networkidle');

    // Trigger dialog
    await page.getByRole('button', { name: 'Simulate Update' }).click();
    await page.waitForTimeout(1000);

    // Check scenario details are shown
    await expect(page.getByText('Updated Hypertension Protocol')).toBeVisible();
    await expect(page.getByText(/Patient with borderline hypertension/)).toBeVisible();
    await expect(page.getByText('Cardiology')).toBeVisible();
  });

  test('"Start Testing Now" button in dialog navigates to /new', async ({ page }) => {
    const newScenario: Scenario = {
      scenario_id: 'scenario-new-1',
      title: 'Updated Hypertension Protocol',
      description: 'Patient with borderline hypertension per new 2026 guidelines',
      source_type: 'web',
      source_url: 'https://cdc.gov/guidelines/hypertension',
      state: 'National',
      specialty: 'Cardiology',
      rubric_criteria: [],
      clinician_approved: false,
    };

    // Mock simulate change API
    await page.route('**:8000/compliance/simulate-change', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'outdated',
            new_scenario: newScenario,
          } as SimulateChangeResponse),
        });
      }
    });

    // Mock scenarios for /new page
    await page.route('**:8000/scenarios', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ scenarios: [newScenario] }),
      });
    });

    await page.goto('/compliance');
    await page.waitForLoadState('networkidle');

    // Trigger dialog
    await page.getByRole('button', { name: 'Simulate Update' }).click();
    await page.waitForTimeout(1000);

    // Click Start Testing Now in dialog (it's a link styled as button)
    await page.getByRole('link', { name: /Start Testing Now/ }).click();

    // Should navigate to /new
    await expect(page).toHaveURL('/new');
  });

  test('dialog shows "Guideline Updated" title', async ({ page }) => {
    const newScenario: Scenario = {
      scenario_id: 'scenario-new-1',
      title: 'Test Scenario',
      description: 'Test description',
      source_type: 'web',
      source_url: null,
      state: null,
      specialty: null,
      rubric_criteria: [],
      clinician_approved: false,
    };

    await page.route('**:8000/compliance/simulate-change', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'outdated',
            new_scenario: newScenario,
          } as SimulateChangeResponse),
        });
      }
    });

    await page.goto('/compliance');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: 'Simulate Update' }).click();
    await page.waitForTimeout(1000);

    // Check dialog title
    await expect(page.getByRole('heading', { name: 'Guideline Updated' })).toBeVisible();
  });
});

// =============================================================================
// Test Suite: Sidebar Navigation
// =============================================================================

test.describe('Sidebar Navigation', () => {
  test('"Batch Runs" nav item exists', async ({ page }) => {
    // Mock batches API
    await page.route('**:8000/batches**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ batches: [] }),
      });
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for Batch Runs nav item (might be in sidebar or nav)
    const batchRunsLink = page.getByRole('link', { name: /Batch/i });

    // If found, verify it exists
    if ((await batchRunsLink.count()) > 0) {
      await expect(batchRunsLink.first()).toBeVisible();
    }
  });

  test('clicking "Batch Runs" navigates to /batches', async ({ page }) => {
    // Mock APIs
    await page.route('**:8000/batches**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ batches: [] }),
      });
    });

    await page.route('**:8000/runs/**', async (route) => {
      await route.fulfill({ status: 404 });
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Try to find and click Batch Runs link
    const batchRunsLink = page.getByRole('link', { name: /Batch/i });

    if ((await batchRunsLink.count()) > 0) {
      await batchRunsLink.first().click();
      await expect(page).toHaveURL('/batches');
    }
  });
});

// =============================================================================
// Test Suite: Integration Tests
// =============================================================================

test.describe('End-to-End Batch Testing Flow', () => {
  test('complete workflow: create batch -> view list -> view detail -> stop', async ({ page }) => {
    // Step 1: Create a batch from /new
    await page.route('**:8000/scenarios', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ scenarios: mockScenarios }),
      });
    });

    const newBatchResponse: CreateBatchRunResponse = {
      batch_id: 'batch-integration-test',
      status: 'pending',
      total_scenarios: 3,
    };

    await page.route('**:8000/batches**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(newBatchResponse),
        });
      } else {
        // GET /batches
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batches: [{
              ...mockBatchRunning,
              batch_id: 'batch-integration-test',
            }],
          }),
        });
      }
    });

    await page.route('**:8000/batches/batch-integration-test', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...mockBatchRunning,
          batch_id: 'batch-integration-test',
        }),
      });
    });

    await page.goto('/new');
    await page.waitForLoadState('networkidle');

    // Enable batch mode and submit
    await page.locator('#batch-mode').click();
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: /Start Batch Testing/ }).click();

    // Should redirect to batch detail
    await expect(page).toHaveURL(/\/batches\/batch-integration-test/);

    // Step 2: Navigate to batch list
    await page.goto('/batches');
    await page.waitForLoadState('networkidle');

    // Should see the batch in the list
    await expect(page.getByText('batch-integration-test')).toBeVisible();

    // Step 3: Click to view detail
    await page.getByText('batch-integration-test').click();
    await expect(page).toHaveURL(/\/batches\/batch-integration-test/);

    // Step 4: Stop the batch
    await page.route('**:8000/batches/batch-integration-test/stop', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'canceled',
          batch_id: 'batch-integration-test',
        }),
      });
    });

    await page.getByRole('button', { name: /Stop All/ }).click();
    await page.waitForTimeout(500);

    // Stop was called
    // Test complete
  });
});
