# ECDAT Backend — Plan

## Status: Phase 0 complete, Phases 1-10 not started

## Phase 0 — Contract & Skeleton (this session)
- [x] Repo layout (backend/{engine,api,scripts,tests}, contracts/, docs/decisions/{backend,frontend}/, frontend/.gitkeep)
- [x] contracts/openapi.yaml (OpenAPI 3.1, every Phase 0 endpoint/schema)
- [x] Minimal FastAPI app: every contract endpoint stubbed with in-memory data
- [x] CI workflow: ruff, mypy --strict, pytest, contract-diff
- [x] PR "contract: v1 API" -> main (not merged by the agent; left for review)

## Phase 1 — Engine packaging (next)
- [ ] `engine/scanner.py` router + first real source detector (tree-sitter,
      start with Python `hashlib`/`cryptography` usage)
- [ ] `bench/` harness: make_fixtures.py, evaluate.py, truth.json
- [ ] Vendor tree-sitter grammars with SHA-256 pins
- [ ] First DEV/HOLD split committed per Loop B1 rules before any tuning

## Phase 2 — Persistence
- [ ] SQLModel models: scans, findings (all raw risk factors stored),
      policies, triage, audit_log
- [ ] Wire `api/store.py` to the database instead of in-memory dicts

## Phase 3 — Real API
- [ ] Replace stub responses with real engine/persistence calls
- [ ] CI fails on contract drift (already wired in Phase 0; keep enforcing)

## Phases 4-10
See the SIH26164 brief for the full phase list (real-time WS, rescore
performance budget, sandboxed ingest, engine improvements via Loop B1,
PQC catalog re-measurement, exports, security hardening). Not started.

## Next 3 tasks
1. Start Phase 1: `engine/scanner.py` + one real Python source detection
   rule, with a fixture + truth entry + failing test first (Loop B1 step 4).
2. Set up `bench/make_fixtures.py` and `bench/evaluate.py` so precision/
   recall can actually be measured (currently: no bench exists, no floor
   exists).
3. Replace `backend/api/store.py`'s in-memory dicts with SQLModel + SQLite
   (Phase 2), keeping the API contract unchanged (contract-diff must still
   pass).
