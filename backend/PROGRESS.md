# ECDAT Backend — Progress

## 2026-09-18 — Phase 2: Persistence

Replaced `api/store.py`'s in-memory dicts with SQLModel + SQLite
(`api/db.py`, `api/db_models.py`) per `PLAN.md`'s Phase 2 scope — see ADR
004. Every raw risk factor is stored as its own column (per the brief),
`Recommendation`/`Policy` nested data as JSON columns. Every mutating
store call now writes an `AuditLogRecord`. Routes switched from
`stub_data.*` to `store.*` for findings; `api/store.py`'s public function
signatures are unchanged from Phase 0/1, so the API contract is untouched
— `contract_diff.py` still reports zero drift.

Manual end-to-end verification (not just the test suite): booted a real
`uvicorn` server against a file-based SQLite DB, `POST /scans`, killed the
process, restarted it, re-fetched the scan — it was still there. This
caught a real bug: SQLite silently strips `tzinfo` from stored
`datetime`s, so `startedAt`/`finishedAt` lost their `Z` suffix after a
restart. Fixed in `api/db._as_utc()` (reattaches UTC on read) with a
regression test. See `docs/decisions/backend/004-phase2-persistence.md`
for the write-up — this is exactly the kind of bug an in-memory-only test
suite doesn't catch, which is why the manual restart check was worth doing.

### Gate output (real, run from `backend/`)

```
$ uv run ruff check .
All checks passed!

$ uv run mypy --strict .
Success: no issues found in 41 source files

$ uv run pytest --cov=api --cov=engine --cov=scripts --cov=bench --cov-report=term-missing --cov-fail-under=85
...
TOTAL                       1116     61    95%
Required test coverage of 85% reached. Total coverage: 94.53%
65 passed, 3 warnings in 3.23s

$ uv run python scripts/contract_diff.py
No contract drift.
```

### Manual verification

```
$ DATABASE_URL="sqlite:////tmp/phase2_test.db" uv run uvicorn api.main:app ...
$ curl -X POST .../api/v1/scans -d '{"path": "/tmp/persist-me"}'
  -> {"id": "scan_7c6b1e016d82", ..., "startedAt": "2026-09-18T00:23:52.606973Z"}
# killed the process, restarted uvicorn against the same DB file
$ curl .../api/v1/scans/scan_7c6b1e016d82
  -> {"startedAt": "2026-09-18T00:23:52.606973Z", ...}   # survived, Z intact after the fix
```

### Loops run

None of B1/B3-B6 apply. No Loop-B2-relevant formula change this phase
(only how factors reach storage, not the formula itself) — Phase 0's
`tests/test_risk_formula.py` still passes unchanged.

### BLOCKED items

None.

### Contract changes / PROPOSALS decisions

None — verified via `contract_diff.py`.

### Next 3 tasks

See `PLAN.md`: (1) Phase 3 — wire `engine.scanner.scan()` into
`POST /scans` so real findings actually get persisted, (2) a real
hand-labelled DEV/HOLD corpus (Loop B1), (3) Phase 4/5 real-time WS +
rescore performance budget now that findings live in an indexed DB.

## 2026-09-17 — Phase 1: Engine Packaging

Built a real Python detection engine per `PLAN.md`'s Phase 1 scope:
`engine/scanner.py` (walk + orchestrate), `engine/source_python.py` +
`engine/queries/python_crypto.scm` (tree-sitter detector: hashlib digests,
hmac.new incl. underlying-hash resolution, RSA/EC keygen via
`cryptography`, weak/symmetric cipher construction), `engine/families.py`
+ `engine/factors.py` (new V/F/E/K/X/Y/Z derivation feeding the Phase 0
formula — see ADR 002), `engine/recommend.py` (family -> PQC
recommendation). Added a `bench/` harness (`evaluate.py` + `truth.json` +
`fixtures/`) that produces the repo's first **real measured** number.

Explicitly not done this pass (see `PLAN.md`): the Loop B1 DEV/HOLD corpus
from real unseen projects (only synthetic starter fixtures exist), other
languages, and wiring the engine into the API (`POST /scans` still returns
Phase 0 stub data — that's Phase 3).

### Gate output (real, run from `backend/`)

```
$ uv run ruff check .
All checks passed!

$ uv run mypy --strict .
Success: no issues found in 38 source files

$ uv run pytest --cov=api --cov=engine --cov=scripts --cov=bench --cov-report=term-missing --cov-fail-under=85
...
TOTAL                        957     61    94%
Required test coverage of 85% reached. Total coverage: 93.63%
57 passed, 3 warnings in 2.91s

$ uv run python scripts/contract_diff.py
No contract drift.

$ uv run python bench/evaluate.py
precision=1.0 recall=1.0 f1=1.0
truth=15 detected=15 tp=15
```

This precision/recall is the **first real measured number in this repo**
(Phase 0's `CLAUDE.md` said "None yet"). It is Phase 1's small synthetic
starter fixture set (8 files, 15 usages) — not the brief's Layer A/B
corpus. See `bench/README.md` for why, and `tests/test_bench_evaluate.py`
for the regression floor this sets.

### Manual verification

Ran `engine.source_python.detect()` directly against a hand-written
snippet exercising all 6 rule branches (md5, hashlib.new, hmac.new+SHA-1,
RSA keygen with key_size kwarg, EC keygen with curve, AES/3DES ciphers)
and confirmed every field (family, function, key_size, curve,
underlying_hash_family) before writing the fixture set — see
`backend/LEARNINGS.md` for the tree-sitter API details confirmed this way.

### Loops run

None of B1/B3-B6 apply yet (no real corpus, no fuzz targets, no API
change, no perf surface, no new external-facing security surface). A
Loop-B2-style property check exists from Phase 0
(`tests/test_risk_formula.py`) and still passes unchanged since the
formula itself didn't change this phase — only what feeds it did.

### BLOCKED items

None.

### Contract changes / PROPOSALS decisions

None — Phase 1 doesn't touch `contracts/openapi.yaml` by design (verified
via `contract_diff.py`, unchanged from Phase 0).

### Next 3 tasks

See `PLAN.md` "Next 3 tasks": (1) a real hand-labelled DEV/HOLD corpus,
(2) Phase 2 persistence (SQLModel), (3) Phase 3 wiring the engine into
`POST /scans` + extending Python detection coverage.

## 2026-09-17 — Phase 0: Contract & Skeleton

Repo (`nani224/SIH26164`) was verified empty at session start (GitHub API:
0 branches, `size: 0`) despite the brief describing a pre-existing engine.
Built Phase 0 from scratch: repo skeleton, `contracts/openapi.yaml` (OpenAPI
3.1, 13 HTTP paths + 1 WS-documented path, 38 generated component schemas),
an in-memory FastAPI stub implementing every contract endpoint, and CI.

### Gate output (real, run from `backend/`)

```
$ uv run ruff check .
All checks passed!

$ uv run mypy --strict .
Success: no issues found in 26 source files

$ uv run pytest --cov=api --cov=engine --cov=scripts --cov-report=term-missing --cov-fail-under=85
...
Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
api/__init__.py                0      0   100%
api/cbom.py                   50      4    92%   42, 46, 54, 74
api/filtering.py              38      9    76%   29, 31, 33, 35, 39-40, 51, 53, 61
api/main.py                   20      0   100%
api/models.py                237      0   100%
api/pdf_stub.py                19      0   100%
api/routes/__init__.py         0      0   100%
api/routes/catalog.py           7      0   100%
api/routes/findings.py         12      0   100%
api/routes/health.py            7      0   100%
api/routes/policies.py         21      2    90%   16, 23
api/routes/scans.py            83      3    96%   96, 186, 188
api/store.py                   31      0   100%
api/stub_data.py               29      1    97%   343
engine/__init__.py              0      0   100%
engine/risk.py                  27      0   100%
scripts/__init__.py             0      0   100%
scripts/contract_diff.py       91     17    81%   84, 102, 104, 111, 113-114, 119, 125, 131-138, 142
--------------------------------------------------------
TOTAL                          672     36    95%
Required test coverage of 85% reached. Total coverage: 94.64%
33 passed, 3 warnings in 2.88s

$ uv run python scripts/contract_diff.py
No contract drift.
```

### Manual end-to-end check (real server, not just TestClient)

Booted `uv run uvicorn api.main:app` on 127.0.0.1:8123 and hit it with curl
+ a small Python `websockets` client:
- `GET /api/v1/health` -> 200, real JSON.
- `GET /api/v1/scans/scan_stub_001/findings` -> 200, real filtered/paginated JSON.
- `GET /api/v1/scans/scan_stub_001/cbom` -> 200, CycloneDX 1.6 JSON.
- `GET /api/v1/scans/scan_stub_001/report.pdf` -> 200, `content-type: application/pdf`;
  `file /tmp/report.pdf` confirmed: `PDF document, version 1.4, 1 page(s)`.
- `GET /api/v1/catalog/pqc` -> 200, real FIPS 203/204/205 reference entries.
- `WS /api/v1/scans/scan_stub_001/events` -> 7 frames received in order
  (stage, progress, stage, finding x2, stage, done), each with an `eventId`.
- `GET /openapi.json` -> 13 paths, 38 component schemas.

### Gates not yet applicable (no engine/bench/exports exist yet)

bench/evaluate.py (Layer A/B), HOLD set, bench/hostile_tests.py,
schemathesis, load test, air-gap run (no network calls exist to disable
yet — trivially true), full CBOM signing, security scanners (bandit/
semgrep/pip-audit/gitleaks/grype) — none run this session; nothing to
scan/measure yet beyond what ruff/mypy/pytest already cover.

### Contract changes / PROPOSALS decisions

Initial contract only — `contracts/CHANGELOG.md` 0.1.0-phase0 entry.
`contracts/PROPOSALS.md` created empty (no frontend proposals yet).

### Loops run

None of Loop B1-B6 apply yet (no detection engine, no persisted findings,
no load-bearing performance surface, no fuzz targets beyond what Phase 0
has). LOOP B2-style property tests were added early for `engine/risk.py`
(Hypothesis: score in [0,100], U non-decreasing in Y / non-increasing in Z,
classically-broken forces U=1 and a stable band regardless of Z,
rescore(original Z) reproduces the stored example score) since that
formula already exists — see `tests/test_risk_formula.py`. Not run to a
cap; there's only one small pure function to test right now.

### BLOCKED items

None. Everything attempted this session succeeded.

### Next 3 tasks

See `PLAN.md` "Next 3 tasks" (start of Phase 1: real `engine/scanner.py` +
one detection rule with fixture/truth/test; `bench/` harness; Phase 2
persistence wiring behind the existing contract).
