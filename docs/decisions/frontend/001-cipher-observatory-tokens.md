# ADR 001: Cipher Observatory Design Tokens & Semantic Architecture

- **Status**: Accepted
- **Date**: 2026-09-17
- **Authors**: Antigravity Lead UI/UX Engineer

## Context
ECDAT serves intelligence analysts and security engineers at NTRO who analyze mission-critical cryptographic postures under intense operational pressure. A generic corporate SaaS theme (bright blues, high bloom, oversized padding) fails to convey precision, causes visual fatigue during multi-hour reviews, and obscures critical threat nuances.

Furthermore, cryptographic state cannot be communicated with generic warning colors alone. Different cryptographic attack vectors (Shor's quantum polynomial time algorithm vs Grover's quantum square root speedup vs classical pre-computation exploits) require mathematically precise and consistent visual distinction.

## Decision
We establish the **"Cipher Observatory"** design system:

1. **Color Model**:
   - All colors are expressed in `oklch()` for uniform perceptual lightness across hue boundaries.
   - Dark Mode ("Observatory Deep Void"): Base `oklch(0.12 0.015 250)`, Card `oklch(0.18 0.022 250)`, Hairline borders `oklch(0.26 0.02 250)`.
   - Light Mode ("Cipher Clean Room"): Base `oklch(0.97 0.008 245)`, Card `oklch(0.99 0.005 245)`, Hairline borders `oklch(0.86 0.015 245)`.

2. **Cryptographic Semantic Mapping**:
   - **Shor-vulnerable** (RSA, ECC, DH) $\to$ **Ember Red** (`oklch(0.62 0.23 25)`).
   - **Classically broken today** (MD5, SHA-1, DES, RC4, ECB) $\to$ **Magenta-Violet** (`oklch(0.58 0.25 320)`) + persistent 45-degree diagonal cross-hatch pattern.
   - **Grover-weakened** (AES-128) $\to$ **Amber** (`oklch(0.75 0.18 75)`).
   - **Quantum-safe classical** (AES-256, SHA-2/3) $\to$ **Steel Blue** (`oklch(0.68 0.12 230)`).
   - **Post-quantum** (ML-KEM, ML-DSA, SLH-DSA) $\to$ **Lattice Teal** (`oklch(0.72 0.16 185)`).
   - **Needs Review** (Confidence $< 0.75$) $\to$ **Dashed outline hairline** + warning label.

3. **Risk Bands (Perceptual Hierarchy)**:
   - Critical ($\ge 60$): Ember Crimson
   - High ($35-59$): Deep Orange
   - Medium ($15-34$): Amber
   - Low ($< 15$): Sage Mint

4. **Typography**:
   - Primary UI: Condensed humanist sans (`IBM Plex Sans Condensed` / `Inter Tight`) to maximize data density.
   - Data & Hex: `JetBrains Mono` with `font-variant-numeric: tabular-nums lining-nums`.

## Consequences
- Every badge, table row, chart node, and graph element shares identical cryptographic semantics across all 10 screens.
- Zero reliance on color alone for critical accessibility (hatch pattern for broken assets, dashed border for confidence review).
- Full WCAG AA compliance in both dark and light modes.
