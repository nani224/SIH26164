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

## M4 — COVERAGE CERTIFICATE
- **Status**: COMPLETED & VERIFIED
- **Changes**:
  - Implemented `backend/engine/certificate.py`:
    - Generates `CoverageCertificate` with total mass, attributed, excluded, residue, coverage ratio, residue cluster count, and top clusters with locations.
    - Generates signed attestation manifest using HMAC-SHA256 and canonical JSON serialization.
    - Implemented `embed_coverage_in_cbom` which embeds coverage properties (`ecdat:coverage:*`) into `metadata.properties` and the certificate into `annotations`.
  - Created `backend/tests/test_coverage_certificate.py`:
    - Verified strict CycloneDX 1.6 schema validation on CBOMs carrying the certificate.
    - Verified reproducibility: identical input produces strictly identical coverage numbers and attestation hashes.
- **Real Verification Output**:
  ```text
  tests/test_coverage_certificate.py ..
  ======================== 2 passed, 3 warnings in 0.44s ========================
  ```

## M5 — THE FOUR KILL TESTS
- **Status**: COMPLETED & ALL FOUR PASSED
- **Changes**:
  - Implemented and verified `backend/tests/test_kill_tests.py`:
    - **K1 SENSITIVITY**: Verified on unmodeled/custom crypto false-negative fixtures. 100% (5/5) surfaced as residue ($\ge 90\%$ threshold).
    - **K2 SPECIFICITY**: Floor defined before running: 5.0% residue mass. Benign fixtures produced 0.00% residue mass (0.0 bytes residue over 819 bytes benign code).
    - **K3 NON-VACUITY**:
      - AES: baseline=0.0 -> disabled=256.0 -> restored=0.0.
      - SHA-256: baseline=0.0 -> disabled=32.0 -> restored=0.0.
      - MD5: baseline=0.0 -> disabled=32.0 -> restored=0.0.
    - **K4 DIRECTIONAL VALIDITY**: Closing 3 residue clusters with rules measurably dropped residue ($\Delta \text{Residue} = -45.00$) and increased recall ($\Delta \text{Findings} = +3$).
- **Real Verification Output**:
  ```text
  tests/test_kill_tests.py 
  [K1 Sensitivity]: 5/5 (100.0%) surfaced as residue
  .
  [K2 Specificity]: benign residue mass = 0.0 over 819 bytes (0.00%)
    Defined floor: 5.0%
  .
  [K3 Non-Vacuity AES]: baseline=0.0 -> disabled=256.0 -> restored=0.0 (OK)
  [K3 Non-Vacuity SHA-256]: baseline=0.0 -> disabled=32.0 -> restored=0.0 (OK)
  [K3 Non-Vacuity MD5]: baseline=0.0 -> disabled=32.0 -> restored=0.0 (OK)
  .
  [K4 Directional Validity]:
    Residue delta: -45.00 (from 45.00 to 0.00)
    Findings/Recall delta: +3 (from 0 to 3)
  .
  ======================== 4 passed, 2 warnings in 0.44s ========================
  ```

## M6 — DEBT-CLOSURE LOOP
- **Status**: COMPLETED & VERIFIED
- **Changes**:
  - Implemented `backend/engine/debt.py`:
    - CLI commands: `ecdat debt list|show|promote|exclude|accept`.
    - `promote_cluster`: Scaffolds a working detection rule stub with its fixture and marks state as `promoted-to-rule`.
    - `exclude_cluster`: Requires written justification and owner, marks state as `excluded`.
    - `accept_cluster`: Records why residue is tolerated, marks state as `accepted`.
    - Persistent debt store `debt_store.json` keyed by content hash so closed clusters never resurface and carry across estates.
  - Created `backend/tests/test_debt_closure.py`:
    - Verified CLI operations (`list`, `show`, `exclude`, `accept`).
    - Verified validation guards (empty justification/owner rejected).
    - Proven end-to-end on a real residue cluster: promoting the cluster generated a working rule, residue dropped by that cluster's exact mass (-32.0), and recall rose (+1 finding).
- **Real Verification Output**:
  ```text
  tests/test_debt_closure.py .
  CLUSTER ID       STATE            OWNER           JUSTIFICATION
  ---------------------------------------------------------------------------
  hash_abc_123     excluded         alice           Benign table
  .
  [M6 End-to-End Promotion]
    Target residue cluster ID: c8d35ec6bc6c107e253944053a2cf840bf55e554faf2b00b3ff166d1fbddc162
    Target residue cluster mass: 32.0
    Baseline residue mass: 32.0
    New residue mass: 0
    Residue drop: 32.0 (expected == 32.0)
    Recall gain: +1 finding
  .
  ======================== 3 passed, 2 warnings in 0.44s ========================
  ```





