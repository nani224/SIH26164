# ECDAT Backend — Plan

## Status: Phases 0-1 complete, Phases 2-10 not started

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
1. Source and hand-label a real DEV/HOLD corpus (Loop B1) from 3+ unseen
   real projects to replace the synthetic starter fixtures with a
   meaningful measured floor.
2. Phase 2: replace `backend/api/store.py`'s in-memory dicts with SQLModel
   + SQLite, storing all raw risk factors, keeping the API contract
   unchanged (contract-diff must still pass).
3. Phase 3: wire `engine.scanner.scan()` into `POST /scans` (replacing the
   stub), and extend the Python detector to more of the brief's
   family/library list (ec.ECDH, hmac.HMAC object-oriented form, PEM/X.509
   parsing) before adding a second language.
