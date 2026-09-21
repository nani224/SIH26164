import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('Screen 12: Estate Cryptographic Trend E2E Verification', () => {
  test('renders trend page, executes time-window switching, and passes Axe a11y in Dark & Light themes', async ({
    page,
  }) => {
    await page.goto('/trend');

    // 1. Verify Screen Header & Trajectory Bento Cards
    await expect(page.getByRole('heading', { name: /Estate Cryptographic Trend/i })).toBeVisible();
    await expect(page.getByText(/Risk Score Velocity/i)).toBeVisible();
    await expect(page.getByText(/Critical Assets Delta/i)).toBeVisible();
    await expect(page.getByText(/Total Findings Delta/i)).toBeVisible();
    await expect(page.getByText(/PQC Horizon Projection/i)).toBeVisible();

    // 2. Verify SVG Chart & Table
    await expect(
      page.getByRole('img', {
        name: /Trend line chart showing risk score and critical findings over time/i,
      })
    ).toBeVisible();
    await expect(page.getByRole('table', { name: /Daily Telemetry/i })).toBeVisible();
    await expect(page.getByText('2026-09-20')).toBeVisible();

    // 3. Interactive Time Window Switching
    const btn7d = page.getByRole('button', { name: /Show 7 days trend/i });
    await btn7d.click();
    await expect(btn7d).toHaveClass(/font-bold/);

    const btn30d = page.getByRole('button', { name: /Show 30 days trend/i });
    await btn30d.click();
    await expect(btn30d).toHaveClass(/font-bold/);

    // 4. Axe a11y Audit in Dark Mode (0 critical, 0 serious)
    const darkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const darkViolations = darkAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(darkViolations).toHaveLength(0);

    // 5. Toggle to Light Mode and Axe Audit
    const themeBtn = page.getByLabel('Toggle visual theme');
    await themeBtn.click();
    await page.waitForTimeout(200);

    const lightAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const lightViolations = lightAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(lightViolations).toHaveLength(0);

    // Switch back to Dark Mode
    await themeBtn.click();
  });

  test('Multi-viewport screenshots & performance check on /trend', async ({ page }) => {
    const screenshotDir = path.join(process.cwd(), 'public', 'screenshots', 'viewports');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }

    const viewports = [
      { name: 'desktop', width: 1440, height: 900, file: 'screen-12-trend-1440.png' },
      { name: 'laptop', width: 1280, height: 720, file: 'screen-12-trend-1280.png' },
      { name: 'mobile', width: 390, height: 844, file: 'screen-12-trend-390.png' },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/trend');
      await expect(page.getByRole('heading', { name: /Estate Cryptographic Trend/i })).toBeVisible();

      // Verify no layout shift / CLS < 0.1
      const cls = await page.evaluate(() => {
        return new Promise<number>((resolve) => {
          let clsValue = 0;
          const observer = new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
              if (!(entry as any).hadRecentInput) {
                clsValue += (entry as any).value;
              }
            }
          });
          observer.observe({ type: 'layout-shift', buffered: true });
          setTimeout(() => {
            observer.disconnect();
            resolve(clsValue);
          }, 500);
        });
      });
      expect(cls).toBeLessThan(0.1);

      // Capture screenshot
      const filePath = path.join(screenshotDir, vp.file);
      await page.screenshot({ path: filePath, fullPage: false });
      expect(fs.existsSync(filePath)).toBe(true);
    }
  });
});
