import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

test.describe('M6: Proof Surfaces & Guided Demo Tour (SCR-02 Ext)', () => {
  test('operates demo tour, attestation proof verification, public benchmark, a11y, and screenshots', async ({ page }) => {
    await page.goto('/overview');

    // 1. Verify Overview Page Loaded
    await expect(page.getByText(/SCREEN 2 · CRYPTOGRAPHIC OVERVIEW CONSOLE/i)).toBeVisible({ timeout: 15000 });
    await expect(page.locator('#open-tour-btn')).toBeVisible();
    await expect(page.locator('#open-attestation-btn')).toBeVisible();
    await expect(page.locator('#open-benchmark-btn')).toBeVisible();

    // 2. Test Guided Demo Tour
    await page.locator('#open-tour-btn').click();
    await expect(page.getByText(/ECDAT v1.0 Guided Product Tour/i)).toBeVisible();
    await expect(page.getByText(/Step 1 of 8/i)).toBeVisible();
    await expect(page.getByText(/1. Blocked PR via CI Precision Gate/i)).toBeVisible();

    // Advance through steps
    const nextBtn = page.locator('#tour-next-btn');
    await nextBtn.click();
    await expect(page.getByText(/Step 2 of 8/i)).toBeVisible();
    await expect(page.getByText(/2. Unprompted Scheduled Scan/i)).toBeVisible();

    await nextBtn.click();
    await expect(page.getByText(/Step 3 of 8/i)).toBeVisible();
    await expect(page.getByText(/3. Drift Analysis with Coverage Drop/i)).toBeVisible();

    await nextBtn.click();
    await expect(page.getByText(/Step 4 of 8/i)).toBeVisible();
    await expect(page.getByText(/4. Residue Explorer & Byte-Level Inspection/i)).toBeVisible();

    await nextBtn.click();
    await expect(page.getByText(/Step 5 of 8/i)).toBeVisible();
    await expect(page.getByText(/5. Debt Workflow: Promote to Rule/i)).toBeVisible();

    await nextBtn.click();
    await expect(page.getByText(/Step 6 of 8/i)).toBeVisible();
    await expect(page.getByText(/6. Coverage Certificate Rises/i)).toBeVisible();

    await nextBtn.click();
    await expect(page.getByText(/Step 7 of 8/i)).toBeVisible();
    await expect(page.getByText(/7. Cryptographic Attestation & Evidence Proof/i)).toBeVisible();

    await nextBtn.click();
    await expect(page.getByText(/Step 8 of 8/i)).toBeVisible();
    await expect(page.getByText(/8. Public Benchmark & Honest Gaps/i)).toBeVisible();

    // Close tour
    await page.getByRole('button', { name: /Finish Tour/i }).click();
    await expect(page.getByText(/ECDAT v1.0 Guided Product Tour/i)).not.toBeVisible();

    // 3. Test Cryptographic Attestation Modal
    await page.locator('#open-attestation-btn').click();
    await expect(page.getByText(/Cryptographic Attestation & Evidence Proof/i)).toBeVisible();
    await expect(page.getByText(/CBOM 1.6 Cryptographic Digest/i)).toBeVisible();
    await expect(page.getByText(/Bound Coverage Certificate Evidence/i)).toBeVisible();

    // Verify digest
    const verifyBtn = page.locator('#verify-attestation-btn');
    await expect(verifyBtn).toBeVisible();
    await verifyBtn.click();

    // Verify confirmation alert appears
    await expect(page.getByText(/VERIFIED: Cryptographic digest matches CBOM 1.6 manifest/i)).toBeVisible();

    // Close Attestation modal via Close button
    await page.getByRole('button', { name: 'Close dialog' }).click();
    await expect(page.getByText(/Cryptographic Attestation & Evidence Proof/i)).not.toBeVisible();

    // 4. Test Public Benchmark Modal
    await page.locator('#open-benchmark-btn').click();
    await expect(page.getByText(/Public Cryptographic Benchmark & Empirical Validation/i)).toBeVisible();
    await expect(page.getByText(/Overall Precision/i)).toBeVisible();
    await expect(page.getByText(/95.83%/i)).toBeVisible();
    await expect(page.getByText(/Overall Recall/i)).toBeVisible();
    await expect(page.getByText(/82.14%/i)).toBeVisible();
    await expect(page.getByText(/Mean Mass Coverage/i)).toBeVisible();
    await expect(page.getByText(/94.8%/i)).toBeVisible();

    // Check language table entries
    await expect(page.getByRole('cell', { name: 'Rust', exact: true })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Go', exact: true })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Python', exact: true })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Java', exact: true })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'C / C++', exact: true })).toBeVisible();

    // Check honest weakness disclosure
    await expect(page.getByText(/Honest Weakness Disclosure & Zero-Hallucination Policy/i)).toBeVisible();
    await expect(page.getByText(/Why C\/C\+\+ recall is 76.0%:/i)).toBeVisible();

    // 5. Real-browser Axe a11y Audit in Dark Mode (0 critical, 0 serious)
    const darkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const darkViolations = darkAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(darkViolations).toHaveLength(0);

    // 6. Real-browser Axe a11y Audit in Light Mode (0 critical, 0 serious)
    await page.getByLabel('Toggle visual theme').click({ force: true });
    await page.waitForTimeout(200);

    const lightAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const lightViolations = lightAxe.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(lightViolations).toHaveLength(0);

    // Revert theme
    await page.getByLabel('Toggle visual theme').click({ force: true });

    // 7. Multi-viewport Screenshots (1440x900, 1280x720, 390x844) x 2 themes
    const shotDir = path.join(process.cwd(), 'public', 'screenshots', 'm6-proof-tour');
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
        path: path.join(shotDir, `m6-benchmark-dark-${vp.name}.png`),
        fullPage: false,
      });

      // Light theme screenshot
      await page.getByLabel('Toggle visual theme').click({ force: true });
      await page.waitForTimeout(200);
      await page.screenshot({
        path: path.join(shotDir, `m6-benchmark-light-${vp.name}.png`),
        fullPage: false,
      });

      // Revert back
      await page.getByLabel('Toggle visual theme').click({ force: true });
    }
  });
});
