import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('Screen 14: Security Alerts & Protocol Probes E2E Verification', () => {
  test('renders alerts page, executes acknowledgement, and passes Axe a11y in Dark & Light themes', async ({
    page,
  }) => {
    await page.goto('/alerts');

    // 1. Verify Screen Header & Bento Cards
    await expect(page.getByRole('heading', { name: /Security Alerts & Protocol Probes/i })).toBeVisible();
    await expect(page.getByText(/Active Alerts/i).first()).toBeVisible();
    await expect(page.getByText(/Critical Alerts/i).first()).toBeVisible();
    await expect(page.getByText(/Probe Downgrades/i).first()).toBeVisible();
    await expect(page.getByText(/Active Probes/i).first()).toBeVisible();

    // 2. Verify Alert Items & Active Probes
    await expect(
      page.getByText(/New classical Shor-vulnerable RSA-2048 key detected in configs\/sshd_config/i)
    ).toBeVisible();
    await expect(
      page.getByText(/Active probe detected cipher suite downgrade to TLS_RSA_WITH_AES_128_CBC_SHA/i)
    ).toBeVisible();
    await expect(page.getByText('api.payments.internal:443')).toBeVisible();
    await expect(page.getByText('NEGOTIATED').first()).toBeVisible();
    await expect(page.getByText('SUPPORTED').first()).toBeVisible();

    // 3. Interactive Status Filtering
    const ackFilterBtn = page.getByRole('button', { name: /^Acknowledged/i });
    await ackFilterBtn.click();
    await expect(
      page.getByText(/Drift detected: 1 new algorithm added, 1 algorithm migrated to PQC/i)
    ).toBeVisible();

    const activeFilterBtn = page.getByRole('button', { name: /^Active/i });
    await activeFilterBtn.click();
    await expect(
      page.getByText(/New classical Shor-vulnerable RSA-2048 key detected/i)
    ).toBeVisible();

    // 4. Interactive Acknowledge Mutation
    const ackBtn = page.getByRole('button', { name: /Acknowledge alert alt-001/i });
    await ackBtn.click();
    // After acknowledging, the button should be gone from Active tab
    await expect(page.getByRole('button', { name: /Acknowledge alert alt-001/i })).not.toBeVisible();

    // 5. Search Filtering
    const searchInput = page.getByLabel('Search alerts');
    await searchInput.fill('downgrade');
    await expect(
      page.getByText(/Active probe detected cipher suite downgrade/i)
    ).toBeVisible();
    await searchInput.clear();

    // 6. Axe a11y Audit in Dark Mode (0 critical, 0 serious)
    const darkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const darkViolations = darkAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(darkViolations).toHaveLength(0);

    // 7. Toggle to Light Mode and Axe Audit
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

  test('Multi-viewport screenshots & performance check on /alerts', async ({ page }) => {
    const screenshotDir = path.join(process.cwd(), 'public', 'screenshots', 'viewports');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }

    const viewports = [
      { name: 'desktop', width: 1440, height: 900, file: 'screen-14-alerts-1440.png' },
      { name: 'laptop', width: 1280, height: 720, file: 'screen-14-alerts-1280.png' },
      { name: 'mobile', width: 390, height: 844, file: 'screen-14-alerts-390.png' },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/alerts');
      await expect(page.getByRole('heading', { name: /Security Alerts & Protocol Probes/i })).toBeVisible();

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
