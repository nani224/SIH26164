# ECDAT Frontend — "Cipher Observatory"

Enterprise Cryptographic Discovery & Analysis Tool (ECDAT)
Smart India Hackathon PS SIH26164 (NTRO).

Interactive cryptographic intelligence console evaluating classical vulnerabilities, Mosca quantum horizons ($X + Y > Z$), and NIST FIPS 203/204/205 post-quantum migration pathways.

---

## Tech Stack
- **Framework**: Next.js 15+ (App Router, Turbopack, React 19)
- **Styling**: Tailwind CSS v4 with CSS-first `@theme` tokens in OKLCH
- **Type Generation**: `openapi-typescript` generating from `../contracts/openapi.yaml`
- **Mock Layer**: MSW v2 (Mock Service Worker) with authentic NTRO prototype fixtures
- **State Management**: Zustand
- **Virtualization**: `@tanstack/react-virtual` (60 fps on 10,000+ rows)
- **3D Estate Graph**: Three.js WebGL with 2D Canvas fallback
- **Charts & Math**: Custom D3 scales and SVG coordinate geometry

---

## Design System: "Cipher Observatory"

- **Visual Tone**: Signals-intelligence lab instrument (calm dark field, precise hairlines, danger-proportional glow, no generic SaaS gradients).
- **Themes**:
  - **Observatory Dark**: `oklch(0.12 0.015 250)` dark obsidian base, 1px precise hairlines (`oklch(0.26 0.02 250)`).
  - **Clean Room Light**: `oklch(0.97 0.008 245)` technical paper background, high-contrast borders.
- **Cryptographic Semantics**:
  - **Shor-vulnerable** (RSA, ECC, DH, X25519) $\to$ Ember Red (`oklch(0.64 0.23 25)`)
  - **Classically broken today** (MD5, SHA-1, DES, 3DES, RC4, ECB) $\to$ Magenta-Violet (`oklch(0.60 0.25 320)`) + **45° diagonal cross-hatch pattern** (`.hatch-broken`) + `[BROKEN]` textual tag
  - **Grover-weakened** (AES-128) $\to$ Amber (`oklch(0.76 0.18 75)`)
  - **Quantum-safe classical** (AES-256, SHA-2/3) $\to$ Steel Blue (`oklch(0.70 0.13 230)`)
  - **Post-quantum** (ML-KEM, ML-DSA, SLH-DSA) $\to$ Lattice Teal (`oklch(0.74 0.16 185)`)
  - **Needs review** (Confidence $< 0.75$) $\to$ Dashed hairline outline + badge (never color alone)

---

## 10 Production Screens & Routes

1. **Scan Launcher** (`/launcher`): Multi-target drop zone (`.zip`, `.tar`, ELF/PE/Mach-O binaries), SHA-256 bundle hash generator, policy picker, and live stage timeline from WebSocket events with real counters.
2. **Overview Console** (`/overview`): Real-time bento metrics (Critical, High, Medium, Low band counts, HNDL active exposure, classically broken count, MB/s ingestion throughput, top-5 urgent threats with direct click-to-drawer).
3. **Mosca Quantum Risk Matrix** (`/mosca`): Signature screen with 2D scientific scatter matrix ($X$-axis $= X + Y$, $Y$-axis $=$ Score), draggable vertical $Z$ CRQC horizon line ($5-15$ years), animated re-banding, and domain invariant proof that classically broken assets keep $U = 1$ and never change bands.
4. **High-Density Inventory** (`/inventory`): Virtualized 10,000+ item table running at 60 fps with faceted filters (Band, Family, Surface, Low-Confidence review), instant search, and saved views.
5. **Finding Drawer** (Slide-over component): Hex view and highlighted source line, evidence list, mathematical $100 \times V \times F \times U \times E \times K = \text{Score}$ waterfall, Mosca parameters, PQC recommendations with byte and latency deltas ($\Delta \text{pkBytes}$, $\Delta \text{wireBytes}$, $\Delta \text{opMs}$), and triage decision commitments.
6. **Crypto Estate Graph (3D)** (`/graph`): Spatial Three.js WebGL topology ($System \to File \to Asset$) with risk bloom shaders, camera focus, hover tooltips, and high-density 2D canvas fallback.
7. **Attack Surface Heatmap** (`/heatmap`): Attack Surface $\times$ Cryptographic Family matrix colored by worst threat score, drilling directly into inventory.
8. **Certificates Timeline** (`/certificates`): Discovered X.509 certificates plotted against the CRQC $Z$ horizon, flagging expired certificates and SHA-1 signatures.
9. **Remediation Plan** (`/plan`): Grouped by deployment subsystem, ordered by score, JSON remediation export, and Executive PDF action (marked `[Proposed]` per RFC-001).
10. **Policy Editor** (`/policies`): Glob path rules overriding exposure ($E$), criticality ($K$), shelf life ($X$), and migration time ($Y$) with live count of findings captured by each rule.
- **Global Features**: ⌘K / Ctrl+K Command Palette, Theme toggle, CycloneDX 1.6 CBOM download button everywhere a scan is displayed.

---

## Running Locally

### Prerequisites
- Node.js $\ge 18.18$ (tested on v24.14.0)
- pnpm $\ge 9.0$ (tested on v12.4.2)

### Quick Start
```bash
# 1. Install dependencies
pnpm install

# 2. Regenerate TypeScript types from contract
pnpm codegen:api

# 3. Start development server
pnpm dev
# Opens at http://localhost:3000
```

### Production Build
```bash
pnpm build
pnpm start -p 3000
```

### Quality Verification Gates
```bash
# Strict type check
pnpm typecheck

# Production build validation
pnpm build
```

---

## Environment Variables

Configure in `.env.local` or `.env`:

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend REST / WebSocket base URL |
| `NEXT_PUBLIC_ENABLE_MSW` | `true` | Set to `false` to turn off MSW and hit live Claude backend directly |
