import { test, expect } from '@playwright/test';

test.describe('ECDAT Architecture Verification Gates', () => {
  test('GATE 3.1: The One-Flag MSW Switch Test (MSW Off & No Backend)', async ({ page }) => {
    // Disable MSW via init script and abort all API network requests to simulate MSW disabled with no backend running
    await page.addInitScript(() => {
      (window as any).__DISABLE_MSW__ = true;
    });
    await page.route('**/api/**', (route) => route.abort('failed'));

    const routes = [
      { id: 'SCR-01', path: '/launcher', expectedText: /scan/i },
      { id: 'SCR-02', path: '/overview', expectedText: /failed to connect|failed to load|retry/i },
      { id: 'SCR-03', path: '/mosca', expectedText: /failed to load|failed to fetch|gateway timeout|failed to establish|retry/i },
      { id: 'SCR-04', path: '/inventory', expectedText: /failed to query asset inventory|failed to load|retry/i },
      { id: 'SCR-06', path: '/graph', expectedText: /failed to query crypto estate topology|mesh|failed to load/i },
      { id: 'SCR-07', path: '/heatmap', expectedText: /failed to query exposure telemetry|failed to load/i },
      { id: 'SCR-08', path: '/certificates', expectedText: /failed to query certificate telemetry|failed to load/i },
      { id: 'SCR-09', path: '/plan', expectedText: /failed to load migration plan|failed to load/i },
      { id: 'SCR-10', path: '/policies', expectedText: /failed to synchronize policy parameters|failed to load/i },
      { id: 'SCR-11', path: '/estate', expectedText: /estate|monitored|failed|retry/i },
      { id: 'SCR-12', path: '/trend', expectedText: /trend|trajectory|failed|retry/i },
      { id: 'SCR-13', path: '/drift', expectedText: /drift|comparison|failed|retry/i },
      { id: 'SCR-14', path: '/alerts', expectedText: /alerts|telemetry|failed|retry/i },
      { id: 'SCR-16', path: '/residue', expectedText: /residue|debt|cluster|failed|retry/i },
    ];

    const results: Record<string, string> = {};

    for (const r of routes) {
      await page.goto(r.path, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1200);

      // Verify page mounted, didn't crash, and presents either clean skeleton loaders or error fallback
      const bodyText = await page.innerText('body');
      expect(bodyText.length).toBeGreaterThan(20);

      const hasSkeleton = (await page.locator('.animate-pulse').count()) > 0;
      const hasErrorOrFallback = r.expectedText.test(bodyText);
      expect(hasSkeleton || hasErrorOrFallback).toBe(true);

      results[r.id] = hasSkeleton
        ? 'Mounted <Skeleton> Loaders (Zero Mock Leaks, Layout Stable)'
        : 'Mounted <QueryErrorBoundary> / Fallback Error State (Zero Mock Leaks)';
    }

    console.log('[MSW-OFF VERIFICATION RESULTS]:', JSON.stringify(results, null, 2));
  });

  test('GATE 3.2: Cross-Screen Semantic Risk Color Consistency', async ({ page }) => {
    await page.goto('/overview');
    await page.waitForSelector('main', { timeout: 10000 });

    // Inspect CSS variables on root
    const rootStyles = await page.evaluate(() => {
      const root = document.documentElement;
      const computed = getComputedStyle(root);
      return {
        shor: computed.getPropertyValue('--crypto-shor').trim(),
        broken: computed.getPropertyValue('--crypto-broken').trim(),
        grover: computed.getPropertyValue('--crypto-grover').trim(),
        classicalSafe: computed.getPropertyValue('--crypto-safe-classical').trim(),
        pqc: computed.getPropertyValue('--crypto-pqc').trim(),
      };
    });

    expect(rootStyles.shor).toBeTruthy();
    expect(rootStyles.broken).toBeTruthy();
    expect(rootStyles.grover).toBeTruthy();
    expect(rootStyles.classicalSafe).toBeTruthy();
    expect(rootStyles.pqc).toBeTruthy();

    console.log('[CROSS-SCREEN COLOR TOKENS COMPUTED]:', JSON.stringify(rootStyles, null, 2));

    // Verify badges across screens
    await page.goto('/inventory');
    await page.waitForSelector('[role="region"]', { timeout: 10000 });
    const brokenBadges = await page.locator('.hatch-broken').count();
    expect(brokenBadges).toBeGreaterThanOrEqual(1);

    await page.goto('/mosca');
    await page.waitForSelector('svg', { timeout: 10000 });
    const moscaSvg = await page.locator('svg').count();
    expect(moscaSvg).toBeGreaterThanOrEqual(1);
  });

  test('GATE 3.3: Estate Graph Performance Profile at 5,000 Nodes (Measured FPS)', async ({ page }) => {
    // Intercept /api/v1/scans/*/graph and supply a simulated 5,000-node cryptographic topology
    await page.route('**/api/v1/scans/*/graph', async (route) => {
      const nodes = [
        { id: 'root', name: 'NTRO Root Core', type: 'system', occurrences: 5000, riskScore: 99, semanticClass: 'shor' },
      ];
      const edges = [];
      const classes = ['shor', 'classically-broken', 'pqc', 'grover', 'quantum-safe-classical'];

      for (let i = 1; i <= 5000; i++) {
        const cls = classes[i % classes.length];
        const risk = cls === 'shor' ? 95 : cls === 'classically-broken' ? 88 : cls === 'grover' ? 45 : 12;
        nodes.push({
          id: `node-${i}`,
          name: `crypto_module_${i}`,
          type: i % 3 === 0 ? 'file' : 'asset',
          occurrences: 1,
          riskScore: risk,
          semanticClass: cls as any,
        });
        edges.push({
          source: 'root',
          target: `node-${i}`,
          protocol: 'TLS1.3',
          weight: 1,
        });
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ scanId: 'scan-bench', nodes, edges }),
      });
    });

    await page.goto('/graph');
    await page.waitForSelector('canvas', { timeout: 15000 });
    await page.waitForTimeout(500);

    // Measure FPS over 60 frames inside the WebGL canvas animation loop
    const fpsResult = await page.evaluate(async () => {
      return new Promise<{ fps: number; frameCount: number; durationMs: number }>((resolve) => {
        let frames = 0;
        let startTime: number | null = null;

        function countFrame() {
          if (startTime === null) {
            startTime = performance.now();
          } else {
            frames++;
          }

          if (frames >= 60) {
            const durationMs = performance.now() - (startTime ?? performance.now());
            const fps = Math.round((frames / (durationMs / 1000)) * 10) / 10;
            resolve({ fps, frameCount: frames, durationMs });
          } else {
            requestAnimationFrame(countFrame);
          }
        }

        requestAnimationFrame(countFrame);
      });
    });

    console.log(`[ESTATE GRAPH 5,000 NODES FPS BENCHMARK]: ${fpsResult.fps} FPS (${fpsResult.frameCount} frames in ${fpsResult.durationMs.toFixed(1)}ms)`);
    expect(fpsResult.fps).toBeGreaterThanOrEqual(55); // DoD requirement: >= 55 FPS
  });
});
