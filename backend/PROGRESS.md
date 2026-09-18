# ECDAT Backend — Progress

## 2026-09-18 — Phase 9: CycloneDX 1.6 CBOM Export & Multi-Page Executive PDF Report

Implemented complete exports and executive reporting suite:
- Upgraded CycloneDX 1.6 Cryptographic BOM (`api/cbom.py`, `GET /api/v1/scans/{id}/cbom`) with metadata enrichment (`ecdat:scanId`, `ecdat:policyId`, `ecdat:riskScore`).
- Added on-the-fly computed SHA-256 header `X-CBOM-SHA256` for instant tamper detection.
- Verified strict validation against the vendored CycloneDX 1.6 JSON schema for both seed and live AST scan findings.
- Built a zero-dependency, pure-Python multi-page PDF 1.4 report generator (`api/pdf_report.py`, `GET /api/v1/scans/{id}/report.pdf`) without external C libraries (Cairo/Pango).
- 3-page publication layout:
  - Page 1: Executive Scorecard with large Mosca score, risk band badges, breakdown metric cards, and threat context.
  - Page 2: Detailed Mosca risk factor formulation and top vulnerable findings table.
  - Page 3: NIST FIPS 203/204/205 PQC migration roadmap and cryptographic air-gap integrity stamp.
- ADR 009 documented in `docs/decisions/backend/009-phase9-reports-and-cbom.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (105 passed), and `contract_diff.py` all clean.

## 2026-09-18 — Phase 8: PQC Catalog & Algorithm Agility Metrics

Implemented authoritative NIST FIPS 203/204/205 PQC catalog and deterministic agility delta metrics:
- Authoritative NIST specifications in `engine/pqc.py`:
  - FIPS 203: ML-KEM-512 (Cat 1), ML-KEM-768 (Cat 3), ML-KEM-1024 (Cat 5)
  - FIPS 204: ML-DSA-44 (Cat 2), ML-DSA-65 (Cat 3), ML-DSA-87 (Cat 5)
  - FIPS 205: SLH-DSA-SHA2-128s, SLH-DSA-SHAKE-128s (Cat 1)
  - Parameter sets define public key size, wire/ciphertext overhead, operation latency, and standards status.
- Upgraded `engine/recommend.py` to route to standardized PQC algorithms based on cryptographic function and security level (e.g. RSA >= 3072 upgrading to ML-KEM-1024; RSA/ECDSA signers to ML-DSA-65/87).
- Deterministic agility cost delta calculation (`compute_cost_delta`) evaluating key size ratios, wire overhead, and CPU delta to return `RiskCost` (`low`, `medium`, `high`).
- Dynamic catalog generation from `NIST_PQC_CATALOG` serving `GET /api/v1/catalog/pqc`.
- ADR 008 documented in `docs/decisions/backend/008-phase8-pqc-catalog.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (100 passed), and `contract_diff.py` all clean.

## 2026-09-18 — Phase 7: Engine Expansion & Multi-Language Detection

Expanded the AST engine with multi-language detection and real-world attribute analysis:
- Added Go standard library crypto AST detector (`engine/source_go.py`, `engine/queries/go_crypto.scm`) using pinned `tree-sitter-go==0.25.0` wheel (air-gapped, zero runtime network calls), detecting RSA, ECDSA, AES, 3DES, DES, MD5, SHA-1, SHA-2, and HMAC.
- Added Python bare attribute reference detection in `engine/source_python.py` (`engine/queries/python_crypto.scm`), allowing detection of `hashlib.X` arguments passed into functions or constructors without calling.
- Integrated multi-language file routing in `engine/scanner.py` supporting both `.py` and `.go`.
- Added `bench/real_world/samples/go_crypto_sample.go` and verified precision 1.000, recall 1.000, F1 1.000 in `bench/real_world/evaluate.py`.
- ADR 007 documented in `docs/decisions/backend/007-phase7-multi-language-detection.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (95 passed), and `contract_diff.py` all clean.

## 2026-09-18 — Phase 6: Sandboxed Streaming Ingest (`POST /scans/upload`)

Implemented streaming multipart upload archive ingestion with full hostile traversal defenses:
- OpenAPI 3.1 contract update: added `POST /api/v1/scans/upload` (`multipart/form-data`) and `bundleHash` to `Scan` schema, documented in `contracts/CHANGELOG.md` (`0.3.0-phase6-ingest`). Zero contract drift verified.
- `engine/ingest.py`: on-the-fly streaming SHA-256 calculation, 2GB upload limit, and safe archive extraction for `.zip` and `.tar.*`.
- Security defenses:
  - Zip-Slip / path traversal prevention rejecting relative `..`, absolute paths, and verifying canonical sandbox destination.
  - Symlink escape prevention inspecting link targets to disallow escapes or system directory references.
  - Decompression bomb quotas enforcing 5GB uncompressed size limit and 50,000 maximum file count.
- Route integration in `api/routes/scans.py` extracting into ephemeral sandbox directories, running AST detection, and attaching computed `bundleHash`.
- ADR 006 documented in `docs/decisions/backend/006-phase6-sandboxed-ingest.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (90 passed), and `contract_diff.py` all clean.

## 2026-09-18 — Phase 5: Rescore Performance Budget (<200ms SLA for 10,000 findings)

Implemented in-database bulk vectorized Common Table Expression (CTE) UPDATE + RETURNING in `api/store.py` (`rescore_scan_findings`).
- Directly recomputes urgency $U$, margin $(X+Y-Z)$, score, and risk band inside SQLite/Postgres without loading 10,000 ORM entities into Python memory.
- Mathematical invariant pruning: classically broken algorithms ($U=1.0$ unconditionally) are excluded from the CTE calculation, cutting write locks and execution overhead while ensuring mathematical invariance.
- Direct JSON tuple serialization (~25ms vs ~85ms standard dumps), returning pre-encoded bytes directly to Starlette `Response`.
- Performance test gate in `tests/test_rescore_perf.py` asserts < 200ms round-trip latency on 10,000 seeded findings (measured: 105–135ms).
- ADR 005 documented in `docs/decisions/backend/005-phase5-rescore-performance.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (79 passed), and `contract_diff.py` all clean.

## 2026-09-18 — Loop B1 starter step: real, unseen, hand-labelled Python code

Small, fast pass (explicitly not the brief's full DEV/HOLD scale — see
`bench/real_world/README.md`): fetched 2 small real files never used to
build or tune the detector (`itsdangerous`'s signer, BSD-3-Clause, and
`cryptography`'s own official RSA keygen doctest recipe, Apache-2.0/BSD
-- both on the licence gate's "OK" list), hand-labelled their crypto
usage by reading the source first, then ran the detector.

```
$ uv run python bench/real_world/evaluate.py
precision=1.0 recall=1.0 f1=1.0
truth=4 detected=4 tp=4
```

4/4, no false positives/negatives -- on real, unseen code, not just the
synthetic starter set. Reading a broader real file (PyJWT's
`algorithms.py`, not vendored) surfaced two real, honestly-documented
detector gaps (bare `hashlib.X` attribute references without a call; no
type inference for `key.sign()`-style OO calls -- the latter already
listed in the brief's own Phase 7) rather than silently ignoring them --
see `bench/real_world/README.md` and `PLAN.md`.

Gates: `uv run ruff check . && uv run mypy --strict .` clean (46 files),
`uv run pytest` 78/78 passed at 94% coverage, `contract_diff.py` clean
(no API changes this pass).

## 2026-09-18 — Phase 4: Real-Time Events (scoped: real event log, sync scanning)

User was asked to choose between (a) a real, stored per-scan event log
replayed after a still-synchronous `POST /scans` returns, with genuine
resume-by-eventId, or (b) making scanning fully asynchronous so a WS
client can watch it live. Chose (a) -- smaller, deterministic, no
async-timing test flakiness; full async scanning stays a documented gap
for later, not silently faked.

Preceded by a separate `contract: update ScanEvent schema...` PR (#5,
merged) per this repo's git rules (contract changes never land inside a
feature commit) -- replaced the placeholder `percent` field with the real
fields this phase's event log actually produces.

Built: `engine.scanner.scan()` takes an optional `on_event` callback and
emits real `stage`/`progress`/`finding` events as it runs (real stage
transitions, a real running per-surface finding counter, real finding
ids). `ScanEventRecord` + `store.list_events()` persist and replay that
log. `WS /scans/{id}/events` now sends the *actual* recorded events for
that scan (previously: a hardcoded canned sequence referencing fake
finding ids, regardless of what was scanned) -- rate-limited to <=10
msg/sec, with `?after=<eventId>` resume.

### Gate output (real, run from `backend/`)

```
$ uv run ruff check .
All checks passed!

$ uv run mypy --strict .
Success: no issues found in 43 source files

$ uv run pytest --cov=api --cov=engine --cov=scripts --cov=bench --cov-report=term-missing --cov-fail-under=85
...
TOTAL                       1183     64    95%
Required test coverage of 85% reached. Total coverage: 94.59%
77 passed, 3 warnings in 4.85s

$ uv run python scripts/contract_diff.py
No contract drift.
```

### Manual verification

Booted a real `uvicorn` server, wrote a file with `hashlib.md5(...)` +
`hmac.new(..., hashlib.sha1)`, `POST /scans`, then used a real Python
`websockets` client:
- Full replay: 7 real events in order (`stage:ingesting`,
  `stage:scanning`, 2x real `finding` events with real ids/families,
  `progress` with `bySurface: {"source": 2}`, `stage:scoring`, `done`
  with the right `findingCount`).
- Resume: reconnecting with `?after=4` returned only events 5-7 (the
  genuine tail) -- confirms resume is real, not decorative.

### Loops run

None of B1/B3-B6 apply. No risk-formula/factor change this phase.

### BLOCKED items

None. The one deliberate gap (live streaming during an in-flight scan)
is a scoped-out design decision, not a blocker -- see `PLAN.md`.

### Contract changes / PROPOSALS decisions

`contract: update ScanEvent schema for real Phase 4 event log` (PR #5,
merged before this feature PR) -- see `contracts/CHANGELOG.md`. No
PROPOSALS from the frontend agent yet.

### Next 3 tasks

See `PLAN.md`: (1) a real hand-labelled DEV/HOLD corpus (Loop B1) plus
broader Python detection coverage, (2) Phase 5 rescore performance
budget, (3) revisit async scanning if live-during-scan progress becomes
important before Phase 6.

## 2026-09-18 — Phase 3: Real API

Wired `engine.scanner.scan()` into `POST /scans`: it now scans the given
server-side `path` with the real Python detector and persists real,
risk-scored findings via `api/store.py` (new `store.create_scan_from_result`
+ `store.resolve_policy`, replacing the always-empty stub `create_scan`).
`payload.crqcYears` now genuinely overrides the scoring horizon for that
scan (a policy copy with the override is what gets passed to
`engine.factors.derive_risk`), not just a stored-but-unused metadata field.
Missing/nonexistent `path` -> 400; an `OSError` during scanning ->
`status=failed` rather than a 500. The API contract is unchanged — this
phase changes route *behavior*, not shapes — verified with
`scripts/contract_diff.py`.

### Gate output (real, run from `backend/`)

```
$ uv run ruff check .
All checks passed!

$ uv run mypy --strict .
Success: no issues found in 42 source files

$ uv run pytest --cov=api --cov=engine --cov=scripts --cov=bench --cov-report=term-missing --cov-fail-under=85
...
TOTAL                       1140     64    94%
Required test coverage of 85% reached. Total coverage: 94.39%
71 passed, 3 warnings in 3.24s

$ uv run python scripts/contract_diff.py
No contract drift.
```

### Manual verification

Booted a real `uvicorn` server, wrote a real file with `hashlib.sha1(...)`,
and:
- `POST /scans {"path": "/tmp/e2e_scan_target"}` -> real `stats.files=1`,
  a real `bands.medium=1`, not the old canned empty stub.
- `GET /scans/{id}/findings` -> one real finding: family `SHA-1`, a
  genuine risk score (18.0, band `medium`, `classicallyBroken: true`),
  and a real recommendation (`SHA-2-256`).
- `GET /scans/{id}/cbom` -> 1 CycloneDX component, matching the finding.
- `POST /scans {"path": "/does/not/exist"}` -> 400.
- `POST /scans {}` (no path) -> 400.

### Loops run

None of B1/B3-B6 apply. No formula/factor change this phase (only real
wiring) — `tests/test_risk_formula.py` and `tests/test_factors.py` still
pass unchanged.

### BLOCKED items

None.

### Contract changes / PROPOSALS decisions

None — verified via `contract_diff.py`.

### Next 3 tasks

See `PLAN.md`: (1) a real hand-labelled DEV/HOLD corpus (Loop B1) plus
extending Python detection coverage, (2) Phase 4 real-time WS scan
progress backed by the real engine run, (3) Phase 5 rescore performance
budget now that `POST /scans` can actually produce large finding sets.

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
