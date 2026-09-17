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
- Test results: `pnpm test:unit` (7/7 passed), `pnpm test:e2e` (6/6 passed).

