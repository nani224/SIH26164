# ADR 003: Phase 7 Multi-Language Engine Expansion & Attribute Reference Detection

Status: accepted
Date: 2026-09-18

## Context

The SIH26164 brief and previous real-world evaluations (Loop B1 evaluation against PyJWT) identified two critical detector capabilities needed for real-world cryptographic discovery:
1. **Multi-Language Detection**: Support for Go crypto (`crypto/rsa`, `crypto/ecdsa`, `crypto/aes`, `crypto/des`, `crypto/md5`, `crypto/sha1`, `crypto/sha256`, `crypto/hmac`).
2. **Bare Attribute References in Python**: Detecting references like `digest_method=hashlib.sha256` passed to functions, constructors, or variables without immediate direct calls.

## Decision

1. **Tree-Sitter Go Grammar (`tree-sitter-go`)**:
   - Pinned official PyPI wheel `tree-sitter-go==0.25.0`, keeping the engine fully air-gapped without runtime network calls.
   - SCM query (`backend/engine/queries/go_crypto.scm`) captures package selector calls (`pkg.Func(...)`).
   - `backend/engine/source_go.py` maps Go standard library crypto usages to standardized `Detection` models.

2. **Python Bare Attribute Reference Detection**:
   - Updated `backend/engine/queries/python_crypto.scm` to capture attribute nodes.
   - Handled in `backend/engine/source_python.py`: avoids duplicate detections when the attribute is the target of a direct call or enclosed within `hmac.new`.

3. **Scanner Router (`backend/engine/scanner.py`)**:
   - Dispatches `.py` files to `source_python.detect` and `.go` files to `source_go.detect_code`.

4. **Real-World Benchmark Evaluation**:
   - Added `go_crypto_sample.go` to `bench/real_world/samples/` with ground-truth verification in `truth.json`.
   - Measured precision 1.000, recall 1.000, F1 1.000 across 7 real-world usages in `tests/test_bench_real_world.py`.

## Consequences

- Full deterministic AST detection for both Python and Go cryptographic assets.
- Clean separation of language-specific detection logic with uniform risk factor and policy evaluation.
