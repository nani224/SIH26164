# ECDAT Frontend Master Plan & Milestones

Lead Product Designer & Frontend Engineer: Antigravity Agent
API Contract: `contracts/openapi.yaml`
Design Language: **Cipher Observatory** (Signals-intelligence lab instrument)

---

## Milestones & Acceptance Criteria

### Milestone 1: Loop F1 — Design System & Specimen
- [x] Initial contract `contracts/openapi.yaml` and type generation setup.
- [x] Next.js 15+ App Router skeleton with Tailwind CSS v4 CSS-first `@theme` tokens.
- [x] Self-contained OKLCH color system for dark ("Observatory Deep Void") and light ("Cipher Clean Room").
- [x] Strict cryptographic semantic classes (Shor, Broken + Hatch, Grover, Safe Classical, PQC, Needs Review).
- [x] Perceptual risk band ramp (Critical $\ge 60$, High $35-59$, Medium $15-34$, Low $< 15$).
- [x] Typography ramp: `IBM Plex Sans Condensed` for high-density UI + `JetBrains Mono` for hex/code/tabular nums.
- [x] Interactive `/specimen` page with theme switch, semantic badges, contrast pass, and dense data table.
- [x] 0 axe accessibility violations, full WCAG AA compliance.

### Milestone 2: Screen 1 — Scan Launcher
- [x] Drop zone supporting `.zip`, `.tar`, `.tar.gz`, ELF/PE/Mach-O binaries.
- [x] Policy selector and CRQC horizon ($Z$) slider ($5-15$ years, default 10).
- [x] Deterministic bundle hash preview (SHA-256).
- [x] Live WebSocket event stream with real counters (progress, stages, findings).

### Milestone 3: Screen 2 — Overview Console
- [x] Bento summary: Critical/High/Medium/Low band counts, HNDL-exposed count, Classically broken count.
- [x] Ingestion speed metrics (MB/s, files, bytes, prefilter skips).
- [x] Top-10 urgent risks card with spring animation on updates.
- [x] Global CBOM download action.

### Milestone 4: Screen 3 — Mosca Quantum Risk Matrix
- [x] Interactive 2D scatter matrix: $X$-axis $= X + Y$ (years), $Y$-axis $=$ Score ($0-100$).
- [x] Draggable vertical CRQC horizon line ($Z \in [5, 15]$) calling `/api/v1/scans/{id}/rescore`.
- [x] Animated re-banding and point translation.
- [x] Classically broken assets visibly remain fixed at $U = 1$.
- [x] Side drawer showing findings that changed band.

### Milestone 5: Screen 4 — High-Density Inventory
- [x] Virtualized table rendering 10,000+ rows at 60 fps (TanStack Virtual).
- [x] Columns: Algorithm, parameters/curves, surface, occurrences, worst band, confidence.
- [x] Faceted multi-select filters, keyboard shortcuts, saved views.

### Milestone 6: Screen 5 — Finding Drawer
- [x] Highlighted code snippet or hex byte-offset view.
- [x] Mathematical waterfall: $100 \times V \times F \times U \times E \times K = \text{Score}$.
- [x] Mosca parameters breakdown: $X, Y, Z, M = X + Y - Z$.
- [x] PQC recommendation with $\Delta \text{pkBytes}$, $\Delta \text{wireBytes}$, $\Delta \text{opMs}$.
- [x] Triage workflow with optimistic updates.

### Milestone 7: Screen 6 — Crypto Estate Graph (3D/2D)
- [x] System $\to$ File $\to$ Asset hierarchical graph.
- [x] Three.js WebGL mesh with bloom post-processing, $\ge 55$ fps.
- [x] Automatic 2D canvas fallback when WebGL2 is absent or `prefers-reduced-motion`.

### Milestone 8: Screen 7 & 8 — Heatmap & Certificate Timeline
- [x] Heatmap matrix: Attack Surface $\times$ Crypto Family.
- [x] Certificate expiry timeline plotted against $Z$ horizon.

### Milestone 9: Screen 9 & 10 — Migration Plan & Policy Editor
- [x] Grouped remediation sequence by business criticality and system exposure.
- [x] Policy rule creator with glob-based path matcher and live finding count.

### Milestone 10: Integration & Quality Gates
- [x] ⌘K / Ctrl+K Command Palette.
- [x] MSW mock suite loaded with authentic NTRO fixtures, switchable via `NEXT_PUBLIC_ENABLE_MSW`.
- [x] Zero type errors (`tsc --noEmit`), production bundle compiled under budget (`next build`).
