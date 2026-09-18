# ECDAT Backend — Plan

## Status: Phases 0-5 complete, Phases 6-10 pending

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
- [x] Real-world benchmark expansion in `bench/real_world/` with `go_crypto_sample.go` (precision 1.000, recall 1.000, F1 1.000 across 7 real usages)
- [x] ADR 007 documented in `docs/decisions/backend/007-phase7-multi-language-detection.md`

## Phases 8-10 Roadmap
- [ ] Phase 8: PQC Catalog & Algorithm Agility Re-measurement (standard NIST FIPS 203/204/205 specs and agility deltas)
- [ ] Phase 9: Exports & Reports (CycloneDX 1.6 CBOM export, PDF executive summary with real findings)
- [ ] Phase 10: Security Hardening & Production Polish (rate limiting, air-gap validation, audit log verification)

## Next 3 tasks
1. Phase 8: PQC Catalog standard FIPS 203/204/205 parameters and cost models.
2. Phase 9: CycloneDX 1.6 strict validation and multi-page executive PDF report generation.
3. Phase 10: Tamper-evident audit log hash-chaining and air-gap verification script.
