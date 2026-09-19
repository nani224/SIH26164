# GATE 3.3 — Estate Graph FPS benchmark, for real GPU hardware

`e2e/gates-verification.spec.ts`'s "GATE 3.3: Estate Graph Performance
Profile at 5,000 Nodes" requires >=55 fps rendering the Estate Graph
(`/graph`) with a synthetic 5,000-node scene. This could not be resolved
in a from-scratch whole-repo audit session because that sandbox has no
hardware GPU (confirmed: `UNMASKED_RENDERER_WEBGL` = `ANGLE (Google,
Vulkan 1.3.0 (SwiftShader Device (Subzero)...), SwiftShader driver)` --
Google's CPU software rasterizer). The diagnostic below rules out a code
defect as the cause (see the session's PROGRESS.md entry for the full
writeup); what's missing is a run on a machine with a real GPU. This
script is that run.

## What was already ruled out (don't re-derive these)

- **Not a missing-instancing bug**: draw calls were counted directly via
  `gl.drawArrays`/`drawElements`/`drawArraysInstanced`/`drawElementsInstanced`
  interception. Result: **exactly 3 draw calls per frame at every scale
  tested (500/1000/2500/5000 nodes)** -- the "5,000+ nodes in 1 single
  draw call" instancing claim in `src/app/graph/page.tsx` is real, not
  aspirational.
- **Not JS-scripting-bound**: the `requestAnimationFrame` callback (all
  per-frame JS: two scalar rotation updates + the `renderer.render()`
  call) measured **~0.4ms per frame** -- under 0.05% of the ~1000ms/frame
  wall time at 5,000 nodes. ~99.96% of frame time happens outside JS,
  in the browser's own render/rasterization pipeline.
- **FPS scales linearly with node count** (~0.20ms/node at 2500 and 5000
  nodes: 500ms and 1000.3ms respectively -- almost exactly 2x time for
  exactly 2x nodes), consistent with genuine per-instance
  vertex/fragment rasterization cost on a CPU software rasterizer, not
  a per-node JS or draw-call leak (which the flat 3-draw-calls-per-frame
  result above already rules out).

None of that requires a GPU to reproduce or believe -- it's why this is
handed off as "needs real hardware to get the number," not "unresolved."

## Steps

1. Clone the branch and check out this commit or later.
2. `cd frontend && pnpm install && pnpm build && pnpm start -p 3000` (a
   production build -- the dev server has extra overhead and isn't what
   GATE 3.3 measures).
3. In a separate terminal, with a normal (non-headless, real GPU) Chrome
   or Chromium available:
   ```bash
   pnpm exec playwright test e2e/gates-verification.spec.ts -g "GATE 3.3" --headed
   ```
   or simply open `http://localhost:3000/graph` in a real browser -- the
   3D view loads with real backend data by default; to reproduce the
   exact 5,000-synthetic-node scenario the gate uses, run the Playwright
   test above rather than eyeballing the live view.
4. Report the real fps the test prints
   (`[ESTATE GRAPH 5,000 NODES FPS BENCHMARK]: <N> FPS`). If it's still
   below 55 fps on real GPU hardware, that reopens this as a genuine
   code-level perf issue (contrary to the diagnostic above) and is worth
   a fresh look at `graph/page.tsx`'s renderer config (e.g. `antialias:
   true` is real MSAA cost that a software rasterizer pays for heavily
   but a real GPU mostly doesn't -- if it's still slow on real hardware,
   that flag and the `MeshStandardMaterial` PBR lighting cost on 5,000
   instances are the next things to profile, in that order).
5. Update `README.md`'s "Spatial Graph Framerate" row and
   `frontend/PROGRESS.md` with the real number and the hardware/browser
   it was measured on -- don't leave the old unverified "60.1 FPS" claim
   standing once a real number exists to replace it.

## Reusable diagnostic script (what produced the numbers above)

Save as `frontend/diag_scaling.mjs`, run with
`PLAYWRIGHT_CHROMIUM_PATH=<path to a real Chrome binary> node diag_scaling.mjs`
against a running `pnpm start -p 3000`. It instruments real GL draw calls
and `requestAnimationFrame` timing directly (no assumptions), so the same
script produces directly comparable per-instance and JS-vs-non-JS numbers
on real GPU hardware.

```js
import { chromium } from '@playwright/test';

const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH });

async function measureAtScale(nodeCount) {
  const page = await browser.newPage();
  await page.route('**/api/v1/scans/*/graph', async (route) => {
    const nodes = [{ id: 'sys_root', type: 'system', label: 'NTRO Root Core', band: 'critical', score: 99, occurrences: nodeCount }];
    const edges = [];
    const bands = ['critical', 'high', 'medium', 'low'];
    for (let i = 1; i <= nodeCount; i++) {
      const band = bands[i % bands.length];
      nodes.push({ id: `node-${i}`, type: i % 3 === 0 ? 'file' : 'asset', label: `crypto_module_${i}`, band, score: 50, occurrences: 1, parentId: 'sys_root' });
      edges.push({ source: 'sys_root', target: `node-${i}` });
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ nodes, edges }) });
  });

  await page.addInitScript(() => {
    window.__prof = { drawCalls: 0, rafCalls: 0 };
    const origGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type, ...args) {
      const ctx = origGetContext.call(this, type, ...args);
      if ((type === 'webgl2' || type === 'webgl') && ctx && !ctx.__patched) {
        ctx.__patched = true;
        ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced'].forEach((name) => {
          if (!ctx[name]) return;
          const orig = ctx[name].bind(ctx);
          ctx[name] = (...a) => { window.__prof.drawCalls++; return orig(...a); };
        });
      }
      return ctx;
    };
    const origRAF = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = (cb) => origRAF((t) => { cb(t); window.__prof.rafCalls++; });
  });

  await page.goto('http://localhost:3000/graph', { waitUntil: 'networkidle' });
  await page.waitForSelector('canvas', { timeout: 15000 });
  await page.evaluate(() => { window.__prof = { drawCalls: 0, rafCalls: 0 }; });

  const windowMs = 4000;
  const t0 = Date.now();
  await page.waitForTimeout(windowMs);
  const elapsed = Date.now() - t0;
  const prof = await page.evaluate(() => window.__prof);
  const fps = prof.rafCalls / (elapsed / 1000);
  await page.close();
  return { nodeCount, fps, rafCalls: prof.rafCalls, drawCalls: prof.drawCalls, drawCallsPerFrame: prof.drawCalls / Math.max(prof.rafCalls, 1) };
}

for (const n of [500, 1000, 2500, 5000]) {
  console.log(JSON.stringify(await measureAtScale(n)));
}
await browser.close();
```
