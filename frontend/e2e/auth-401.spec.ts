import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import path from 'path';

const ARTIFACTS_DIR = 'C:/Users/HP/.gemini/antigravity-ide/brain/d5af7d9a-7a01-45ed-8333-c5460de2bf93';

test.describe('ECDAT Auth Token, Actor Header & 401 Designed State E2E', () => {
  test('M1: Every API request carries Authorization: Bearer <token> and X-ECDAT-Actor: <actor>', async ({ page }) => {
    const capturedHeaders: Array<{ url: string; auth: string | null; actor: string | null }> = [];

    // Listen to all outgoing network requests
    page.on('request', (req) => {
      if (req.url().includes('/api/v1/')) {
        const headers = req.headers();
        capturedHeaders.push({
          url: req.url(),
          auth: headers['authorization'] || null,
          actor: headers['x-ecdat-actor'] || null,
        });
      }
    });

    await page.goto('/overview');
    await page.waitForLoadState('networkidle');

    expect(capturedHeaders.length).toBeGreaterThan(0);

    for (const entry of capturedHeaders) {
      console.log(`[CAPTURED API REQUEST]: ${entry.url} -> Auth: ${entry.auth}, Actor: ${entry.actor}`);
      expect(entry.auth).toMatch(/^Bearer\s+.+/);
      expect(entry.actor).toBeTruthy();
    }
  });

  test('M2: 401 is a designed, legible state across screens with wrong token', async ({ page }) => {
    // Set an intentionally wrong token in localStorage before page load
    await page.addInitScript(() => {
      localStorage.setItem('ecdat_api_token', 'wrong-invalid-token-12345');
      localStorage.setItem('ecdat_actor', 'security-auditor');
    });

    // Overview screen
    await page.goto('/overview');
    await page.waitForSelector('[role="region"][aria-label="Authentication Required State"]', { timeout: 10000 });

    const overviewTitle = await page.textContent('h2');
    expect(overviewTitle).toContain('API Authentication Required');

    const configBtn = page.getByRole('button', { name: /Configure API Token/i });
    await expect(configBtn).toBeVisible();

    // Launcher screen
    await page.goto('/launcher');
    await page.waitForSelector('[role="region"][aria-label="Authentication Required State"]', { timeout: 10000 });
    const launcherTitle = await page.textContent('h2');
    expect(launcherTitle).toContain('API Authentication Required');

    // Estate screen
    await page.goto('/estate');
    await page.waitForSelector('[role="region"][aria-label="Authentication Required State"]', { timeout: 10000 });

    // Inventory screen
    await page.goto('/inventory');
    await page.waitForSelector('[role="region"][aria-label="Authentication Required State"]', { timeout: 10000 });
  });

  test('M2/M4: Real-browser Axe accessibility audit & screenshots in dark and light themes', async ({ page }) => {
    // Set wrong token
    await page.addInitScript(() => {
      localStorage.setItem('ecdat_api_token', 'wrong-invalid-token-12345');
      localStorage.setItem('ecdat_actor', 'security-auditor');
    });

    // 1. Dark Theme
    await page.addInitScript(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await page.goto('/overview');
    await page.waitForSelector('[role="region"][aria-label="Authentication Required State"]');

    // Ensure dark theme attribute
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
      document.documentElement.classList.add('dark');
    });
    await page.waitForTimeout(500);

    const darkScreenshotPath = path.join(ARTIFACTS_DIR, 'screenshot_401_dark.png');
    await page.screenshot({ path: darkScreenshotPath, fullPage: true });
    console.log(`[SCREENSHOT SAVED]: ${darkScreenshotPath}`);

    const darkAxeResults = await new AxeBuilder({ page })
      .disableRules(['color-contrast']) // As per standard repo test config
      .analyze();

    const darkViolations = darkAxeResults.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(darkViolations).toHaveLength(0);

    // 2. Light Theme
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'light');
      document.documentElement.classList.remove('dark');
    });
    await page.waitForTimeout(500);

    const lightScreenshotPath = path.join(ARTIFACTS_DIR, 'screenshot_401_light.png');
    await page.screenshot({ path: lightScreenshotPath, fullPage: true });
    console.log(`[SCREENSHOT SAVED]: ${lightScreenshotPath}`);

    const lightAxeResults = await new AxeBuilder({ page })
      .disableRules(['color-contrast'])
      .analyze();

    const lightViolations = lightAxeResults.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(lightViolations).toHaveLength(0);
  });

  test('Live Backend: Requests carry headers and 401 is shown against real backend (MSW disabled)', async ({ page }) => {
    // Disable MSW so all requests hit the real FastAPI backend on port 8000 via Next.js rewrites
    await page.addInitScript(() => {
      (window as any).__DISABLE_MSW__ = true;
    });

    const liveCapturedHeaders: Array<{ url: string; auth: string | null; actor: string | null }> = [];
    page.on('request', (req) => {
      if (req.url().includes('/api/v1/')) {
        const headers = req.headers();
        liveCapturedHeaders.push({
          url: req.url(),
          auth: headers['authorization'] || null,
          actor: headers['x-ecdat-actor'] || null,
        });
      }
    });

    // 1. With wrong token -> Real backend responds 401
    await page.goto('/policies');
    await page.evaluate(() => {
      localStorage.setItem('ecdat_api_token', 'wrong-live-backend-token');
      localStorage.setItem('ecdat_actor', 'live-operator');
    });
    await page.reload();
    await page.waitForSelector('[role="region"][aria-label="Authentication Required State"]', { timeout: 10000 });

    const title = await page.textContent('h2');
    expect(title).toContain('API Authentication Required');

    // Confirm live network request carried both headers to backend
    expect(liveCapturedHeaders.length).toBeGreaterThan(0);
    const lastRequest = liveCapturedHeaders[liveCapturedHeaders.length - 1];
    expect(lastRequest.auth).toBe('Bearer wrong-live-backend-token');
    expect(lastRequest.actor).toBe('live-operator');
    console.log(`[LIVE BACKEND 401 CONFIRMED]: ${lastRequest.url} with Bearer wrong-live-backend-token -> 401 State rendered`);

    // 2. With valid token -> Real backend responds 200
    await page.evaluate(() => {
      localStorage.setItem('ecdat_api_token', 'ecdat-dev-insecure-token');
      localStorage.setItem('ecdat_actor', 'live-operator');
    });

    await page.reload();
    await expect(page.locator('input[value="Default NTRO baseline"]')).toBeVisible({ timeout: 10000 });
    console.log('[LIVE BACKEND 200 CONFIRMED]: Default NTRO baseline loaded successfully from real backend');
  });
});
