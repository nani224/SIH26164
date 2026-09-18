# ECDAT Backend — Plan

## Status: Phases 0-3 complete, Phases 4-10 not started

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
- [ ] First DEV/HOLD split (Loop B1) — **not done**. Needs real,
      hand-labelled third-party projects (>=150 usages across 3 unseen
      projects); this session only built starter synthetic fixtures.
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
- [ ] Async/WS-driven progress — `POST /scans` is still synchronous
      (Phase 4)

## Phases 4-10
See the SIH26164 brief for the full phase list (real-time WS, rescore
performance budget, sandboxed ingest, engine improvements via Loop B1,
PQC catalog re-measurement, exports, security hardening). Not started.

## Next 3 tasks
1. Source and hand-label a real DEV/HOLD corpus (Loop B1) from 3+ unseen
   real projects to replace the synthetic starter fixtures with a
   meaningful measured floor, and extend the Python detector's coverage
   (ec.ECDH, hmac.HMAC object-oriented form, PEM/X.509 parsing) before
   adding a second language.
2. Phase 4: real-time WS scan progress backed by the real engine run
   (replacing the canned event sequence `/scans/{id}/events` still sends),
   batched at <=10 msg/s per the brief.
3. Phase 5: rescore performance budget (<200ms for 10,000 findings) now
   that findings live in a real (indexed) database — add a load test and
   an index on `FindingRecord.scan_id` if needed.
