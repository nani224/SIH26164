import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('M1: Coverage Certificate on Overview', () => {
  test('renders coverage certificate with mass conservation bar, ratio, and residue CTA', async ({ page }) => {
    await page.goto('/overview');

    // Verify card is visible
    const card = page.getByTestId('coverage-certificate-card');
    await expect(card).toBeVisible({ timeout: 15000 });

    // Verify title and ratio (93.5%)
    await expect(card.getByText(/Crypto Mass Coverage/i)).toBeVisible();
    await expect(card.getByText('93.5%')).toBeVisible();

    // Verify mass progressbar with accessible attributes
    const progressbar = card.getByRole('progressbar');
    await expect(progressbar).toBeVisible();
    await expect(progressbar).toHaveAttribute('aria-valuenow', '93.5');

    // Verify Mass Breakdown values
    await expect(card.getByText('Attributed').first()).toBeVisible();
    await expect(card.getByText('8,850')).toBeVisible();
    await expect(card.getByText('Excluded').first()).toBeVisible();
    await expect(card.getByText('500')).toBeVisible();
    await expect(card.getByText('Unexplained Residue')).toBeVisible();
    await expect(card.getByText('650')).toBeVisible();

    // Verify CTA and Residue text linking to Residue Explorer
    await expect(card.getByText(/7 unexplained crypto residue clusters detected in this scan/i)).toBeVisible();
    const cta = card.getByRole('link', { name: /Review Residue Ledger/i });
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute('href', '/residue');

    // Real-browser Axe a11y Audit in Dark Mode (0 critical, 0 serious)
    const darkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const darkViolations = darkAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(darkViolations).toHaveLength(0);

    // Toggle to Light Mode and Axe Audit
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

  test('Multi-Viewport Screenshot generation for M1 Coverage Certificate (1440x900, 1280x720, 390x844)', async ({ page }) => {
    const viewports = [
      { name: 'desktop-1440x900', width: 1440, height: 900 },
      { name: 'laptop-1280x720', width: 1280, height: 720 },
      { name: 'mobile-390x844', width: 390, height: 844 },
    ];

    const outDir = path.resolve(process.cwd(), 'public/screenshots/m1-overview');
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true });
    }

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/overview');
      await expect(page.getByTestId('coverage-certificate-card')).toBeVisible({ timeout: 15000 });

      // Capture Dark Mode
      await page.screenshot({
        path: path.join(outDir, `overview-coverage-${vp.name}-dark.png`),
        fullPage: false,
      });

      // Toggle to Light Mode
      const themeBtn = page.getByLabel('Toggle visual theme');
      await themeBtn.click();
      await page.waitForTimeout(300);

      // Capture Light Mode
      await page.screenshot({
        path: path.join(outDir, `overview-coverage-${vp.name}-light.png`),
        fullPage: false,
      });

      // Reset to Dark Mode for next iteration
      await themeBtn.click();
    }
  });
});
