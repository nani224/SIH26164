# ECDAT Backend — Progress

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
