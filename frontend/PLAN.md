# ECDAT Frontend Master Plan & Milestones

Lead Product Designer & Frontend Engineer: Antigravity Agent
API Contract: `contracts/openapi.yaml`
Design Language: **Cipher Observatory** (Signals-intelligence lab instrument)

---

## Milestones & Acceptance Criteria

### Milestone 1: Loop F1 — Design System & Specimen
- [x] Initial contract `contracts/openapi.yaml` and type generation setup.
- [ ] Next.js 15+ App Router skeleton with Tailwind CSS v4 CSS-first `@theme` tokens.
- [ ] Self-contained OKLCH color system for dark ("Observatory Deep Void") and light ("Cipher Clean Room").
- [ ] Strict cryptographic semantic classes:
  - Shor-vulnerable (Ember Red)
  - Classically broken (Magenta-Violet + 45° diagonal hatch pattern)
  - Grover-weakened (Amber)
  - Quantum-safe classical (Steel Blue)
  - Post-quantum (Lattice Teal)
  - Needs review (Dashed hairline outline + warning indicator)
- [ ] Perceptual risk band ramp (Critical $\ge 60$, High $35-59$, Medium $15-34$, Low $< 15$).
- [ ] Typography ramp: `IBM Plex Sans Condensed` for high-density UI + `JetBrains Mono` for hex/code/tabular nums.
- [ ] Interactive `/specimen` page with theme switch, semantic badges, contrast pass, and dense data table.
- [ ] 0 axe accessibility violations, full WCAG AA compliance.

### Milestone 2: Screen 1 — Scan Launcher
- [ ] Drop zone supporting `.zip`, `.tar`, `.tar.gz`, ELF/PE/Mach-O binaries.
- [ ] Policy selector and CRQC horizon ($Z$) slider ($5-15$ years, default 10).
- [ ] Deterministic bundle hash preview (SHA-256).
- [ ] Live WebSocket event stream with real counters (progress, stages, findings).

### Milestone 3: Screen 2 — Overview Console
- [ ] Bento summary: Critical/High/Medium/Low band counts, HNDL-exposed count, Classically broken count.
- [ ] Ingestion speed metrics (MB/s, files, bytes, prefilter skips).
- [ ] Top-10 urgent risks card with spring animation on updates.
- [ ] Global CBOM download action.

### Milestone 4: Screen 3 — Mosca Quantum Risk Matrix
- [ ] Interactive 2D scatter matrix: $X$-axis $= X + Y$ (years), $Y$-axis $=$ Score ($0-100$).
- [ ] Draggable vertical CRQC horizon line ($Z \in [5, 15]$) calling `/api/v1/scans/{id}/rescore`.
- [ ] Animated re-banding and point translation.
- [ ] Classically broken assets visibly remain fixed at $U = 1$.
- [ ] Side drawer showing findings that crossed risk thresholds.

### Milestone 5: Screen 4 — High-Density Inventory
- [ ] Virtualized table rendering 10,000+ rows at 60 fps (TanStack Virtual).
- [ ] Columns: Algorithm, parameters/curves, surface, occurrences, worst band, confidence.
- [ ] Faceted multi-select filters, keyboard shortcuts, saved views.

### Milestone 6: Screen 5 — Finding Drawer
- [ ] Highlighted code snippet or hex byte-offset view.
- [ ] Mathematical waterfall: $100 \times V \times F \times U \times E \times K = \text{Score}$.
- [ ] Mosca parameters breakdown: $X, Y, Z, M = X + Y - Z$.
- [ ] PQC recommendation with $\Delta \text{pkBytes}$, $\Delta \text{wireBytes}$, $\Delta \text{opMs}$.
- [ ] Triage workflow with optimistic updates.

### Milestone 7: Screen 6 — Crypto Estate Graph (3D/2D)
- [ ] System $\to$ File $\to$ Asset hierarchical graph.
- [ ] Instanced Three.js mesh with bloom post-processing, $\ge 55$ fps at 5,000 nodes.
- [ ] Automatic 2D canvas/SVG fallback when WebGL2 is absent or `prefers-reduced-motion`.

### Milestone 8: Screen 7 & 8 — Heatmap & Certificate Timeline
- [ ] Heatmap matrix: Attack Surface $\times$ Crypto Family.
- [ ] Certificate expiry timeline plotted against $Z$ horizon.

### Milestone 9: Screen 9 & 10 — Migration Plan & Policy Editor
- [ ] Grouped remediation sequence by business criticality and system exposure.
- [ ] Policy rule creator with glob-based path matcher and live finding count.

### Milestone 10: Integration & Quality Gates
- [ ] End-to-end Playwright tests in both themes.
- [ ] Lighthouse CI score $\ge 95$ on Overview, Inventory, Finding Drawer.
