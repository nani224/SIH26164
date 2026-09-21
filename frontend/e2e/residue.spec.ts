import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('Screen 16: Residue Explorer & Debt Workflow E2E (M2 & M3)', () => {
  test('renders cluster list, exact range preview, and operates debt workflow', async ({ page }) => {
    await page.goto('/residue');

    // 1. Verify Screen Header & Stats
    await expect(page.getByRole('heading', { name: /Residue Explorer & Debt Ledger/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Screen 16')).toBeVisible();
    await expect(page.getByText('Open Debt Mass:')).toBeVisible();

    // 2. Verify Cluster Cards
    await expect(page.getByText('cluster-res-001').first()).toBeVisible();
    await expect(page.getByText('cluster-res-002').first()).toBeVisible();
    await expect(page.getByText('cluster-res-003').first()).toBeVisible();

    // 3. Verify Detail View & Exact Range Code Preview
    await expect(page.getByText(/Firing Extractor Signals/i)).toBeVisible();
    await expect(page.locator('span', { hasText: 'constant_pool' }).first()).toBeVisible();
    await expect(page.getByText(/Exact range match/i)).toBeVisible();

    // 4. Test Debt Workflow: Exclusion Enforcement (Owner & Justification Required)
    const excludeBtn = page.getByRole('button', { name: /^Exclude Cluster$/i });
    await excludeBtn.click();
    await expect(page.getByText(/Exclude Cluster from Active Debt/i)).toBeVisible();

    const confirmExcludeBtn = page.locator('#confirm-exclude-btn');
    // Submit must be disabled initially
    await expect(confirmExcludeBtn).toBeDisabled();

    // Fill owner only -> still disabled
    await page.locator('#exclude-owner').fill('secops-lead');
    await expect(confirmExcludeBtn).toBeDisabled();

    // Fill justification -> now enabled
    await page.locator('#exclude-justification').fill('Verified non-cryptographic constant matrix');
    await expect(confirmExcludeBtn).toBeEnabled();

    // Click confirm exclusion
    await confirmExcludeBtn.click();
    await expect(page.getByText(/Cluster successfully updated to EXCLUDED/i)).toBeVisible();

    // 5. Test Debt Workflow: Promote to Rule Scaffold
    const promoteBtn = page.getByRole('button', { name: /^Promote to Rule$/i });
    await promoteBtn.click();
    await expect(page.getByText(/Generated Rule Scaffold/i)).toBeVisible();
    await expect(page.getByText(/ecdat-rule-cluster-/i)).toBeVisible();

    // 6. Real-browser Axe a11y Audit in Dark Mode (0 critical, 0 serious)
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

    // Reset back to Dark Mode
    await themeBtn.click();
  });

  test('Multi-Viewport Screenshot generation for Screen 16 Residue Explorer (1440x900, 1280x720, 390x844)', async ({ page }) => {
    const viewports = [
      { name: 'desktop-1440x900', width: 1440, height: 900 },
      { name: 'laptop-1280x720', width: 1280, height: 720 },
      { name: 'mobile-390x844', width: 390, height: 844 },
    ];

    const outDir = path.resolve(process.cwd(), 'public/screenshots/m2-residue');
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true });
    }

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/residue');
      await expect(page.getByRole('heading', { name: /Residue Explorer & Debt Ledger/i })).toBeVisible({ timeout: 15000 });

      // Capture Dark Mode
      await page.screenshot({
        path: path.join(outDir, `residue-explorer-${vp.name}-dark.png`),
        fullPage: false,
      });

      // Toggle to Light Mode
      const themeBtn = page.getByLabel('Toggle visual theme');
      await themeBtn.click();
      await page.waitForTimeout(300);

      // Capture Light Mode
      await page.screenshot({
        path: path.join(outDir, `residue-explorer-${vp.name}-light.png`),
        fullPage: false,
      });

      // Reset to Dark Mode for next iteration
      await themeBtn.click();
    }
  });
});
