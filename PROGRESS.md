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

## M2 — RULE-INDEPENDENT EXTRACTORS (`backend/engine/extract/`)
- **Status**: COMPLETED & VERIFIED
- **Changes**:
  - Implemented rule-independent extractors in `backend/engine/extract/`:
    - `tables.py`: 256-byte bijections over 0..255 (cipher-agnostic S-box shape) & binary u32 constant tables with high pairwise Hamming distance.
    - `entropy.py`: Shannon entropy sliding window flagging sustained high-entropy regions inside low-entropy artifacts.
    - `arx.py`: ARX opcode density in binaries and AST subtrees composing rotate + XOR in source.
    - `bigint.py`: Modular-exponentiation loop shapes (conservative multiply-reduce cycles).
    - `framing.py`: Structural PEM, DER ASN.1 sequences, and Base64 blocks (without algorithm keywords).
    - `literals.py`: Large numeric arrays, key-length shaped literals (256/512/1024/2048/3072/4096), and high-entropy string constants.
    - `__init__.py`: Aggregates all extractors with `extract_all()`.
  - Created `backend/tests/test_extractors.py`:
    - Verified architectural independence: `extract/` strictly does not import from `rules/` or `source_*` or `scanner`.
    - Tested each extractor on a positive fixture and a benign negative fixture.
    - Verified determinism: identical input produces identical spans across 3 runs.
- **Real Verification Output**:
  ```text
  tests/test_extractors.py ........
  ======================== 8 passed, 2 warnings in 0.33s ========================
  ```

