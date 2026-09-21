import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('M4: Coverage in Drift, Estate, & Alerts Traceability E2E', () => {
  test('verifies coverage drop traceability from estate -> drift -> residue in <= 3 clicks', async ({ page }) => {
    // CLICK 1: Start at Estate Screen
    await page.goto('/estate');
    await expect(page.getByRole('heading', { name: /Cryptographic Estate Console/i })).toBeVisible({ timeout: 15000 });

    // Verify Coverage column in targets table
    await expect(page.getByRole('columnheader', { name: 'Coverage' })).toBeVisible();
    await expect(page.getByText('93.5%').first()).toBeVisible();
    await expect(page.getByText('RESIDUE').first()).toBeVisible();

    // Click on target-001's drift link (Click 1)
    const driftLink = page.locator('a[title="View drift for Core Payment Gateway"]');
    await expect(driftLink).toBeVisible();
    await driftLink.click();

    // Land on /drift?targetId=target-001
    await expect(page).toHaveURL(/.*\/drift\?targetId=target-001/);
    await expect(page.getByRole('heading', { name: /Cryptographic Drift Analysis/i })).toBeVisible();

    // CLICK 2: Verify Coverage Shift & Residue Warning Banner on Drift Screen
    await expect(page.getByText('Coverage Shift')).toBeVisible();
    await expect(page.getByText('-4.2%')).toBeVisible();
    await expect(page.getByText('+45.0 unexplained residue')).toBeVisible();

    const residueAlertBanner = page.getByTestId('drift-coverage-alert');
    await expect(residueAlertBanner).toBeVisible();
    await expect(residueAlertBanner.getByText(/Coverage dropped by 4.2% between snapshots/i)).toBeVisible();

    // Click "Review New Residue" (Click 2)
    const reviewResidueBtn = page.locator('#drift-to-residue-link');
    await expect(reviewResidueBtn).toBeVisible();
    await reviewResidueBtn.click();

    // Land on /residue?targetId=target-001
    await expect(page).toHaveURL(/.*\/residue\?targetId=target-001/);
    await expect(page.getByRole('heading', { name: /Residue Explorer & Debt Ledger/i })).toBeVisible();

    // CLICK 3: Inspect cluster in Residue Explorer (Click 3)
    const clusterCard = page.getByText('cluster-res-001').first();
    await expect(clusterCard).toBeVisible();
    await clusterCard.click();

    // Verify exact byte/source range preview is visible
    await expect(page.getByText(/Exact range match/i)).toBeVisible();
    await expect(page.getByText(/src\/crypto\/handshake\.c/i).first()).toBeVisible();

    // 4. Verify residue-rise alert on Alerts Screen
    await page.goto('/alerts');
    await expect(page.getByRole('heading', { name: /Security Alerts & Protocol Probes/i })).toBeVisible();
    await expect(page.locator('span', { hasText: /^residue rise$/i }).first()).toBeVisible();
    await expect(page.getByText(/Unexplained cryptographic residue rose by \+45\.0 units/i)).toBeVisible();
    const alertResidueLink = page.getByRole('link', { name: /Inspect Unexplained Residue Clusters/i }).first();
    await expect(alertResidueLink).toBeVisible();

    // 5. Axe accessibility in Dark Mode
    const darkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const darkViolations = darkAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(darkViolations).toHaveLength(0);

    // 6. Axe accessibility in Light Mode
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

    // Reset back to Dark Mode
    await themeBtn.click();
  });

  test('Multi-Viewport Screenshot generation for M4 Drift & Estate Coverage (1440x900, 1280x720, 390x844)', async ({ page }) => {
    const viewports = [
      { name: 'desktop-1440x900', width: 1440, height: 900 },
      { name: 'laptop-1280x720', width: 1280, height: 720 },
      { name: 'mobile-390x844', width: 390, height: 844 },
    ];

    const outDir = path.resolve(process.cwd(), 'public/screenshots/m4-drift-estate');
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true });
    }

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      // 1. Capture Drift Screen
      await page.goto('/drift?targetId=target-001');
      await expect(page.getByTestId('drift-coverage-alert')).toBeVisible({ timeout: 15000 });

      await page.screenshot({
        path: path.join(outDir, `drift-coverage-${vp.name}-dark.png`),
        fullPage: false,
      });

      // 2. Capture Estate Screen
      await page.goto('/estate');
      await expect(page.getByRole('columnheader', { name: 'Coverage' })).toBeVisible({ timeout: 15000 });

      await page.screenshot({
        path: path.join(outDir, `estate-coverage-${vp.name}-dark.png`),
        fullPage: false,
      });

      // Toggle to Light Mode
      const themeBtn = page.getByLabel('Toggle visual theme');
      await themeBtn.click();
      await page.waitForTimeout(300);

      // Light Mode Estate Screenshot
      await page.screenshot({
        path: path.join(outDir, `estate-coverage-${vp.name}-light.png`),
        fullPage: false,
      });

      // Light Mode Drift Screenshot
      await page.goto('/drift?targetId=target-001');
      await expect(page.getByTestId('drift-coverage-alert')).toBeVisible({ timeout: 15000 });
      await page.screenshot({
        path: path.join(outDir, `drift-coverage-${vp.name}-light.png`),
        fullPage: false,
      });

      // Reset to Dark Mode
      await themeBtn.click();
    }
  });
});
