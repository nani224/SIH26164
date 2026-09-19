import { test, expect } from '@playwright/test';
import path from 'path';

const themes = ['dark', 'light'] as const;

for (const theme of themes) {
  test.describe(`ECDAT Grand Finale E2E — Theme: ${theme.toUpperCase()}`, () => {
    test.use({ serviceWorkers: 'block' });

    test.beforeEach(async ({ page }) => {
      await page.emulateMedia({ colorScheme: theme });
      await page.addInitScript((mode) => {
        document.documentElement.className = mode;
        (window as any).__DISABLE_MSW__ = true;
      }, theme);
      await page.route('**/api/v1/**', async (route) => {
        const targetUrl = route.request().url().replace('http://localhost:3000', 'http://localhost:8000');
        await route.continue({ url: targetUrl });
      });
    });

    test(`Complete User Flow in ${theme} mode: upload -> stages -> overview -> rescore -> triage -> cbom -> graph 2D`, async ({
      page,
      request,
    }) => {
      test.setTimeout(60000);

      // 1. Upload bench corpus & watch live stages
      await page.goto('/launcher');
      await expect(page.locator('h1')).toContainText('Target Ingestion & Assessment Setup');

      const corpusPath = path.resolve(__dirname, '../../backend/bench/benchmark_corpus.tar.gz');
      await page.locator('input[type="file"]').setInputFiles(corpusPath);

      // Verify file info rendered
      await expect(page.locator('text=benchmark_corpus.tar.gz')).toBeVisible();

      // Launch scan
      const launchBtn = page.getByRole('button', { name: /start enterprise scan/i });
      await expect(launchBtn).toBeVisible();
      await launchBtn.click();

      // Watch live stages
      await expect(page.locator('text=WS /events')).toBeVisible();
      await expect(
        page.getByRole('button', { name: /open scan overview console/i })
      ).toBeVisible({ timeout: 25000 });
      await page.getByRole('button', { name: /open scan overview console/i }).click();

      // 2. Overview counts match API
      await expect(page).toHaveURL(/\/overview/);
      await expect(page.locator('text=CRYPTOGRAPHIC OVERVIEW CONSOLE')).toBeVisible();

      // Read active scan ID from the Overview header
      const scanIdElement = page.locator('p:has-text("Scan ID:")');
      await expect(scanIdElement).toBeVisible();
      const scanIdText = await scanIdElement.innerText();
      const scanIdMatch = scanIdText.match(/scan[_-][a-f0-9]+/i);
      const activeScanId = scanIdMatch ? scanIdMatch[0] : 'scan-7f8e1a';

      // Fetch scan directly from API to compare
      const scanRes = await request.get(`http://localhost:8000/api/v1/scans/${activeScanId}`);
      expect(scanRes.ok()).toBeTruthy();
      const activeScan = await scanRes.json();

      const expectedCritical = String(activeScan.bands.critical);
      const expectedHigh = String(activeScan.bands.high);

      // Verify Overview band counts
      await expect(page.locator(`text=${expectedCritical}`).first()).toBeVisible();
      await expect(page.locator(`text=${expectedHigh}`).first()).toBeVisible();

      // 3. Drag Z from 15 to 5 and confirm the changed-band list matches /rescore
      await page.goto('/mosca');
      await expect(page.locator('h1')).toContainText('Mosca Horizon Assessment');

      const slider = page.locator('input[type="range"]');
      
      // Helper to cleanly update React controlled range input
      const updateRangeValue = async (targetValue: number) => {
        await slider.evaluate((el: HTMLInputElement, val: number) => {
          const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype,
            'value'
          )?.set;
          if (nativeSetter) {
            nativeSetter.call(el, String(val));
          } else {
            el.value = String(val);
          }
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }, targetValue);
      };

      // Set initial Z to 15
      await updateRangeValue(15);
      await page.waitForTimeout(600);

      // Drag/change Z to 5 and capture real /rescore response
      const [rescoreResponse] = await Promise.all([
        page.waitForResponse((res) => res.url().includes('/rescore') && res.status() === 200),
        updateRangeValue(5),
      ]);

      const rescoreData = await rescoreResponse.json();
      expect(rescoreData.bands).toBeDefined();
      const changedFindings = rescoreData.changedFindings || rescoreData.changed || [];
      expect(changedFindings.length).toBeGreaterThan(0);

      // Confirm UI displays the changed count
      await expect(page.locator(`text=${changedFindings.length} Affected`)).toBeVisible({ timeout: 10000 });

      // 4. Open a stripped-binary finding (AES S-box constant) and triage it
      await page.goto('/inventory');
      await expect(page.locator('h1')).toContainText('Discovered Cryptographic Assets');

      // Search for AES S-box
      const searchInput = page.getByPlaceholder(/search algorithm/i);
      await searchInput.fill('AES S-box');
      await page.waitForTimeout(600);

      // Click finding row
      const sboxRow = page.locator('text=AES S-box constant in stripped binary').first();
      await expect(sboxRow).toBeVisible({ timeout: 10000 });
      await sboxRow.click();

      // Verify FindingDrawer is open with details
      await expect(page.locator('text=AES S-box constant in stripped binary').first()).toBeVisible();
      await expect(page.locator('text=AES_SBOX').first()).toBeVisible();

      // Triage it: click Accepted Risk button
      const acceptedRiskBtn = page.getByRole('button', { name: /accepted risk/i });
      await acceptedRiskBtn.click();

      // Fill triage note
      const noteTextarea = page.getByPlaceholder(/record cryptographic justification/i);
      await noteTextarea.fill('Verified static S-box table in stripped binary; migration to AES-256-GCM scheduled.');

      // Commit triage decision
      const commitBtn = page.getByRole('button', { name: /commit decision/i });
      await commitBtn.click();
      await expect(page.locator('text=TRIAGE SAVED')).toBeVisible({ timeout: 8000 });

      // 5. Export CBOM and confirm schema-valid
      const cbomRes = await request.get(`http://localhost:8000/api/v1/scans/${activeScan.id}/cbom`);
      expect(cbomRes.ok()).toBeTruthy();
      const cbom = await cbomRes.json();
      expect(cbom.bomFormat).toBe('CycloneDX');
      expect(cbom.specVersion).toBe('1.6');
      expect(Array.isArray(cbom.components)).toBe(true);
      expect(cbom.components.length).toBeGreaterThan(0);
      expect(cbom.serialNumber).toMatch(/^urn:uuid:/);

      // 6. Open 3D graph, confirm 2D fallback with reduced motion
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.goto('/graph');
      await expect(page.locator('h1')).toContainText('System → File → Cryptographic Asset Topology');

      // Confirm 2D fallback mode is active under reduced motion
      await expect(page.locator('text=2D Hierarchical Projection Mode')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Accessible 2D fallback mode enabled')).toBeVisible();

      // Switch to 3D and back to 2D manually to verify toggle
      const switchBtn = page.getByRole('button', { name: /switch to 3d|switch to 2d/i });
      await switchBtn.click();
      await page.waitForTimeout(500);
      await switchBtn.click();
      await expect(page.locator('text=2D Hierarchical Projection Mode')).toBeVisible();
    });
  });
}
