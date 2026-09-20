import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('Screen 11: Continuous Estate Console E2E Verification', () => {
  test('renders estate console, executes interactive operations, and passes Axe a11y in Dark & Light themes', async ({
    page,
  }) => {
    await page.goto('/estate');

    // 1. Verify Screen Header & Bento Metrics
    await expect(page.getByRole('heading', { name: /Cryptographic Estate Console/i })).toBeVisible();
    await expect(page.getByText(/Total Targets/i)).toBeVisible();
    await expect(page.getByText(/Total Scans/i)).toBeVisible();
    await expect(page.getByText(/Critical Findings/i)).toBeVisible();
    await expect(page.getByText(/PQC Readiness/i)).toBeVisible();
    await expect(page.getByText(/Active Alerts/i)).toBeVisible();

    // 2. Verify Monitored Targets Table
    await expect(page.getByText('Core Payment Gateway')).toBeVisible();
    await expect(page.getByText('Gateway Firmware Binary')).toBeVisible();
    await expect(page.getByText('Production Ingress TLS')).toBeVisible();

    // 3. Interactive Search Filter
    const searchInput = page.getByLabel('Search targets');
    await searchInput.fill('Payment');
    await expect(page.getByText('Core Payment Gateway')).toBeVisible();
    await expect(page.getByText('Gateway Firmware Binary')).not.toBeVisible();
    await searchInput.clear();
    await expect(page.getByText('Gateway Firmware Binary')).toBeVisible();

    // 4. Interactive Scan Now Execution
    const scanNowBtn = page.getByRole('button', { name: /Scan target Core Payment Gateway/i });
    await scanNowBtn.click();
    await expect(page.getByText(/Active scan initiated/i)).toBeVisible();

    // 5. Register Target Modal Flow
    const registerBtn = page.getByRole('button', { name: 'Register Target' });
    await registerBtn.click();
    const dialog = page.getByRole('dialog', { name: /Register Cryptographic Target/i });
    await expect(dialog).toBeVisible();

    await page.getByPlaceholder(/e\.g\. Core Payment Gateway/i).fill('E2E Test Auth Microservice');
    await page.getByPlaceholder(/https:\/\/github\.com\/org\/repo\.git/i).fill('https://github.com/org/auth-microservice.git');
    await page.getByRole('button', { name: 'Register Target' }).last().click();

    // Verify dialog closed and target added
    await expect(dialog).not.toBeVisible();
    await expect(page.getByRole('table').getByText('E2E Test Auth Microservice')).toBeVisible();

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

  test('Multi-viewport screenshots & performance check on /estate', async ({ page }) => {
    const screenshotDir = path.join(process.cwd(), 'public', 'screenshots', 'viewports');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }

    const viewports = [
      { name: 'desktop', width: 1440, height: 900, file: 'screen-11-estate-1440.png' },
      { name: 'laptop', width: 1280, height: 720, file: 'screen-11-estate-1280.png' },
      { name: 'mobile', width: 390, height: 844, file: 'screen-11-estate-390.png' },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/estate');
      await expect(page.getByRole('heading', { name: /Cryptographic Estate Console/i })).toBeVisible();

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
