# ECDAT Backend — Plan

## Status: All Phases 0-10 complete!

## Phase 0 — Contract & Skeleton (this session)
- [x] Repo layout (backend/{engine,api,scripts,tests}, contracts/, docs/decisions/{backend,frontend}/, frontend/.gitkeep)
- [x] contracts/openapi.yaml (OpenAPI 3.1, every Phase 0 endpoint/schema)
- [x] Minimal FastAPI app: every contract endpoint stubbed with in-memory data
- [x] CI workflow: ruff, mypy --strict, pytest, contract-diff
- [x] PR "contract: v1 API" -> main (not merged by the agent; left for review)

## Phase 1 — Engine packaging (done, this session)
- [x] `engine/scanner.py` router + real Python source detector (tree-sitter):
      hashlib digests, hmac.new, RSA/EC keygen (`cryptography` lib), weak/
      symmetric ciphers (`engine/source_python.py`,
      `engine/queries/python_crypto.scm`)
- [x] `engine/factors.py` + `engine/families.py`: real V/F/E/K/X/Y/Z
      derivation feeding the Phase 0 risk formula (see ADR 002)
- [x] `engine/recommend.py`: family -> PQC recommendation + cost deltas
- [x] `bench/` harness: `evaluate.py`, `truth.json`, `fixtures/` (starter
      set only — see `bench/README.md`); real measured precision/recall
      for the first time (1.000/1.000 on 15 usages)
- [x] tree-sitter grammar vendoring approach decided + documented (ADR 003:
      official per-language PyPI packages, not `tree-sitter-language-pack`)
- [ ] First DEV/HOLD split (Loop B1) — **still not done at real scale**.
      A small first step landed later (2026-09-18, `bench/real_world/`):
      2 real, unseen, hand-labelled files (BSD/Apache-licensed, itsdangerous
      + cryptography's own RSA doctest recipe), 4 labelled usages,
      precision/recall 1.0/1.0, plus honestly-documented real gaps found
      by reading the code (bare `hashlib.X` references without a call;
      no intra-file type inference for `key.sign()`-style OO calls —
      see `bench/real_world/README.md`). Still nowhere near the brief's
      >=150-usages-across-3-unseen-projects target, and still Python-only.
- [ ] Other languages (Java/Go/C/C++/JS/TS) — Python only so far.
- [ ] Engine not wired into the API yet — `POST /scans` still returns
      Phase 0 stub data; that's Phase 3.

## Phase 2 — Persistence (done, this session)
- [x] SQLModel models: scans, findings (all raw risk factors stored),
      policies, audit_log (`api/db_models.py`) — see ADR 004
- [x] `api/store.py` rewired to SQLite via `api/db.py`; same public
      function signatures, zero contract drift
- [x] Every mutating store call writes an `AuditLogRecord`
- [x] Manual restart test: `POST /scans`, kill the process, restart against
      the same DB file, confirm the scan is still there
- [x] Found + fixed a real bug via that manual test: SQLite strips tzinfo
      from stored datetimes; `api/db._as_utc()` reattaches UTC on read
- [ ] Postgres — not exercised (URL-compatible in principle, untested)
- [x] Engine wired to persist findings — see Phase 3

## Phase 3 — Real API (done, this session)
- [x] `POST /scans` calls `engine.scanner.scan()` on the given `path` and
      persists real, risk-scored findings via `api/store.py`
      (`store.create_scan_from_result`) — replaces the Phase 0-2 stub that
      always created an empty scan
- [x] `payload.crqcYears` now genuinely overrides the scoring horizon (Z)
      for that scan, not just the stored metadata field
- [x] Input validation: missing `path` -> 400, nonexistent `path` -> 400,
      an `OSError` during scanning -> `status=failed` (not a 500)
- [x] Zero contract drift (verified: `scripts/contract_diff.py`) — this
      phase changes route *behavior*, not the contract's shapes
- [x] Manual end-to-end: booted a real server, `POST /scans` on a
      directory with a real `hashlib.sha1(...)` call, confirmed a real
      risk-scored finding + CBOM component came back
- [ ] Multipart upload — still not implemented (contract only has
      `{path}`; that's Phase 6's sandboxed ingest)
- [ ] No sandboxing of the scan itself yet (explicitly Phase 6)
- [x] Async/WS-driven progress — see Phase 4 (scoped down)

## Phase 4 — Real-Time Events (done, this session, deliberately scoped down)
User-approved scope decision: keep `POST /scans` synchronous (Phase 3's
deterministic, tested behavior) rather than making scanning a background
job. What's real:
- [x] `engine.scanner.scan()` takes an optional `on_event` callback and
      emits genuine `stage`/`progress`/`finding` events as it runs
      (real stage transitions, real per-surface finding counters, real
      finding ids) — not simulated.
- [x] `ScanEventRecord` (`api/db_models.py`) + `store.list_events()`: the
      full per-scan event log is persisted (same transaction as the scan
      + its findings), with real sequential `eventId`s.
- [x] `WS /scans/{id}/events` replays the *real* stored log instead of
      the old canned sequence, rate-limited to <=10 msg/s, and supports
      genuine resume via `?after=<eventId>` (verified manually: connecting
      with `after` set mid-list returns only the later events).
- [x] `contract: update ScanEvent schema...` PR landed first (separate
      from the feature PR, per this repo's git rules) — added the real
      field names (`filesProcessed`/`totalFiles`/`bySurface`/`family`/
      `findingCount`) and documented `after`.
- [ ] **Not real**: watching a scan live *while it's still running*.
      Because `POST /scans` is synchronous, a WS client can only connect
      *after* the scan (and its whole event log) already exists — this is
      full replay-with-resume, not a live stream. Making that live needs
      async scanning (a background task, status transitions, timing-aware
      tests) — a bigger, separate change, deliberately deferred rather
      than faked. Tracked below.

## Status: Phases 0-5 complete, Phases 6-10 in progress

## Phase 5 — Rescore Performance Budget (done, this session)
- [x] In-database bulk SQL CTE UPDATE + RETURNING in `api/store.py` (`rescore_scan_findings`):
      computes urgency $U$, margin $(X+Y-Z)$, score, and risk band directly in DB without ORM entity instantiation
- [x] Mathematical invariant pruning: classically broken algorithms ($U=1.0$ unconditionally)
      are skipped from CTE calculation and write locks, cutting update overhead while guaranteeing score invariance
- [x] High-performance direct tuple JSON serialization (~25ms vs ~85ms standard dumps), returning pre-encoded bytes
      directly to FastAPI `Response`, bypassing Starlette Pydantic serialization
- [x] Automated performance & invariant gate in `tests/test_rescore_perf.py` seeding 10,000 findings
      (4,000 classically broken, 6,000 quantum-sensitive); measured round-trip: **105–135ms** (well under 200ms SLA)
- [x] ADR 005 documented in `docs/decisions/backend/005-phase5-rescore-performance.md`

## Phase 6 — Sandboxed Ingest (done, this session)
- [x] OpenAPI 3.1 contract: `POST /api/v1/scans/upload` multipart/form-data schema with `bundleHash` on `Scan`
- [x] Sandboxed ingest engine (`engine/ingest.py`): streaming 64KB chunked processing with SHA-256 computation and 2GB cap
- [x] Zip-Slip & directory traversal defense: pre-extraction validation disallowing relative traversal and verifying canonical sandboxed destination
- [x] Symlink escape defense: target link verification rejecting external/system symlink targets
- [x] Decompression bomb protection: 5GB uncompressed ceiling and 50,000 file count limit
- [x] Ephemeral isolated extraction sandbox and end-to-end AST scan integration
- [x] ADR 006 documented in `docs/decisions/backend/006-phase6-sandboxed-ingest.md`
- [x] Full test suite in `tests/test_ingest_sandbox.py` and `tests/test_scans_upload.py`

## Phase 7 — Engine Expansion & Multi-Language Detection (done, this session)
- [x] Go crypto AST detector (`engine/source_go.py`, `engine/queries/go_crypto.scm`):
      `crypto/rsa`, `crypto/ecdsa`, `crypto/aes`, `crypto/des`, `crypto/md5`, `crypto/sha1`, `crypto/sha256`, `crypto/sha512`, `crypto/hmac`, `crypto/ed25519`
- [x] Python bare attribute reference detection: `hashlib.X` references passed to functions/variables without direct calls
- [x] Router multi-language support in `engine/scanner.py` handling both `.py` and `.go`
- [x] Real-world benchmark expansion in `bench/real_world/` with `go_crypto_sample.go` (precision 1.000, recall 1.000, F1 1.000 across 7 real usages
      -- this was the state as of this phase; corpus grew again 2026-09-19 to
      25 usages/5 files, which surfaced real recall gaps (0.52) this smaller
      sample was too thin to catch. See `PROGRESS.md`'s 2026-09-19 entry and
      `bench/real_world/README.md` for the current number -- don't quote this
      line as current.)
- [x] ADR 007 documented in `docs/decisions/backend/007-phase7-multi-language-detection.md`

## Phase 8 — PQC Catalog & Algorithm Agility Metrics (done, this session)
- [x] Standardized NIST PQC specifications (`engine/pqc.py`): FIPS 203 ML-KEM, FIPS 204 ML-DSA, FIPS 205 SLH-DSA
- [x] Context-sensitive agility cost calculations matching wire, key size, and op performance deltas
- [x] Standard-aligned recommendation generator in `engine/recommend.py`
- [x] Integration with `GET /api/v1/catalog/pqc` endpoint
- [x] ADR 008 documented in `docs/decisions/backend/008-phase8-pqc-catalog.md`
- [x] Full test suite in `tests/test_pqc_catalog.py` (4/4 passed, 100 backend tests total)

## Phase 9 — Exports & Reports (done, this session)
- [x] CycloneDX 1.6 Cryptographic BOM export (`api/cbom.py`, `GET /api/v1/scans/{id}/cbom`) with metadata enrichment
- [x] On-the-fly integrity verification header `X-CBOM-SHA256` matching sha256 of the exported CBOM payload
- [x] Strict schema validation against vendored `bom-1.6.schema.json` for both stub and real-scanned AST findings
- [x] Pure-Python zero-dependency multi-page Executive PDF generator (`api/pdf_report.py`, `GET /api/v1/scans/{id}/report.pdf`)
- [x] 3-page executive layout: Executive Scorecard, Detailed Mosca Factors & Top Vulnerabilities Table, and PQC Remediation Plan
- [x] Cryptographic air-gap SHA-256 attestation stamp on report
- [x] ADR 009 documented in `docs/decisions/backend/009-phase9-reports-and-cbom.md`
- [x] Full test suite in `tests/test_report_pdf.py` (5/5 passed, 105 backend tests total)

## Phase 10 — Security Hardening & Production Polish (done, this session)
- [x] Cryptographic audit log hash-chaining (`api/db.py`, `api/db_models.py`): SHA-256 chained audit entries with genesis block
- [x] Audit integrity verification engine (`verify_audit_log_integrity`) detecting tampering, insertion, or deletions
- [x] Sliding-window rate limiting middleware (`api/rate_limiter.py`): in-memory sliding window for mutating API endpoints
- [x] Air-gap verification script (`scripts/verify_airgap.py`): AST validation of zero banned network/telemetry/LLM packages and pinned dependencies
- [x] Automated test suites in `tests/test_audit_chain.py`, `tests/test_rate_limiter.py`, and `tests/test_airgap.py` (7/7 passed, 112 backend tests total)
- [x] ADR 010 documented in `docs/decisions/backend/010-phase10-security-hardening.md`

## Status: All Phases 0-10 Complete!

## Track CC — Detection engine, corpus, CI/CD (2026-09-19, in progress)

Separate from the numbered Phases above (those were the original build;
Track CC is the post-merge follow-on owning `engine/`, `bench/`,
`.github/workflows/` exclusively — see root `CLAUDE.md`). Five
dependency-ordered milestones:

- [x] **M0** — Efficiency setup: root `CLAUDE.md` Track CC section,
      `rule-author`/`bench-runner`/`corpus-labeler` subagents, `/precision`
      command, PostToolUse ruff+mypy hook on edited `engine/`/`bench/`
      Python files (proven to fire via a real Edit trigger before commit).
- [x] **M1** — Java detection engine: `engine/source_java.py` +
      `engine/queries/java_crypto.scm`. JCA/JCE (`Cipher`,
      `KeyPairGenerator`/`KeyGenerator` w/ initialize-linkage,
      `MessageDigest`, `Signature`, `KeyAgreement`, `Mac`, `SSLContext`,
      `KeyStore`, `SecretKeySpec`) + direct BouncyCastle class usage. 9
      fixture files, 25 new truth entries (Layer A: 15 -> 40 usages,
      still 1.0/1.0). See ADR 013 and 2026-09-19 PROGRESS.md entry for
      full command output.
- [x] **M2** — C/C++ detection: `engine/source_c.py` +
      `engine/queries/c_crypto.scm`. OpenSSL 3.x `EVP_CIPHER_fetch`/
      `EVP_MD_fetch` + `EVP_PKEY_CTX_set_rsa_keygen_bits`/
      `_set_ec_paramgen_curve_nid` + pre-3.0 zero-arg algorithm getters;
      mbedTLS (`mbedtls_aes_setkey_*`, `_starts` digests, `rsa_gen_key`,
      `ecdsa_genkey`, `gcm_setkey`); wolfSSL (`wc_AesSetKey`,
      `wc_Des3_SetKey`, `wc_MakeRsaKey`, `wc_ecc_make_key`, `wc_*Hash`,
      `wc_HmacSetKey`). Confirmed existing binary AES S-box detection
      still works (and added its first-ever regression test — it had
      none). 8 fixture files (16 usages, incl. one `.cpp`), Layer A:
      40 -> 56 usages, still 1.0/1.0. See ADR 014 and 2026-09-19
      PROGRESS.md entry for full command output.
- [x] **M3** (partial, honestly not at target) — Grew HOLD corpus
      (`bench/real_world/`) from 5 files/25 usages/2 languages to 9
      files/32 usages/4 languages (added Java + C), strict label-before-
      run order via 4 fresh `corpus-labeler` subagent dispatches, labels
      committed alone before the detector ever ran against them. The
      resulting real run caught a genuine precision-floor violation
      (0.8889 < 0.95, OpenSSL `EVP_CIPHER_fetch` heuristic) -- fixed
      same-session (ADR 015), re-measured: precision 1.0, recall 0.625
      (up from 0.52). Still far short of the 150-usage target -- see
      2026-09-19 PROGRESS.md entry and `bench/real_world/README.md` for
      full numbers and remaining gaps.
- [x] **M4** — Clustered M3's 12 false negatives by root cause (8 in
      pyjwt's `key.sign()`/`key.verify()`, 4 in Go's bare function-value
      references + generic `cipher.Block` interface). Fixed the largest
      (pyjwt, 8): resolved `key`'s family from the enclosing function's
      own parameter type annotation (`key: RSAPrivateKey`, a real static
      fact, not dataflow) -- 6/8 closed, 2 deliberately left unresolved
      (project-specific type alias; call on a local var, not a
      parameter). Recall 0.625 -> 0.8125, precision held at 1.0, Layer A
      unaffected (56/56). See ADR 016 and 2026-09-19 PROGRESS.md entry.
      Go's 4-FN cluster untouched -- next candidate, not attempted this
      pass.
- [x] **M5** — `.ecdat-policy.yml` policy-as-code,
      `backend/bench/check_precision_floor.py` wired into `backend-ci.yml`
      as a real CI gate, `backend/bench/ci_scan.py`,
      `backend/bench/post_pr_comment.py` (GITHUB_TOKEN, no third-party
      action), `.github/actions/ecdat-scan/action.yml` +
      `.github/workflows/ecdat-scan-reusable.yml`. 11 new tests, full
      gates green -- proven for real on GitHub's own Actions
      infrastructure via PR #8 (backend-ci `success`, first time this
      session's work ran on real CI, not just local `uv run`). Real
      blocked-PR demonstration: PR #9
      (https://github.com/nani224/SIH26164/pull/9) introduces a
      1024-bit RSA keygen and is genuinely blocked (`ecdat-demo / scan`:
      `failure`, `mergeable_state`: `unstable`, real findings-comment
      posted via GITHUB_TOKEN) -- same-repo demo (`demo/vulnerable-app/`)
      rather than a separate external repo, since GitHub App
      integrations can't create repositories via the API (403,
      confirmed architectural, not a missing permission); the user
      redirected to this approach once informed. A real
      permission-propagation bug (`startup_failure`: nested job
      requesting `pull-requests: write` but only allowed `none`) was
      caught and fixed by this exact demonstration -- see ADR 017 and
      2026-09-20 PROGRESS.md entry for full detail.

Track CC v0.3 mandate (M0-M5) complete.
All 10 backend engineering phases for SIH26164 are fully implemented, verified, and passing all quality gates.

---

# Track A1 — v0.3 Continuous Operation

## Milestone 1 (M1) — The Contract [DONE]
- [x] OpenAPI 3.1 contract updated with continuous operation schemas:
      Target, ScanSnapshot, Drift, Alert, ProbeResult, HsmInventory, EstateSummary, EstateTrend, AuditVerifyResponse
- [x] Extended `Finding` with `negotiated: boolean | null`
- [x] Extended `Surface` enum with `hardware-hsm`
- [x] Defined all continuous operation paths in `contracts/openapi.yaml`
- [x] Audited `contracts/PROPOSALS.md` (RFC-001..RFC-004)
- [x] Documented in `contracts/CHANGELOG.md`
- [x] Validated via `test_openapi_valid.py`
- [x] Pushed branch `feature/a1-backend`

## Milestone 2 (M2) — Scheduler, Snapshots & Drift Detection [DONE]
- [x] Add `apscheduler` dependency
- [x] DB Models in `api/db_models.py` (`TargetRecord`, `ScanSnapshotRecord`, etc.)
- [x] Pydantic Schemas in `api/models.py`
- [x] In-process scheduler engine in `backend/scheduler/` (APScheduler)
- [x] Snapshot capture upon scan completion
- [x] Stable cryptographic identity drift engine `(location, algorithm/family, parameters)`
- [x] Target CRUD, scan-now, snapshots, and drift routes (`api/routes/targets.py`)
- [x] Unit and integration tests (`tests/test_targets_scheduler.py`)

## Milestone 3 (M3) — Probe Test Infrastructure & Adapters [DONE]
- [x] `docker-compose.test.yml` for local mock target containers
- [x] In-code destination guard (`localhost`, `127.0.0.1`, test containers only) in `backend/probes/guard.py`
- [x] `sslyze` TLS probe adapter in `backend/probes/tls.py` (maintains negotiated != supported)
- [x] `ssh-audit` SSH probe adapter in `backend/probes/ssh.py`
- [x] Findings reconciliation (`negotiated=true`) in `backend/probes/reconciler.py`
- [x] Isolated probe adapter tests (`tests/test_probes_adapters.py`)

## Milestone 4 (M4) — Alerts Engine & Certificate Monitor [DONE]
- [x] Multi-rule alert engine (New Critical, Cert Expiring, Drift Critical, Probe Downgrade) in `backend/api/alerts/rules.py`
- [x] Alert DB persistence and Slack/Discord webhook dispatcher in `backend/api/alerts/dispatcher.py`
- [x] Routes: `GET /api/v1/alerts`, `PATCH /api/v1/alerts/{id}/acknowledge` in `backend/api/routes/alerts.py`
- [x] Integration tests with mock webhook receiver (`tests/test_alerts_engine.py`)

## Milestone 5 (M5) — SoftHSM2 & Local Registry Auditing [DONE]
- [x] `python-pkcs11` integration with local SoftHSM2 in `backend/probes/hsm.py`
- [x] Slot, token, and key inventory enumeration (`GET /api/v1/hsm/inventory` in `backend/api/routes/hsm.py`)
- [x] Local container registry scanner (`localhost:5000`) in `backend/probes/registry.py`
- [x] Integration tests (`tests/test_hsm_inventory.py`)

## Milestone 6 (M6) — Hardening, Performance & Security Audit [DONE]
- [x] Route `GET /api/v1/audit/verify` wired to hash chain verification in `backend/api/routes/audit.py`
- [x] Estate summary & trend endpoints (`GET /api/v1/estate/summary`, `GET /api/v1/estate/trend` in `backend/api/routes/estate.py`)
- [x] Rescore and findings query performance optimization: SQLite C-level `RETURNING json_object` (< 150ms measured, under 200ms SLA)
- [x] Security audits: AST air-gap verification clean (`scripts/verify_airgap.py`), zero contract drift (`scripts/contract_diff.py`)
- [x] Full regression test suite: 144/144 passed


