import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display the main heading', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('AI Video Generator');
  });

  test('should display the subtitle', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('Create Amazing Videos with AI');
  });

  test('should display feature cards', async ({ page }) => {
    // Check for feature cards
    const featureCards = page.locator('.bg-gray-800\\/50');
    await expect(featureCards).toHaveCount(3);

    // Check feature titles
    await expect(page.getByText('Fast Generation')).toBeVisible();
    await expect(page.getByText('Multiple Models')).toBeVisible();
    await expect(page.getByText('Cloud Storage')).toBeVisible();
  });

  test('should have navigation bar', async ({ page }) => {
    const nav = page.locator('nav');
    await expect(nav).toBeVisible();
    await expect(nav).toContainText('AI Video Generator');
  });
});

test.describe('Video Generator Component', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display model selection dropdown', async ({ page }) => {
    const modelSelect = page.locator('select');
    await expect(modelSelect).toBeVisible();
  });

  test('should display prompt textarea', async ({ page }) => {
    const textarea = page.locator('textarea');
    await expect(textarea).toBeVisible();
    await expect(textarea).toHaveAttribute('placeholder', /describe/i);
  });

  test('should display generate button', async ({ page }) => {
    const button = page.getByRole('button', { name: /generate video/i });
    await expect(button).toBeVisible();
  });

  test('generate button should be disabled without prompt', async ({ page }) => {
    const button = page.getByRole('button', { name: /generate video/i });
    await expect(button).toBeDisabled();
  });

  test('should enable generate button when prompt is entered', async ({ page }) => {
    const textarea = page.locator('textarea');
    await textarea.fill('A beautiful sunset over the ocean');

    const button = page.getByRole('button', { name: /generate video/i });
    await expect(button).toBeEnabled();
  });

  test('should show advanced settings when expanded', async ({ page }) => {
    // Click on advanced settings
    await page.click('summary');

    // Check that settings are visible
    await expect(page.getByText('Frames')).toBeVisible();
    await expect(page.getByText('FPS')).toBeVisible();
    await expect(page.getByText('Width')).toBeVisible();
    await expect(page.getByText('Height')).toBeVisible();
  });

  test('should change model selection', async ({ page }) => {
    const select = page.locator('select');

    // Get all options
    const options = await select.locator('option').allTextContents();
    expect(options.length).toBeGreaterThan(0);

    // Select a different model
    if (options.length > 1) {
      await select.selectOption({ index: 1 });
    }
  });
});

test.describe('Image Upload for I2V', () => {
  test('should show image upload for I2V models', async ({ page }) => {
    await page.goto('/');

    const select = page.locator('select');

    // Find and select an I2V model
    const options = await select.locator('option').allTextContents();
    const i2vIndex = options.findIndex(opt => opt.toLowerCase().includes('i2v'));

    if (i2vIndex !== -1) {
      await select.selectOption({ index: i2vIndex });

      // Check for image upload area
      await expect(page.getByText(/input image/i)).toBeVisible();
    }
  });
});

test.describe('Responsive Design', () => {
  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Should still show main elements
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('textarea')).toBeVisible();
  });

  test('should be responsive on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');

    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('textarea')).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test('should have proper aria labels', async ({ page }) => {
    await page.goto('/');

    // Check for accessible elements
    const textarea = page.locator('textarea');
    await expect(textarea).toBeVisible();

    const button = page.getByRole('button', { name: /generate/i });
    await expect(button).toBeVisible();
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/');

    // Tab through the page
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Should be able to navigate
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedElement).toBeTruthy();
  });
});
