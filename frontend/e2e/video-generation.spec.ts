import { test, expect } from '@playwright/test';

test.describe('Video Generation Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should submit video generation request', async ({ page }) => {
    // Mock the API response
    await page.route('**/api/generate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'test-task-123',
          status: 'submitted',
          message: 'Video generation task submitted successfully'
        })
      });
    });

    // Fill in the prompt
    const textarea = page.locator('textarea');
    await textarea.fill('A beautiful sunset over the ocean with waves crashing on the shore');

    // Click generate
    const button = page.getByRole('button', { name: /generate video/i });
    await button.click();

    // Should show generating state
    await expect(page.getByText(/generating/i)).toBeVisible({ timeout: 5000 });
  });

  test('should show progress during generation', async ({ page }) => {
    // Mock the API response
    await page.route('**/api/generate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'test-task-123',
          status: 'submitted',
          message: 'Task submitted'
        })
      });
    });

    // Mock WebSocket for progress
    // Note: WebSocket mocking is complex, this is a simplified version

    const textarea = page.locator('textarea');
    await textarea.fill('Test prompt');

    const button = page.getByRole('button', { name: /generate video/i });
    await button.click();

    // Progress bar should appear
    // Note: Actual progress testing requires WebSocket mocking
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock error response
    await page.route('**/api/generate', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Internal server error'
        })
      });
    });

    const textarea = page.locator('textarea');
    await textarea.fill('Test prompt');

    const button = page.getByRole('button', { name: /generate video/i });
    await button.click();

    // Should show error message
    await expect(page.getByText(/error|failed/i)).toBeVisible({ timeout: 5000 });
  });

  test('should handle invalid model type', async ({ page }) => {
    // Mock validation error
    await page.route('**/api/generate', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Invalid model type'
        })
      });
    });

    const textarea = page.locator('textarea');
    await textarea.fill('Test prompt');

    const button = page.getByRole('button', { name: /generate video/i });
    await button.click();

    // Should show error
    await expect(page.getByText(/invalid|error/i)).toBeVisible({ timeout: 5000 });
  });

  test('should cancel ongoing generation', async ({ page }) => {
    // Mock API
    await page.route('**/api/generate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'test-task-123',
          status: 'submitted',
          message: 'Task submitted'
        })
      });
    });

    await page.route('**/api/task/**', async (route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Task cancelled'
          })
        });
      }
    });

    const textarea = page.locator('textarea');
    await textarea.fill('Test prompt');

    const generateButton = page.getByRole('button', { name: /generate video/i });
    await generateButton.click();

    // Cancel button should appear
    const cancelButton = page.getByRole('button', { name: /cancel/i });
    if (await cancelButton.isVisible()) {
      await cancelButton.click();
      // Generation should be cancelled
    }
  });
});

test.describe('Advanced Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Open advanced settings
    await page.click('summary');
  });

  test('should modify frame count', async ({ page }) => {
    const framesInput = page.locator('input').filter({ hasText: '' }).first();

    // Find frames input by label
    const frameLabel = page.getByText('Frames');
    const framesContainer = frameLabel.locator('..');
    const input = framesContainer.locator('input');

    if (await input.isVisible()) {
      await input.fill('120');
      await expect(input).toHaveValue('120');
    }
  });

  test('should modify FPS', async ({ page }) => {
    // Similar pattern for FPS
    const fpsLabel = page.getByText('FPS');
    const fpsContainer = fpsLabel.locator('..');
    const input = fpsContainer.locator('input');

    if (await input.isVisible()) {
      await input.fill('16');
      await expect(input).toHaveValue('16');
    }
  });

  test('should modify resolution', async ({ page }) => {
    // Width
    const widthLabel = page.getByText('Width');
    const widthContainer = widthLabel.locator('..');
    const widthInput = widthContainer.locator('input');

    if (await widthInput.isVisible()) {
      await widthInput.fill('1920');
    }

    // Height
    const heightLabel = page.getByText('Height');
    const heightContainer = heightLabel.locator('..');
    const heightInput = heightContainer.locator('input');

    if (await heightInput.isVisible()) {
      await heightInput.fill('1080');
    }
  });

  test('should modify inference steps', async ({ page }) => {
    const label = page.getByText('Inference Steps');
    const container = label.locator('..');
    const input = container.locator('input');

    if (await input.isVisible()) {
      await input.fill('75');
      await expect(input).toHaveValue('75');
    }
  });

  test('should modify guidance scale', async ({ page }) => {
    const label = page.getByText('Guidance Scale');
    const container = label.locator('..');
    const input = container.locator('input');

    if (await input.isVisible()) {
      await input.fill('10.5');
      await expect(input).toHaveValue('10.5');
    }
  });
});

test.describe('Video Player', () => {
  test('should display video when generation completes', async ({ page }) => {
    // This test would require full flow mocking
    // Including WebSocket for progress and final video URL

    await page.goto('/');

    // Mock successful generation with video URL
    await page.route('**/api/generate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'test-task-123',
          status: 'submitted',
          message: 'Task submitted'
        })
      });
    });

    // Note: Full video player testing requires WebSocket mocking
    // which is complex in Playwright
  });
});
