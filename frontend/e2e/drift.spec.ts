import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('Screen 13: Cryptographic Drift Analysis E2E Verification', () => {
  test('renders drift page, executes tab filtering, opens finding drawer, and passes Axe a11y in Dark & Light themes', async ({
    page,
  }) => {
    await page.goto('/drift');

    // 1. Verify Screen Header & Summary Bento Cards
    await expect(page.getByRole('heading', { name: /Cryptographic Drift Analysis/i })).toBeVisible();
    await expect(page.getByText(/Added Assets/i)).toBeVisible();
    await expect(page.getByText(/Resolved Assets/i)).toBeVisible();
    await expect(page.getByText(/Changed Bands/i)).toBeVisible();
    await expect(page.getByText(/Net Risk Delta/i)).toBeVisible();

    // 2. Verify Sections & Content
    await expect(page.getByText(/Newly Added Cryptographic Assets/i)).toBeVisible();
    await expect(page.getByText(/Resolved \/ Remediated Assets/i)).toBeVisible();
    await expect(page.getByText(/Changed Severity Postures/i)).toBeVisible();
    await expect(page.getByText('X25519', { exact: true })).toBeVisible();

    // 3. Interactive Category Tabs
    const addedTab = page.getByRole('tab', { name: /^Added/i });
    await addedTab.click();
    await expect(page.getByText(/Newly Added Cryptographic Assets/i)).toBeVisible();
    await expect(page.getByText(/Resolved \/ Remediated Assets/i)).not.toBeVisible();

    const allTab = page.getByRole('tab', { name: /^All Drift/i });
    await allTab.click();
    await expect(page.getByText(/Resolved \/ Remediated Assets/i)).toBeVisible();

    // 4. Interactive Finding Drawer Integration
    const findingRow = page.getByLabel(/Inspect finding X25519/i);
    await findingRow.click();

    const drawer = page.getByRole('dialog');
    await expect(drawer).toBeVisible();
    await expect(page.getByText(/Quantum & Classical Threat Assessment/i)).toBeVisible();

    // Dismiss drawer with Escape
    await page.keyboard.press('Escape');
    await expect(drawer).not.toBeVisible();

    // 5. Axe a11y Audit in Dark Mode (0 critical, 0 serious)
    const darkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const darkViolations = darkAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(darkViolations).toHaveLength(0);

    // 6. Toggle to Light Mode and Axe Audit
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

  test('Multi-viewport screenshots & performance check on /drift', async ({ page }) => {
    const screenshotDir = path.join(process.cwd(), 'public', 'screenshots', 'viewports');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }

    const viewports = [
      { name: 'desktop', width: 1440, height: 900, file: 'screen-13-drift-1440.png' },
      { name: 'laptop', width: 1280, height: 720, file: 'screen-13-drift-1280.png' },
      { name: 'mobile', width: 390, height: 844, file: 'screen-13-drift-390.png' },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/drift');
      await expect(page.getByRole('heading', { name: /Cryptographic Drift Analysis/i })).toBeVisible();

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
