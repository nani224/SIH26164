# Changelog

## v0.3.0-sih-finale — 2026-09-20

The "continuous operation" release. ECDAT moves from a one-shot scanner to
a system that watches a registered target unattended, catches drift
between scans, alerts on it, probes live infrastructure, and proves its
own audit trail hasn't been tampered with — all verified against a real
running stack (real backend, real frontend with MSW off, real Docker
containers for TLS/registry/HSM probing) rather than unit tests alone.

### Track CC — Detection engine, corpus, CI/CD

- Multi-language AST detection: Python, Java, Go, and C/C++ crypto usage
  detection via tree-sitter queries (M1–M2, M7).
- Real-world HOLD corpus grown to 56 hand-labelled usages across 14 real,
  unseen third-party files in 4 languages (M3, M6, M7) — labelled blind,
  before the detector was ever run against them, per the repo's own
  label-before-running discipline.
- Closed the largest known false-negative clusters: OpenSSL EVP
  cipher-context linkage, Python `key.sign()`/`key.verify()` OO calls,
  Go bare function references (M3, M4, M6).
- CI precision-floor gate (0.95) wired as a real GitHub Actions check,
  with a real blocked PR proving it fails red on a deliberate regression
  and passes green on revert (M5, PR #12); a reusable
  `ecdat-scan-reusable.yml` GitHub Action lets any consuming repository
  call ECDAT's scan-and-gate directly.
- Starter-fixture precision/recall: **1.000 / 1.000** (64 usages, 27
  files). Real-world HOLD: **0.9583 / 0.8214** (46 tp / 48 detected / 56
  truth) — honestly short of the brief's 150-usage target, not rounded up.

### Track A1 — Backend continuous operation

- Real APScheduler cron scanning: a registered target re-scans itself
  unattended on its configured schedule, proven via real wall-clock waits
  against a live server (P1).
- Real drift detection between scheduled scans (`added`/`resolved`/
  `changed`), with a real bug found and fixed along the way: two distinct
  findings on different lines of the same file collided under the old
  finding-identity check, which would have silently dropped a real new
  weak algorithm from `added[]` — fixed by including `location.line` in
  the identity tuple (P2/P4, `backend/api/store.py`).
- Real alert engine (new-critical, cert-expiring, drift, probe-downgrade)
  with real Slack/Discord webhook delivery, fail-closed under network
  errors (P4).
- Real live TLS probing (`sslyze`) reconciled against static findings,
  distinguishing `negotiated` from merely `supported` ciphers (P3).
- Real SoftHSM2/PKCS#11 key and slot inventory (P5).
- SHA-256 hash-chained tamper-evident audit log; `GET /audit/verify`
  proven to catch a real raw-SQL row tamper and identify the exact broken
  entry (P6).
- Rescore performance: 10,000 findings in 149.26ms cold / ~84ms warm,
  under the 200ms budget (P7).

### Track A2 — Frontend v0.3 screens

- Four new real screens: Continuous Estate Console (`/estate`), Estate
  Trend (`/trend`), Cryptographic Drift Analysis (`/drift`), Security
  Alerts & Protocol Probes (`/alerts`) — bringing the app to 15 real
  routes.
- Each screen built against the real v0.3 contract, with real interactive
  flows (tab filtering, finding-drawer triage, alert acknowledgement) and
  its own Axe accessibility test.

### Finale integration pass (this release)

Ran the project's first genuinely real end-to-end verification: real
backend + real frontend (MSW off) actually talking to each other through
the full scan → triage → export → drift → alert → probe → audit flow.
Found and fixed real bugs that unit tests alone had not caught:

- **`/estate/trend` aggregation bug**: averaging multiple same-day
  snapshots divided one day's *summed* weighted score by a single
  day-average finding count, producing scores as high as 400.0 (intended
  scale: 0–100). Fixed to average each snapshot's own weighted score
  across the day. Verified live: 400.0 → 62.9 on the same underlying rows.
- **`/specimen` accessibility gap**: the only route in the app with zero
  axe test coverage; a real scan against the live backend found a real
  `scrollable-region-focusable` (serious) violation — a horizontally
  scrollable findings table with no keyboard access. Fixed with
  `tabIndex`/`role`/`aria-label`; a permanent regression test now covers it.
- **`GET /findings` performance**: measured p50 710ms / p95 773ms on a
  10,000-finding scan's default (unfiltered) page load — far over the
  150ms budget — because every request materialized every finding for the
  scan into a full Pydantic object before pagination ran. Fixed with a
  SQL-level `LIMIT`/`OFFSET` fast path for the common unfiltered case:
  p50 8.34ms / p95 10.97ms after the fix.
- **Air-gap verification coverage gap**: `scripts/verify_airgap.py` never
  covered `probes/` or `scheduler/` — the entire v0.3 continuous-operation
  surface — so nothing had mechanically checked either directory's
  network behavior. Extended to enforce zero network imports in
  `api/`/`engine/`/`scheduler/` and a `probes.guard`-or-documented-
  exception rule for `probes/`; both new rules proven with real
  deliberately-introduced violations.
- **`postcss` HIGH CVEs** (CVE-2026-45623, CVE-2026-73646), pinned
  internally by Next.js's own dependency graph rather than the project's
  direct devDependency: fixed via a `pnpm.overrides` forcing every
  resolution to the patched version.
- **`cryptography` HIGH CVEs** (CVE-2026-69247, CVE-2026-69249,
  GHSA-537c-gmf6-5ccf): found real, confirmed unfixable today — `sslyze`
  (the real TLS probe library) hard-pins `cryptography<47`, and every fix
  lands at `>=47`. Documented as an accepted, upstream-blocked exception
  with an exposure assessment rather than worked around with an unverified
  version-compatibility gamble.

### Known Gaps (see README.md's Known Gaps & Roadmap for the full list)

- External-repo CI proof still blocked on a one-time human action.
- Real-world HOLD corpus (56 usages) is honest but short of the brief's
  150-usage target.
- No custom `api`/`web` container image was built or vulnerability-scanned
  in this pass (sandbox-specific Docker build limitation, not a product
  defect — see `docs/decisions/backend/021-g2-real-stack-verification.md`).
- 3 pre-existing Playwright tests assert on MSW-fixture-only literal
  strings and fail when run against the real backend instead of mocks —
  a test-authoring gap, not an application defect.
