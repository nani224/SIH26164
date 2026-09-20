import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('Milestone 6: 7-Minute Guided Demo Tour Across All 14 Screens', () => {
  test('launches demo tour, steps through 14 screens, verifies FindingDrawer, and passes Axe a11y', async ({
    page,
  }) => {
    await page.goto('/overview');
    await expect(page.getByText(/SCREEN 2 · CRYPTOGRAPHIC OVERVIEW CONSOLE/i)).toBeVisible();

    // 1. Launch 7-Min Demo Tour from Header
    const tourBtn = page.getByRole('button', { name: /Start 7-Minute Guided Demo Tour/i });
    await expect(tourBtn).toBeVisible();
    await tourBtn.click();

    // Verify tour controller appears
    const tourController = page.getByRole('complementary', { name: /7-Minute Guided Demo Tour Controller/i });
    await expect(tourController).toBeVisible();
    await expect(page.getByText(/Step 1 of 14 · Screen 11/i)).toBeVisible();
    await expect(page.getByText(/Autonomous Telemetry & Cryptographic Estate/i)).toBeVisible();

    // Step 1 -> Step 2 (Trend)
    const nextBtn = page.getByRole('button', { name: /Next/i });
    await nextBtn.click();
    await expect(page.getByText(/Step 2 of 14 · Screen 12/i)).toBeVisible();
    await expect(page.getByText(/Dual-Axis Historical Risk & Critical Findings/i)).toBeVisible();

    // Step 2 -> Step 3 (Drift)
    await nextBtn.click();
    await expect(page.getByText(/Step 3 of 14 · Screen 13/i)).toBeVisible();
    await expect(page.getByText(/Two-Snapshot Differential Analysis/i)).toBeVisible();

    // Step 3 -> Step 4 (Alerts)
    await nextBtn.click();
    await expect(page.getByText(/Step 4 of 14 · Screen 14/i)).toBeVisible();
    await expect(page.getByText(/Active Downgrade Probes & Live Telemetry/i)).toBeVisible();

    // Step 4 -> Step 5 (Launcher)
    await nextBtn.click();
    await expect(page.getByText(/Step 5 of 14 · Screen 1/i)).toBeVisible();
    await expect(page.getByText(/Deterministic Target Ingestion/i)).toBeVisible();

    // Jump to Step 9 (FindingDrawer inspection)
    const stepSelector = page.getByRole('combobox', { name: /Jump to tour step/i });
    await stepSelector.selectOption('8'); // index 8 is Step 9
    await expect(page.getByText(/Step 9 of 14 · Screen 5/i)).toBeVisible();

    // Verify FindingDrawer opens on Step 9
    await expect(page.getByRole('dialog', { name: /Cryptographic finding details drawer/i })).toBeVisible();

    // Close FindingDrawer
    const closeDrawerBtn = page.getByRole('button', { name: /Close drawer/i });
    await closeDrawerBtn.click();
    await expect(page.getByRole('dialog', { name: /Cryptographic finding details drawer/i })).not.toBeVisible();

    // Jump to Step 14 (Policies)
    await stepSelector.selectOption('13'); // index 13 is Step 14
    await expect(page.getByText(/Step 14 of 14 · Screen 10/i)).toBeVisible();
    await expect(page.getByText(/Cryptographic Policy Rules & Glob Overrides/i)).toBeVisible();

    // 2. Axe a11y Audit in Dark Mode on Tour Controller
    const darkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const darkViolations = darkAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(darkViolations).toHaveLength(0);

    // 3. Toggle to Light Mode and Axe Audit
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

    // Switch back to Dark Mode and close tour via Escape
    await themeBtn.click();
    await page.keyboard.press('Escape');
    await expect(tourController).not.toBeVisible();
  });
});
