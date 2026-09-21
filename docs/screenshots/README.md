# Screenshots

Canonical, documentation-worthy captures of the Cipher Observatory
frontend, one per screen (dark + light where both were captured):

- `overview.png` — Overview console
- `mosca-dark.png` / `mosca-light.png` — Mosca Quantum Risk Matrix
- `estate.png` — Continuous Estate Console
- `trend.png` — Estate Trend
- `drift.png` — Cryptographic Drift Analysis
- `alerts.png` — Security Alerts & Protocol Probes

These are not Playwright visual-regression baselines (this repo has no
`toHaveScreenshot()` usage) — they're a curated subset of the multi-
viewport captures the `e2e/*.spec.ts` suite writes to
`frontend/public/screenshots/` on every run (existence-checked only, not
pixel-diffed, and gitignored for that reason). Refresh these manually
after a meaningful UI change by copying the relevant file out of a fresh
local `pnpm test:e2e` run.
