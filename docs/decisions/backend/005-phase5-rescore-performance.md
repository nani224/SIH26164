# ADR 005: Phase 5 rescore performance budget (< 200ms SLA for 10,000 findings)

Status: accepted
Date: 2026-09-18

## Context

The SIH26164 brief establishes a strict SLA:
Interactive rescoring of up to 10,000 findings from stored risk factors when the cryptographic horizon $Z$ is adjusted in the UI (e.g., dragging the Mosca timeline slider), without re-running code analysis or AST detection, must complete in **< 200ms**.

In the initial naive implementation:
- `store.list_findings` loaded 10,000 ORM entities into Python memory (~400ms).
- A Python loop rescored findings and issued individual SQL UPDATEs, taking 2–4 seconds and thrashing transaction logs.
- Attempting standard Pydantic response validation on 6,000 changed finding objects took > 500ms alone.

## Decision

1. **In-Database Vectorized Bulk CTE Update (`backend/api/store.py`)**:
   - The urgency $U$, margin $(X + Y - Z)$, score ($100 \cdot V \cdot F \cdot U \cdot E \cdot K$), and risk band are computed entirely inside the database using a Common Table Expression (CTE) `UPDATE findings SET ... FROM banded WHERE ... RETURNING`.
   - **Mathematical Invariant Pruning**: Classically broken algorithms have an unconditional invariant urgency $U = 1.0$, regardless of $Z$. Filtering `WHERE ... AND (risk_classically_broken = 0 OR risk_classically_broken IS NULL)` skips 40% of the dataset (e.g. 4,000 SHA-1 / 3DES rows), reducing index lookups and write locks while guaranteeing mathematical invariance.
   - Bypasses SQLAlchemy ORM session tracking overhead by using the underlying raw DBAPI connection cursor (`conn.connection.dbapi_connection.cursor()`).

2. **Single Transaction & Compact Audit Summary**:
   - A single transaction executes: the bulk CTE update, the updated band counts aggregation (`SELECT risk_band, COUNT(*) ... GROUP BY risk_band`), the scan update, and one summary audit log entry (`scan.rescore`, recording total rows rescored and count changed).

3. **Optimized Direct JSON Serialization**:
   - Standard `json.dumps()` on 6,000 nested Python dictionaries (containing `location`, `risk`, `triage`) allocated over 300,000 heap objects and incurred ~85ms serialization overhead with GC pressure.
   - We format row tuples directly via string templating into pre-encoded UTF-8 `bytes`, reducing serialization from ~85ms to **~25ms**.
   - The route handler returns `Response(content=content_bytes, media_type="application/json")`, completely bypassing Starlette's redundant Pydantic re-serialization.

4. **Automated Performance & Invariant Gate (`backend/tests/test_rescore_perf.py`)**:
   - Seeds 10,000 findings (4,000 classically broken SHA-1 and 3DES; 6,000 quantum-sensitive RSA, AES, ML-KEM).
   - Warms the TestClient / ASGI worker thread, then measures roundtrip latency.
   - Asserts:
     1. Status code is 200.
     2. Total turnaround time is strictly `< 0.200` seconds.
     3. Mathematical invariance: SHA-1 and 3DES scores never change.
     4. Quantum-sensitive findings update accurately.
     5. Total counts across all bands sum to exactly 10,000.

## Empirical Measurements

- **In-Database Bulk Update + Returning**: ~70–80 ms
- **Bands count & scan update**: ~3–5 ms
- **Direct serialization + UTF-8 encode**: ~25 ms
- **FastAPI response dispatch**: < 0.1 ms
- **Total TestClient Round-trip Latency**: **105 ms – 135 ms** (comfortably within the 200ms budget limit, with ~65–95ms of headroom).

## Consequences

- **Zero Contract Drift**: Fully verified against `contracts/openapi.yaml` via `scripts/contract_diff.py`.
- **High Concurrency**: Direct DBAPI transaction keeps write lock durations under 80ms even at 10,000-row scale.
- **Maintainability**: The Mosca formula is strictly mirrored between `engine/risk.py` and the SQL CTE, with identical clamping ($0.05 \le U \le 1.0$) and band cutoffs ($60 / 35 / 15$).
