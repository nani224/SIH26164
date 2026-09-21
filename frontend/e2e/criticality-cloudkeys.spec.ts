import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('M5: Business Criticality & Cloud KMS Keys (SCR-04 Ext)', () => {
  test('operates criticality modal, CSV import re-ranking, and cloud keys modal with a11y and shots', async ({ page }) => {
    await page.goto('/inventory');

    // 1. Verify Inventory Page Loaded
    await expect(page.getByRole('heading', { name: /Discovered Cryptographic Assets/i })).toBeVisible({ timeout: 15000 });

    // 2. Open Criticality Modal
    const critBtn = page.locator('#open-criticality-btn');
    await expect(critBtn).toBeVisible();
    await critBtn.click();

    // Verify Modal Header & Tabs
    await expect(page.getByText(/Business Criticality & Finding Re-ranking/i)).toBeVisible();
    await expect(page.getByText(/Criticality Rule Editor/i)).toBeVisible();

    // 3. Switch to CSV Import & Re-ranking Preview Tab
    const csvTabBtn = page.getByRole('button', { name: /CSV Import & Re-ranking Preview/i });
    await csvTabBtn.click();
    await expect(page.getByText(/Paste CSV Records/i)).toBeVisible();

    // 4. Fill CSV Textarea
    const csvTextarea = page.locator('#csv-textarea');
    await csvTextarea.fill('target-001,src/crypto/**,mission-critical,Payment Core,PCI-DSS,external\ntarget-002,src/docs/**,low,Docs,PUBLIC,internal');

    // 5. Verify Projected Re-ranking Impact Preview Table is displayed
    await expect(page.getByText(/Projected Finding Re-ranking Impact Preview/i)).toBeVisible();
    await expect(page.getByText(/Elevates findings in mission-critical & high paths/i)).toBeVisible();

    // 6. Confirm CSV Import & Re-ranking
    const confirmImportBtn = page.locator('#confirm-csv-import-btn');
    await expect(confirmImportBtn).toBeEnabled();
    await confirmImportBtn.click();

    // Verify Tab switches back to editor with rules
    await expect(page.getByText(/Criticality Rule Editor/i)).toBeVisible();

    // Close Criticality Modal via Close button
    await page.getByRole('button', { name: 'Close dialog' }).click();
    await expect(page.getByText(/Business Criticality & Finding Re-ranking/i)).not.toBeVisible();

    // 7. Open Cloud Keys Modal
    const cloudBtn = page.locator('#open-cloud-keys-btn');
    await expect(cloudBtn).toBeVisible();
    await cloudBtn.click();

    // Verify Cloud Keys Header, Roadmap Notice, and Keys
    await expect(page.getByText(/Cloud KMS Cryptographic Keys \(AWS KMS\)/i)).toBeVisible();
    await expect(page.getByText(/AWS KMS via LocalStack is actively supported in v1.0/i)).toBeVisible();
    await expect(page.getByText(/AES-GCM/i)).toBeVisible();
    await expect(page.getByText(/RSA_4096/i)).toBeVisible();
    await expect(page.getByText(/ROTATION OVERDUE/i).first()).toBeVisible();

    // 8. Real-browser Axe a11y Audit in Dark Mode (0 critical, 0 serious)
    const darkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const darkViolations = darkAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(darkViolations).toHaveLength(0);

    // 9. Real-browser Axe a11y Audit in Light Mode (0 critical, 0 serious)
    await page.getByLabel('Toggle visual theme').click({ force: true });
    await page.waitForTimeout(200);

    const lightAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const lightViolations = lightAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(lightViolations).toHaveLength(0);

    // Revert to dark theme
    await page.getByLabel('Toggle visual theme').click({ force: true });

    // 10. Multi-viewport Screenshots (1440x900, 1280x720, 390x844) x 2 themes
    const shotDir = path.join(process.cwd(), 'public', 'screenshots', 'm5-criticality-cloudkeys');
    if (!fs.existsSync(shotDir)) {
      fs.mkdirSync(shotDir, { recursive: true });
    }

    const viewports = [
      { name: '1440x900', width: 1440, height: 900 },
      { name: '1280x720', width: 1280, height: 720 },
      { name: '390x844', width: 390, height: 844 },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.waitForTimeout(200);

      // Dark theme screenshot
      await page.screenshot({
        path: path.join(shotDir, `m5-cloudkeys-dark-${vp.name}.png`),
        fullPage: false,
      });

      // Light theme screenshot
      await page.getByLabel('Toggle visual theme').click({ force: true });
      await page.waitForTimeout(200);
      await page.screenshot({
        path: path.join(shotDir, `m5-cloudkeys-light-${vp.name}.png`),
        fullPage: false,
      });

      // Revert back
      await page.getByLabel('Toggle visual theme').click({ force: true });
    }
  });
});
