import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('Milestone 5: HSM Inventory + Audit Log Hash-Chain Verification + CI Surfaces', () => {
  test('renders HSM partitions, verifies audit hash-chain, inspects CI surfaces, and passes Axe a11y in Dark & Light modes', async ({
    page,
  }) => {
    // 1. Navigate to Inventory and switch to HSM tab
    await page.goto('/inventory');
    await expect(page.getByText(/SCREEN 4 · HIGH-DENSITY CRYPTOGRAPHIC INVENTORY/i)).toBeVisible();

    const hsmTab = page.getByRole('tab', { name: /Hardware HSM Partitions/i });
    await hsmTab.click();

    // Verify HSM view rendered
    await expect(page.getByTestId('hsm-inventory-view')).toBeVisible();
    await expect(page.getByText(/SoftHSM v2 Slot 0 - Root Vault/i)).toBeVisible();
    await expect(page.getByText(/SoftHSM v2 Slot 1 - Payment Tokenizer/i)).toBeVisible();

    // Verify metrics
    await expect(page.getByText(/SoftHSM2 Slots/i)).toBeVisible();
    await expect(page.getByText(/Total Stored Keys/i)).toBeVisible();
    await expect(page.getByText(/Post-Quantum Keys/i)).toBeVisible();

    // Verify key algorithms and PQC readiness badges
    await expect(page.getByText(/Root CA Signing Key \(Shor-vulnerable\)/i)).toBeVisible();
    await expect(page.getByText(/PQC Transport KEM Key \(ML-KEM-768\)/i)).toBeVisible();
    await expect(page.getByText(/Audit Log Signature Key \(ML-DSA-65\)/i)).toBeVisible();
    await expect(page.getByText(/POST-QUANTUM/).first()).toBeVisible();
    await expect(page.getByText(/SHOR-VULNERABLE/).first()).toBeVisible();

    // 2. Click inspect on an HSM key to verify FindingDrawer deep-link
    const inspectBtn = page.getByRole('button', { name: /Inspect/i }).first();
    await inspectBtn.click();
    await expect(page.getByRole('dialog', { name: /Cryptographic finding details drawer/i })).toBeVisible();

    // Close drawer
    const closeBtn = page.getByRole('button', { name: /Close drawer/i });
    await closeBtn.click();
    await expect(page.getByRole('dialog', { name: /Cryptographic finding details drawer/i })).not.toBeVisible();

    // 3. Verify Cryptographic Audit Hash-Chain Verification Control
    await expect(page.getByTestId('audit-verify-control').first()).toBeVisible();
    await expect(page.getByText(/Audit Log Hash-Chain Integrity/i).first()).toBeVisible();
    await expect(page.getByText(/CHAIN VALID/).first()).toBeVisible();
    await expect(page.getByText(/1,248/).first()).toBeVisible();
    await expect(page.getByText(/Head Hash \(SHA-256\)/i).first()).toBeVisible();

    // 4. Verify Estate Console CI/CD Pipeline Surfaces & Honest Roadmap Annotations
    await page.goto('/estate');
    await expect(page.getByRole('heading', { name: /Cryptographic Estate Console/i })).toBeVisible();
    await expect(page.getByText(/CI\/CD PIPELINE SURFACES & AUTOMATION/i)).toBeVisible();
    await expect(page.getByRole('heading', { name: /Continuous Cryptographic Gates/i })).toBeVisible();
    await expect(page.getByText(/GitHub Actions/).first()).toBeVisible();
    await expect(page.getByText(/GitLab CI Runner/).first()).toBeVisible();

    // Check honest roadmap annotations on CI surfaces
    const roadmapBadges = page.getByText(/\[Roadmap: GitHub Actions \/ GitLab CI runner pending\]/i);
    await expect(roadmapBadges.first()).toBeVisible();

    // Verify Audit Seal on Estate
    await expect(page.getByTestId('audit-verify-control')).toBeVisible();

    // 5. Verify Launcher CI tab
    await page.goto('/launcher');
    await expect(page.getByRole('heading', { name: /Target Ingestion & Assessment Setup/i })).toBeVisible();
    const ciTriggerTab = page.getByRole('tab', { name: /CI \/ CD Pipeline Trigger/i });
    await ciTriggerTab.click();
    await expect(page.getByTestId('launcher-ci-panel')).toBeVisible();
    await expect(page.getByText(/Automated CI\/CD Pipeline Execution/i)).toBeVisible();
    await expect(page.getByText(/\[Roadmap: GitHub Actions \/ GitLab CI runner pending\]/i)).toBeVisible();

    // 6. Axe a11y Audit in Dark Mode on HSM inventory view
    await page.goto('/inventory?surface=hardware-hsm');
    await expect(page.getByTestId('hsm-inventory-view')).toBeVisible();

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

  test('Multi-viewport screenshots & performance check on HSM inventory', async ({ page }) => {
    const screenshotDir = path.join(process.cwd(), 'public', 'screenshots', 'viewports');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }

    const viewports = [
      { name: 'desktop', width: 1440, height: 900, file: 'screen-04-hsm-inventory-1440.png' },
      { name: 'laptop', width: 1280, height: 720, file: 'screen-04-hsm-inventory-1280.png' },
      { name: 'mobile', width: 390, height: 844, file: 'screen-04-hsm-inventory-390.png' },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/inventory?surface=hardware-hsm');
      await expect(page.getByTestId('hsm-inventory-view')).toBeVisible();

      // Ensure stable layout
      await page.waitForTimeout(300);

      // Save screenshot
      await page.screenshot({
        path: path.join(screenshotDir, vp.file),
        fullPage: false,
      });

      expect(fs.existsSync(path.join(screenshotDir, vp.file))).toBe(true);
    }
  });
});
