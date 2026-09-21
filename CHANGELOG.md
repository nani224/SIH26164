# Changelog

## v1.0.0 — Crypto Mass Conservation (CMC) & PS Gap Closure — 2026-09-21

The "Crypto Mass Conservation" release. ECDAT pairs detection with mass conservation:
measuring not just what was found, but mathematically accounting for what was unexplained
(crypto debt residue). Closes key problem-statement (PS) gaps including business criticality
reranking, cloud KMS key discovery (LocalStack), and cryptographic estate coverage.

### Track A1 — Coverage API, Debt Ledger, PS-Gap Closure

- **M1: Contract v1.0.0**: Added OpenAPI schemas for `CoverageCertificate`, `ArtifactCoverage`,
  `ResidueCluster`, `AssetCriticality`, `CloudKeyRecord`, and `EstateCoverage`.
- **M2: Coverage Persistence**: Persisted coverage certificates and per-artifact coverage
  with content-hash deduplication (`save_coverage`/`get_coverage_certificate`), ensuring
  reproducible coverage numbers and identical cluster IDs across scans. Latency budget
  met: p95 < 150ms.
- **M3: Debt Ledger State Machine**: Residue cluster lifecycle (`open` -> `promoted` | `excluded` | `accepted`)
  with tamper-evident SHA-256 audit chaining. Strict validation: exclusions require justification
  and owner; promoted clusters are terminal. Real-time alert rule `check_residue_rise`.
- **M4: Coverage in Drift & Trend**: Wired `coverageRatio` and `residueMass` through scan snapshots
  and calculate_drift(), tracking `coverageDelta` and `residueMassDelta`.
- **M5: Business Criticality Reranking**: Operator-managed `AssetCriticality` records translated
  into synthetic higher-priority `ContextWithGlob` policy entries, visibly adjusting K/E exposure
  and Mosca risk scores on subsequent scans without altering engine formula. Derivation of
  `internalFacingAssets`/`externalFacingAssets` in `EstateSummary`.
- **M6: Cloud Key Discovery**: Self-hosted AWS KMS probe via LocalStack (`backend/probes/cloud_kms.py`)
  with public key fingerprinting (`identityId`), finding join, allowlisted destination guard, and
  clean degradation. Azure Key Vault and GCP Cloud HSM documented under `[Roadmap]`.
- **M7: Hardening & Performance**:
  - Benchmark on 10k findings + coverage: p95 for coverage queries < 46ms (budget: 150ms);
    p95 for residue queries < 7ms (budget: 200ms).
  - Security scans: `bandit` (0 issues identified), `pip-audit` (1 package exception in ADR 017).

### Track CC/Engine — Residue Extractors, Attribution Calculus, Kill Tests & Benchmark

- **M1-M2: Rule-Independent Extractors**: Implemented 6 extractor classes (`tables`, `arx`, `entropy`,
  `bigint`, `framing`, `literals`) with zero imports from detection rules, detecting unmodelled crypto.
- **M3: Attribution Calculus & Conservation Invariant**: Mathematically verified
  $M_{\text{attributed}} + M_{\text{excluded}} + M_{\text{residue}} = M_{\text{total}}$ on all 33 corpus artifacts with zero units lost.
- **M4: Coverage Certificate & CBOM Embedding**: CycloneDX 1.6 CBOM export with embedded coverage certificate
  and SHA-256 run manifest, validated against strict JSON schema.
- **M5: Kill Tests K1–K4**:
  - **K1 Sensitivity**: 100.0% of known false negatives surfaced as residue (floor $\ge 90\%$).
  - **K2 Specificity**: 0.00% residue mass on benign artifacts (floor $\le 5.0\%$).
  - **K3 Non-Vacuity**: Disabling AES, SHA-256, and MD5 rules returned exact masses to residue; restoring returned exact baseline.
  - **K4 Directional Validity**: Closing 3 residue clusters dropped residue by 45.00 units and increased recall by 3 findings.
- **M6: Debt-Closure Loop**: `ecdat debt` CLI commands (`list`, `show`, `promote`, `exclude`, `accept`).
  End-to-end promotion proved exact 32.0 mass transfer.
- **M7: Detection Parity Across 6 Languages**: Expanded corpus to 339 usages across Java, C/C++, Python, Go, Rust, and C#.
  Added PE/Mach-O binary parsing and sandboxed Squashfs/CPIO firmware extraction with hostile-input hardening.
- **M8: Public Benchmark Suite**: Standalone `score.py` scoring tool, `PROTOCOL.md`, `RESULTS.md`, and `make benchmark`.

### Track A2/UI — Coverage Certificate, Residue Explorer & Proof Surfaces

- **M1: Coverage Certificate on Overview**: Integrated mass conservation bar (attributed / excluded / residue),
  ratio metric, 5-scan trend sparkline, and prominent residue review CTA banner.
- **M2-M3: Residue Explorer & Debt Workflow (Screen 16)**: Built `/residue` with cluster table, occurrence
  drawer, split Hex/Source range viewer, and modals for Promoting to Rule, Excluding (enforcing justification + owner),
  and Accepting residue.
- **M4: Coverage in Drift, Estate & Alerts**: Added coverage column to `/estate`, Coverage Shift card to `/drift`,
  and first-class `residue_rise` alerts to `/alerts`. 2-click traceability estate $\rightarrow$ drift $\rightarrow$ cluster.
- **M5: PS-Gap Surfaces**: Business Criticality modal with CSV upload, validation error preview, and live risk re-ranking preview;
  Cloud Keys modal with real LocalStack AWS KMS keys and honest `[Roadmap]` labeling for Azure and GCP.
- **M6: Proof Surfaces & Demo Tour v3**: Attestation modal with CBOM SHA-256 digest and verify action;
  Benchmark modal with transparent language breakdowns; 8-step, under-7-minute guided tour traversing the full story.
- **Verification Gates**: 84 unit tests passing; 8 Playwright E2E suites passing; 0 critical/serious axe violations across all 16 screens in both Light and Dark themes.

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
  defect — see `docs/decisions/backend/022-real-stack-verification.md`).
- 3 pre-existing Playwright tests assert on MSW-fixture-only literal
  strings and fail when run against the real backend instead of mocks —
  a test-authoring gap, not an application defect.
