import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('Screen 3: Mosca Quantum Risk Matrix E2E & Real Browser Accessibility (Loops F2–F5)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/mosca');
    await page.waitForLoadState('networkidle');
  });

  test('Flow Test: Draggable CRQC Z horizon re-scores quantum assets while keeping classically broken fixed', async ({
    page,
  }) => {
    // 1. Initial State Verification
    await expect(page.locator('text=CRQC HORIZON: Z = 10y')).toBeVisible();

    // 2. Query initial SVG Y positions
    // SHA-1 (f-002) is classically broken
    const sha1Circle = page.locator('[data-testid="scatter-node-f-002"] circle').first();
    const sha1InitialCy = await sha1Circle.getAttribute('cy');

    // AES-128-GCM (f-005) is Grover quantum-sensitive asset
    const aesCircle = page.locator('[data-testid="scatter-node-f-005"] circle').first();
    const aesInitialCy = await aesCircle.getAttribute('cy');

    expect(sha1InitialCy).not.toBeNull();
    expect(aesInitialCy).not.toBeNull();

    // 3. Adjust Z slider from 10y to 5y
    const slider = page.getByLabel('CRQC Horizon in years');
    await slider.focus();
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('ArrowLeft');
    }

    // 4. Verify Z line text updates in DOM
    await expect(page.locator('text=CRQC HORIZON: Z = 5y')).toBeVisible();

    // 5. Invariant Assertion: Classically broken assets visibly remain fixed at U = 1
    const sha1PostCy = await sha1Circle.getAttribute('cy');
    expect(sha1PostCy).toBe(sha1InitialCy); // SHA-1 MUST NOT MOVE

    // 6. Verify side panel announces changed findings from server rescore
    await expect(page.locator('text=Scenario Horizon Shifts')).toBeVisible();
    await expect(page.locator('text=AES-128-GCM').first()).toBeVisible();

    // 7. Invariant Assertion: Quantum-sensitive assets re-calculate Urgency and shift Y
    await expect(aesCircle).not.toHaveAttribute('cy', aesInitialCy!);

    // 8. Verify screen-reader live region announced the change
    const liveRegion = page.locator('[aria-live="polite"]').first();
    await expect(liveRegion).toContainText('CRQC horizon updated to 5 years');
  });

  test('Keyboard-Only Walkthrough: Arrow key control of Z slider and Screen Reader announcement', async ({
    page,
  }) => {
    const slider = page.getByLabel('CRQC Horizon in years');
    await slider.focus();

    // Verify slider is activeElement
    const isFocused = await slider.evaluate((el) => el === document.activeElement);
    expect(isFocused).toBe(true);

    // Press ArrowLeft to decrement from 10 to 9
    await page.keyboard.press('ArrowLeft');
    await expect(page.locator('text=CRQC HORIZON: Z = 9y')).toBeVisible();

    // Press ArrowLeft to decrement from 9 to 8
    await page.keyboard.press('ArrowLeft');
    await expect(page.locator('text=CRQC HORIZON: Z = 8y')).toBeVisible();

    // Verify live region reflects keyboard change
    const liveRegion = page.locator('[aria-live="polite"]').first();
    await expect(liveRegion).toContainText('CRQC horizon updated to 8 years');

    // Press ArrowRight to increment back to 9
    await page.keyboard.press('ArrowRight');
    await expect(page.locator('text=CRQC HORIZON: Z = 9y')).toBeVisible();

    // Tab to a scatter point and press Enter to open finding drawer
    const node = page.locator('[data-testid="scatter-node-f-004"]');
    await node.focus();
    await page.keyboard.press('Enter');

    // Drawer should open and display RSA-2048 parameters
    await expect(page.locator('role=dialog')).toBeVisible();
    await expect(page.locator('text=RSA-2048 in certs/gateway_server.crt')).toBeVisible();

    // Press Escape to close drawer
    await page.keyboard.press('Escape');
    await expect(page.locator('role=dialog')).not.toBeVisible();
  });

  test('Loop F4 Accessibility: @axe-core/playwright real browser audit in Dark Mode', async ({
    page,
  }) => {
    await expect(page.locator('html')).toHaveClass(/dark/);

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const seriousOrCritical = accessibilityScanResults.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );

    expect(seriousOrCritical).toEqual([]);
  });

  test('Loop F4 Accessibility: @axe-core/playwright real browser audit in Light Mode', async ({
    page,
  }) => {
    // Toggle theme to Light
    const themeBtn = page.getByLabel('Toggle visual theme');
    await themeBtn.click();
    await expect(page.locator('html')).not.toHaveClass(/dark/);

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const seriousOrCritical = accessibilityScanResults.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );

    expect(seriousOrCritical).toEqual([]);
  });

  test('Loop F3 Visual QA: Capture screenshots across 3 viewports × 2 themes × 3 states', async ({
    page,
  }) => {
    const viewports = [
      { name: 'desktop', width: 1440, height: 900 },
      { name: 'tablet', width: 768, height: 1024 },
      { name: 'mobile', width: 375, height: 667 },
    ];

    const dir = path.join(process.cwd(), 'public', 'screenshots');
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      // 1. Typical State - Dark Mode
      await page.goto('/mosca');
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: path.join(dir, `mosca-typical-dark-${vp.name}.png`),
        fullPage: true,
      });

      // 2. Typical State - Light Mode
      const themeBtn = page.getByLabel('Toggle visual theme');
      await themeBtn.click();
      await page.waitForTimeout(150);
      await page.screenshot({
        path: path.join(dir, `mosca-typical-light-${vp.name}.png`),
        fullPage: true,
      });
      // Toggle back to dark
      await themeBtn.click();
    }

    // Capture Empty and Error states on Desktop
    await page.setViewportSize({ width: 1440, height: 900 });

    // Empty state
    await page.goto('/mosca?state=empty');
    await page.waitForLoadState('networkidle');
    await page.screenshot({
      path: path.join(dir, 'mosca-empty-dark-desktop.png'),
      fullPage: true,
    });

    // Error state
    await page.goto('/mosca?state=error');
    await page.waitForLoadState('networkidle');
    await page.screenshot({
      path: path.join(dir, 'mosca-error-dark-desktop.png'),
      fullPage: true,
    });
  });

  test('Loop F5 Performance: Layout Stability (CLS) measurement', async ({ page }) => {
    // Measure Cumulative Layout Shift via PerformanceObserver in browser context
    const cls = await page.evaluate(async () => {
      return new Promise<number>((resolve) => {
        let clsScore = 0;
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!(entry as any).hadRecentInput) {
              clsScore += (entry as any).value;
            }
          }
        });
        observer.observe({ type: 'layout-shift', buffered: true });
        setTimeout(() => {
          observer.disconnect();
          resolve(clsScore);
        }, 1000);
      });
    });

    // CLS budget for Core Web Vitals good rating is < 0.1
    expect(cls).toBeLessThan(0.05);
  });
});
