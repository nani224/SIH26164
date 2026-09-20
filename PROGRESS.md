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

## M3 — ATTRIBUTION CALCULUS (`backend/engine/attribute/`)
- **Status**: COMPLETED & VERIFIED
- **Changes**:
  - Implemented attribution calculus in `backend/engine/attribute/`:
    - `claim.py`: Interval overlap join between finding spans and suspicion spans; a suspicion span is ATTRIBUTED when overlapped by $\ge 1$ finding span.
    - `exclude.py`: Falsifiable exclusion predicates (benign-table registry keyed by content hash: CRC-32, Base64 alphabet, hex tables; non-crypto identity byte mapping; base64 media/plain-text detection).
    - `ledger.py`: Computes the Conservation Invariant ($\text{attributed} + \text{excluded} + \text{residue} == \text{total\_suspicion\_mass}$), clusters adjacent/overlapping residue spans keyed deterministically by content hash, and tracks cluster states (`open`, `promoted-to-rule`, `excluded`, `accepted`).
    - `__init__.py`: Exports attribution calculus APIs.
  - Created `backend/tests/test_attribution_calculus.py`:
    - Verified the conservation invariant on 100% of corpus artifacts (27 files in `bench/fixtures`).
    - Verified residue cluster hashes are stable across runs.
    - Verified benign CRC-32 table exclusion and audit trail logging.
    - Hypothesis property test verifying conservation invariant for arbitrary random span configurations with 0 unit lost.
- **Real Verification Output**:
  ```text
  tests/test_attribution_calculus.py 
  [M3 Attribution Calculus Invariant Report]
    Corpus artifacts audited: 27
    Total suspicion mass: 26.00
    Attributed mass: 26.00
    Excluded mass: 0.00
    Residue mass: 0.00
  ....
  ======================== 4 passed, 2 warnings in 0.96s ========================
  ```


