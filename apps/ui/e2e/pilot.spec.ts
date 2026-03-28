import { test, expect } from '@playwright/test';

test.describe('USF Platform — Pilot E2E', () => {
  test('login page renders', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading')).toContainText(/USF|Login/i);
  });

  test('dashboard accessible after login', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[type="email"]', 'demo@acme-bank.com');
    await page.fill('[type="password"]', 'demo123');
    await page.click('[type="submit"]');
    await page.waitForURL('**/dashboard');
    await expect(page.locator('usf-graph-viewer, [class*="graph"]')).toBeVisible();
  });

  test('query lab shows layer debug panel', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[type="email"]', 'demo@acme-bank.com');
    await page.fill('[type="password"]', 'demo123');
    await page.click('[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/query-lab');
    await page.click('button:has-text("Execute")');
    await expect(page.locator('usf-layer-debug-panel, [class*="layer-debug"]')).toBeVisible({ timeout: 5000 });
  });

  test('kg explorer renders graph', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[type="email"]', 'demo@acme-bank.com');
    await page.fill('[type="password"]', 'demo123');
    await page.click('[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/kg-explorer');
    await expect(page.locator('usf-graph-viewer, [class*="graph"]')).toBeVisible();
  });

  test('audit log renders entries', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[type="email"]', 'demo@acme-bank.com');
    await page.fill('[type="password"]', 'demo123');
    await page.click('[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/audit');
    await expect(page.locator('table')).toBeVisible();
    await expect(page.locator('tbody tr')).toHaveCount(20, { timeout: 5000 });
  });
});
