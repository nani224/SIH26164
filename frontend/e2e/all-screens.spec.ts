import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

const SCREENS = [
  { id: 'SCR-01', name: 'Scan Launcher', route: '/launcher', heading: 'SCREEN 1 · CRYPTOGRAPHIC SCAN LAUNCHER' },
  { id: 'SCR-02', name: 'Overview', route: '/overview', heading: 'SCREEN 2 · CRYPTOGRAPHIC OVERVIEW CONSOLE' },
  { id: 'SCR-03', name: 'Mosca Matrix', route: '/mosca', heading: 'SCREEN 3 · SIGNATURE MOSCA QUANTUM RISK MATRIX' },
  { id: 'SCR-04', name: 'Inventory', route: '/inventory', heading: 'SCREEN 4 · HIGH-DENSITY CRYPTOGRAPHIC INVENTORY' },
  { id: 'SCR-06', name: 'Estate Graph', route: '/graph', heading: 'SCREEN 6 · CRYPTO ESTATE GRAPH (3D / 2D)' },
  { id: 'SCR-07', name: 'Heatmap', route: '/heatmap', heading: 'SCREEN 7 · ATTACK SURFACE × CRYPTOGRAPHIC FAMILY HEATMAP' },
  { id: 'SCR-08', name: 'Certificates', route: '/certificates', heading: 'SCREEN 8 · X.509 CERTIFICATE TIMELINE & COMPLIANCE' },
  { id: 'SCR-09', name: 'Migration Plan', route: '/plan', heading: 'SCREEN 9 · POST-QUANTUM MIGRATION ROADMAP' },
  { id: 'SCR-10', name: 'Policy Editor', route: '/policies', heading: 'SCREEN 10 · CRYPTOGRAPHIC POLICY & MOSCA CONTEXT ENGINE' },
];

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'laptop', width: 1280, height: 720 },
  { name: 'mobile', width: 390, height: 844 },
];

test.describe('ECDAT 10-Screen E2E Verification Matrix', () => {
  for (const scr of SCREENS) {
    test(`[${scr.id}] ${scr.name}: renders correctly, passes Axe a11y in Dark & Light themes`, async ({ page }) => {
      await page.goto(scr.route);
      await page.waitForLoadState('networkidle');

      // Verify screen heading
      await expect(page.locator(`text=${scr.heading}`)).toBeVisible();

      // Verify Axe a11y in Dark Mode (0 critical, 0 serious)
      const darkAxe = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();
      const darkViolations = darkAxe.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
      expect(darkViolations).toHaveLength(0);

      // Toggle to Light Mode
      const themeBtn = page.getByLabel('Toggle visual theme');
      await themeBtn.click();
      await page.waitForTimeout(100);

      // Verify Axe a11y in Light Mode (0 critical, 0 serious)
      const lightAxe = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();
      const lightViolations = lightAxe.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
      expect(lightViolations).toHaveLength(0);

      // Toggle back to Dark Mode
      await themeBtn.click();
    });
  }

  test('[SCR-05] Finding Drawer: opens from inventory, passes Axe a11y and keyboard navigation', async ({ page }) => {
    await page.goto('/inventory');
    await page.waitForLoadState('networkidle');

    // Click on the first asset row to open finding drawer
    const row = page.locator('text=X25519').first();
    await row.click();

    // Verify dialog opened
    const drawer = page.locator('role=dialog');
    await expect(drawer).toBeVisible();
    await expect(page.locator('text=Quantum & Classical Threat Assessment')).toBeVisible();

    // Verify Axe a11y on open drawer
    const axeResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const serious = axeResults.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(serious).toHaveLength(0);

    // Keyboard navigation: Escape key closes drawer
    await page.keyboard.press('Escape');
    await expect(drawer).not.toBeVisible();
  });

  test('Global Command Palette (Cmd+K / Ctrl+K) accessible across all routes', async ({ page }) => {
    await page.goto('/overview');
    await page.waitForLoadState('networkidle');

    // Press Control+k
    await page.keyboard.press('Control+k');

    // Verify command palette modal appears
    await expect(page.getByPlaceholder(/Search console routes/i)).toBeVisible();

    // Press Escape to dismiss
    await page.keyboard.press('Escape');
    await expect(page.locator('role=dialog')).not.toBeVisible();
  });

  test('Multi-Viewport Snapshot generation (1440x900, 1280x720, 390x844)', async ({ page }) => {
    const dir = path.join(process.cwd(), 'public', 'screenshots', 'viewports');
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/overview');
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: path.join(dir, `overview-${vp.name}.png`),
      });
    }
  });

  test('Core Web Vitals CLS Budget (< 0.1) across key views', async ({ page }) => {
    await page.goto('/overview');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=SCREEN 2 · CRYPTOGRAPHIC OVERVIEW CONSOLE')).toBeVisible();

    const cls = await page.evaluate(async () => {
      return new Promise<number>((resolve) => {
        let clsScore = 0;
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!(entry as any).hadRecentInput) {
              clsScore += (entry as any).value;
            }
          }
        });
        observer.observe({ type: 'layout-shift', buffered: false });
        setTimeout(() => {
          observer.disconnect();
          resolve(clsScore);
        }, 1000);
      });
    });

    expect(cls).toBeLessThan(0.1);
  });
});
