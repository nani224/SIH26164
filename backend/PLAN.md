# ECDAT Backend — Plan

## Status: Phases 0-2 complete, Phases 3-10 not started

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
- [ ] Engine still not wired to persist findings — `POST /scans` creates
      an empty scan (0 findings); that's Phase 3

## Phase 3 — Real API
- [ ] Replace stub responses with real engine/persistence calls
- [ ] CI fails on contract drift (already wired in Phase 0; keep enforcing)

## Phases 4-10
See the SIH26164 brief for the full phase list (real-time WS, rescore
performance budget, sandboxed ingest, engine improvements via Loop B1,
PQC catalog re-measurement, exports, security hardening). Not started.

## Next 3 tasks
1. Phase 3: wire `engine.scanner.scan()` into `POST /scans` (persisting
   real findings via `api/store.py` instead of an empty scan), and extend
   the Python detector's coverage (ec.ECDH, hmac.HMAC object-oriented
   form, PEM/X.509 parsing) before adding a second language.
2. Source and hand-label a real DEV/HOLD corpus (Loop B1) from 3+ unseen
   real projects to replace the synthetic starter fixtures with a
   meaningful measured floor.
3. Phase 4/5: real-time WS scan progress backed by the real engine run,
   and a `< 200ms for 10,000 findings` rescore budget test now that
   findings are in a real (indexed) database.
