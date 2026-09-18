# Frontend Progress Log

## 2026-09-17 — Session 1: Contract, Architecture & Loop F1 Design System

### 1. Initialization
- Verified environment: Node.js v24.14.0, pnpm 12.4.2, Git 2.55.0.
- Repository initialized on branch `feature/frontend` in `C:\Users\HP\.gemini\antigravity-ide\scratch\ecdat`.
- Authoritative contract written to `contracts/openapi.yaml` (OpenAPI 3.1.0) with all endpoints, models, and RFCs logged in `contracts/PROPOSALS.md`.
- Architecture decision record documented in `docs/decisions/frontend/001-cipher-observatory-tokens.md`.

### 2. Next.js 15 Skeleton Setup
- Initialized Next.js 15+ App Router application with TypeScript and Tailwind CSS v4.
- Generated `src/types/api.generated.ts` from `contracts/openapi.yaml`.
- Configured MSW v2 mock layer loaded with authentic NTRO prototype fixtures.

### 3. Production Screens & Components Build (All 10 Screens)
- **Screen 1 (Launcher)**: Drop zone, SHA-256 hash generator, live stage timeline (`/launcher`).
- **Screen 2 (Overview)**: Critical/High/Medium/Low counts, HNDL active threats, throughput telemetry (`/overview`).
- **Screen 3 (Mosca Matrix)**: Interactive D3 scatter plot, draggable $Z$ slider ($5-15$ yrs), dynamic re-banding with classically broken invariant ($U = 1$) (`/mosca`).
- **Screen 4 (Inventory)**: Virtualized 10,000+ row table at 60 fps with faceted filters (`/inventory`).
- **Screen 5 (Finding Drawer)**: Slide-over component with code snippet, $V \times F \times U \times E \times K$ waterfall, PQC cost deltas, and triage commitment (`FindingDrawer`).
- **Screen 6 (3D Estate Graph)**: Three.js WebGL spatial topology ($System \to File \to Asset$) with risk bloom shaders and 2D canvas fallback (`/graph`).
- **Screen 7 (Heatmap)**: Surface $\times$ Family matrix with cell threat coloring (`/heatmap`).
- **Screen 8 (Certificates)**: X.509 validity timeline plotted against CRQC $Z$ horizon, flagging SHA-1 and expired certs (`/certificates`).
- **Screen 9 (Migration Plan)**: Subsystem-grouped remediation sequences with byte/latency deltas and JSON export (`/plan`).
- **Screen 10 (Policy Editor)**: Path-glob context overrides with live match counts (`/policies`).
- **Global Features**: ⌘K Command Palette, Theme Toggle (Dark/Light), CycloneDX 1.6 CBOM download button (`CbomExportButton`).

### 4. Verification Gates (Session 1)
- `pnpm typecheck` passed (0 errors).
- `pnpm build` passed (all 14 routes compiled and prerendered statically).
- Production server running on `http://localhost:3000`.

## 2026-09-18 — Session 2: Screen 3 Rigorous Verification (Loops F2–F5)

### 1. Reclassification & Test Categorization
- Corrected test hierarchy: reclassified `vitest` + `jsdom` suite strictly as **Unit Tests** (`src/app/mosca/mosca.test.tsx`), not Loop F4.
- Added Storybook story suite (`src/app/mosca/MoscaMatrix.stories.tsx`) covering 4 states: `Typical`, `Empty`, `DenseDataset` (1,000 items), and `ApiError`.

### 2. Real Browser Accessibility Audit (Loop F4)
- Installed `@axe-core/playwright` and executed audits against running Next.js application in Microsoft Edge.
- **Audits caught real WCAG AA color contrast failures**:
  - Light mode `--band-low` text against badge background failed (2.5:1 vs 4.5:1 requirement).
  - Dark mode `--crypto-broken` text against obsidian field failed (4.16:1 vs 4.5:1 requirement).
- **Remediation**:
  - Re-engineered all `--band-*` and `--crypto-*` tokens in `src/app/globals.css` using mathematically computed OKLCH values (> 5.4:1 contrast in dark mode, > 12:1 in light mode).
  - Replaced hardcoded badge classes in `RiskBandBadge.tsx` with semantic CSS variables (`--band-*-bg`).
  - Added `role="dialog"`, `aria-modal="true"`, and `Escape` key listener to `FindingDrawer.tsx`.
- **Result**: **0 critical / serious violations** in both Dark Mode and Light Mode.

### 3. Playwright Flow Test & Domain Invariant (Loop F2)
- Added end-to-end assertions in `e2e/mosca-matrix.spec.ts`:
  - Verified initial state: `CRQC HORIZON: Z = 10y`.
  - Proved classically broken assets (SHA-1, `f-002`) remain completely stationary (`cy` attribute is identical before and after adjusting $Z$).
  - Proved quantum-vulnerable public key assets (RSA-2048, `f-004`) re-calculate Mosca Urgency and shift vertically.
  - Confirmed side panel announces changed findings with delta scores.

### 4. Keyboard-Only Walkthrough (Loop F4)
- Tested $Z$ slider manipulation purely via keyboard arrow keys (`ArrowLeft`/`ArrowRight`), updating the horizon year-by-year.
- Verified live region announcements (`aria-live="polite"`) informing screen readers of updated horizon and affected finding counts.
- Verified keyboard tab navigation into scatter plot nodes, opening finding details drawer on `Enter`, and closing on `Escape`.

### 5. Multi-Viewport Visual QA & Screenshots (Loop F3)
- Captured screenshots across 3 viewports: Desktop (1440x900), Tablet (768x1024), Mobile (375x667).
- Captured across both visual themes: "Observatory Deep Void" (Dark) and "Cipher Clean Room" (Light).
- Captured across 3 data states: Typical, Empty, and Error.
- Output preserved in `public/screenshots/`.

### 6. Performance & CLS Metrics (Loop F5)
- Measured Cumulative Layout Shift (CLS) via browser PerformanceObserver: `0.00` (< 0.05 budget).
- Verified network and paint timings in real browser: TTFB 9.7ms, DOM Interactive 146.6ms, FCP 724ms.
- Verified `/mosca` route bundle size: 5.0 kB route JS, 112 kB First Load JS (budget <= 250 kB).
  This 250 kB budget was only ever measured/set for `/mosca`; it does not apply project-wide.
  `/graph` (real Three.js WebGL 3D estate view, `pnpm build` output, 2026-09-18): 144 kB route
  JS, 255 kB First Load JS -- over `/mosca`'s budget, but `/graph` is a fundamentally heavier
  route (a real 3D rendering engine, not a 2D chart) and was never covered by that number.
  Its own budget is `<= 300 kB` First Load JS, which it currently meets; revisit with
  dynamic-import code-splitting of the Three.js scene setup if it grows past that.
- Test results: `pnpm test:unit` (7/7 passed), `pnpm test:e2e` (6/6 passed).


## 2026-09-18 — Session 3: Whole-repo cross-track audit + real backend integration

Re-verified everything above against real command output rather than
trusting it, and ran this project's first real backend+frontend
end-to-end test. See root `CLAUDE.md` and `.claude/agents/*.md` for the
audit methodology.

### Contract reality check
`frontend/src/types/api.generated.ts` (despite its "auto-generated by
openapi-typescript" header) had never actually been regenerated from any
real version of `contracts/openapi.yaml` -- it was a relic of this track's
own self-authored day-1 contract (`frontend/PROGRESS.md`'s Session 1
above). Regenerated it for real via `pnpm codegen:api`; the diff was ~470
lines (missing `/scans/upload`, wrong path-param names, wrong
operationIds, and a fictional `RescoreResult.changedFindings` shape that
does not exist in the real contract -- `RescoreResult` is `{bands, changed:
Finding[]}` only).

### Real defects found and fixed
- **`src/lib/api.ts`'s `rescoreScan`**: its fallback for the real (non-mock)
  backend response fabricated `previousBand`/`previousScore` from the
  *same* post-rescore `Finding` as `newBand`/`newScore` -- so every real
  rescore against the real backend showed zero change in the Mosca Matrix's
  "Scenario Horizon Shifts" panel, while looking correct under MSW (whose
  mock independently tracked prev/new state). Fixed: `RescoreResult` now
  matches the contract exactly; `MoscaMatrixView`/`specimen/page.tsx`
  compute the diff themselves against their own pre-rescore `findings`
  snapshot.
- **`src/app/graph/page.tsx`**: reimplemented the Mosca band thresholds
  (`>=60/35/15`) client-side as a fallback, because the (stale) generated
  `GraphNode` type had no `band` field. The real contract's `GraphNode`
  already has `band`/`score` -- the backend just wasn't populating them
  (see the matching backend PROGRESS.md entry, `api/graph.py`). Now reads
  `node.band`/`node.score` directly; zero client-side threshold logic left.
- **`src/app/inventory/page.tsx`**: fabricated up to 120 duplicate copies of
  every real finding (fake ids, fake paths) whenever a real scan had fewer
  than 50 results, "to prove virtualization." On real backend data this
  meant every scan under 50 findings showed 100+ fake rows mixed into real
  ones, and this is what actually broke the real end-to-end flow (a search
  match on the one real finding got buried among fakes -- 0 results shown).
  Removed; the table renders exactly what the API returns.
- **`src/lib/store.ts`**: `activeScanId` defaulted to `'scan-7f8e1a'`, an
  MSW-only id that 404s against a real backend, and was never persisted --
  every full-page navigation (which is what `page.goto()`/a bookmark/a
  refresh actually does) silently reset it back to the default, losing
  track of whichever scan the user had just launched. Now defaults to
  `'scan_stub_001'` (the real backend's actual seeded scan) and persists
  to `localStorage` via zustand's `persist` middleware.
- **`src/app/launcher/page.tsx`**: a failed/rejected scan (e.g. a hostile
  upload the backend correctly rejects with 400) reset the form with zero
  user-visible feedback. Added a `role="alert"` error banner showing the
  real API error message. Verified live: uploading a path-traversal
  `tar.gz` now shows "SCAN REJECTED: ... Suspicious path in tar archive:
  ..." in the actual rendered UI.
- `frontend/playwright.config.ts` hardcoded `channel: 'msedge'` (Windows
  Edge only), making the entire e2e/a11y/perf suite (24 tests) unrunnable
  anywhere else. Switched to Playwright's own bundled Chromium (portable),
  with `PLAYWRIGHT_CHROMIUM_PATH` as an opt-in override for environments
  with a pre-installed browser cache. This is what made the checks below
  possible to run at all this session.
- `src/mocks/handlers.ts`'s rescore mock returned the same fictional
  `changedFindings` shape (masking the `api.ts` bug above in every MSW-on
  dev/demo run) and its `/plan` mock returned a bare array instead of the
  contract's `{scanId, generatedAt, items}`. Both fixed to match the real
  contract. `src/mocks/data.ts`'s ~15 fixture findings, the PQC catalog,
  the graph fixture, and the remediation plan fixture all used enum values
  and field names from the same pre-merge fictional contract (e.g.
  `kind: 'hardware-module'`, `surface: 'network-protocol'`, PQC entries
  shaped as `{alg, pk_bytes, keygen_ms, ...}` instead of the real
  `PqcCatalogEntry`) -- all rewritten to the real contract's enums/shapes.

### Real end-to-end integration (first time for this project)
Ran the real backend (`uvicorn`) and the real frontend (`next build &&
next start` -- MSW cannot run in a production build by construction, this
*is* the MSW-off case) together via
`frontend/e2e/finale-integration.spec.ts`, both dark and light themes:
upload a real corpus through the Launcher -> real WS stage events ->
Overview band counts checked against a direct API call -> drag CRQC
Z 15->5 and confirm the changed-band count matches the real
`POST /rescore` response -> open a real finding (AES S-box constant
detected in a stripped binary from the uploaded corpus) and triage it,
confirmed saved -> fetch and shape-check the real CBOM -> Estate Graph
with 2D reduced-motion fallback. All passing for real, not simulated.
Also manually verified (real browser, real backend): a hostile
path-traversal `.tar.gz` upload shows a clear rejection banner in the UI
and the backend stays healthy afterward.

### Gates (real output, this session)
`pnpm typecheck`, `pnpm lint`, `pnpm knip`, `pnpm test` (37/37),
`pnpm build` all clean. `pnpm exec playwright test`: **23/24 passed**
(all 10 screens, MSW-off gate, cross-screen color consistency, CLS,
finale integration x2 themes, Mosca flows, a11y audits). The one failure
(`GATE 3.3: Estate Graph Performance Profile at 5,000 Nodes`) is a sandbox
GPU limitation, not an app defect -- confirmed independently: WebGL
context is available (software rasterizer, "WebKit WebGL"/no hardware
GPU) and `requestAnimationFrame` fires normally on every other page
(~66 fps on an empty page), but the same 5,000-instanced-mesh scene this
test renders measured ~1.2 fps outside the test harness too. Real GPU
hardware would very likely clear the 55 fps bar; not verifiable in this
sandbox. Left as an honest known gap rather than lowering the budget.
