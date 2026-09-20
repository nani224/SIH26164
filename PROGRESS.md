# ECDAT v1.0 — Crypto Mass Conservation (CMC) Engine: Progress Log

## M1 — SPAN PROVENANCE (Foundation)
- **Status**: COMPLETED & VERIFIED
- **Changes**:
  - Implemented `Span` dataclass in `backend/engine/models.py`:
    ```python
    @dataclass(frozen=True)
    class Span:
        artifact_hash: str
        kind: Literal["byte", "ast"]
        start: int
        end: int
        producing_rule: str
        coarse: bool = False
    ```
  - Added `spans: list[Span]` to `Detection`.
  - Added `spans_by_finding: dict[str, list[Span]]` to `ScanResult`.
  - Updated all source detectors (`source_python.py`, `source_go.py`, `source_java.py`, `source_c.py`) and binary scanner (`scanner.py`) to generate precise `Span` objects with byte ranges, artifact hash, and producing rule name.
  - Attached spans to `Finding` objects via `object.__setattr__(finding, "spans", ...)` and populated `finding.location.offset = span.start`.
  - Created `backend/tests/test_span_provenance.py` covering 100% span coverage, coarse-span rate, and property tests via Hypothesis ensuring `0 <= span.start <= span.end <= len(artifact)`.
- **Real Verification Output**:
  ```text
  tests/test_span_provenance.py 
  [M1 Span Provenance Report]
    Total findings: 64
    Findings with spans: 64 (100.0%)
    Total spans: 64
    Coarse spans: 0 (coarse rate: 0.0%)
  ....
  ======================== 4 passed, 2 warnings in 1.09s ========================
  ```
  All existing scanner & detector tests (69 items) pass green.
