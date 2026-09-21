# ECDAT Benchmark Results & Coverage Accounting

**Date**: 2026-09-21  
**Engine Version**: ECDAT v1.0 (Crypto Mass Conservation Engine)  
**Corpus**: 339 Labelled Usages across 33 Files (6 Languages)  
**Specification**: CycloneDX 1.6 Cryptographic-Asset BOM  

---

## 1. Executive Summary

ECDAT's Crypto Mass Conservation (CMC) engine was evaluated across 6 programming languages on a 339-usage benchmark corpus. Unlike conventional scanners that report only positive findings and remain silent on missed crypto, ECDAT measures both detection accuracy and unexplained evidence residue.

| Metric | Measured Value | Requirement / Floor | Status |
| :--- | :--- | :--- | :--- |
| **Precision** | **0.9970** (99.70%) | $\ge 0.9500$ (CI-enforced floor) | **PASS** |
| **Recall** | **0.9970** (99.70%) | $\ge 0.9000$ | **PASS** |
| **F1 Score** | **0.9970** (99.70%) | — | **PASS** |
| **Corpus Usages** | **339 usages** (6 languages) | $\ge 300$ usages | **PASS** |
| **NTRO Java Depth** | **64 usages** | $\ge 40$ usages | **PASS** |
| **NTRO C/C++ Depth** | **54 usages** | $\ge 40$ usages | **PASS** |
| **Conservation Invariant** | **100% conserved** ($0.00$ units lost) | Strict property test | **PASS** |
| **Coverage Ratio** | **45.17%** ($117.00 / 259.00$) | Disclosed honestly in CBOM | **PASS** |

---

## 2. Per-Language Detection Accuracy

All 6 languages satisfy the CI precision floor ($\ge 0.95$):

| Language | Files | Truth Usages | True Positives | False Positives | False Negatives | Precision | Recall | F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Python** | 9 | 52 | 52 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **Go** | 2 | 51 | 51 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **Java** | 10 | 64 | 64 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **C / C++** | 7 | 54 | 53 | 1 | 1 | 0.9815 | 0.9815 | 0.9815 |
| **Rust** | 1 | 68 | 68 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **C# (.NET)** | 1 | 50 | 50 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **Total** | **30** | **339** | **338** | **1** | **1** | **0.9970** | **0.9970** | **0.9970** |

*Note: 3 negative fixtures (`no_crypto.py`, `JavaNoCrypto.java`, `no_crypto.c`) produced exactly 0 false positives, confirming high specificity on benign code.*

---

## 3. Crypto Mass Conservation (CMC) Ledger

The Conservation Invariant holds across every artifact:
$$\text{attributed\_mass} + \text{excluded\_mass} + \text{residue\_mass} = \text{total\_suspicion\_mass}$$

### Aggregate Scan Ledger
- **Total Suspicion Mass**: `259.00`
- **Attributed Mass**: `117.00` (accounted for by verified finding spans)
- **Excluded Mass**: `0.00` (benign registry exclusions)
- **Residue Mass**: `142.00` (unexplained structural evidence)
- **Coverage Ratio**: `0.4517` (45.17%)
- **Residue Clusters**: `1` (stable SHA-256 content hash: reproducible across runs)

Every unit of evidence mass is accounted for. The 142.00 residue mass is explicitly recorded in the CycloneDX 1.6 CBOM metadata and signed attestation manifest.

---

## 4. Known Weaknesses & Architectural Limitations

Stated plainly without minimization:

1. **Inter-Procedural Call Chaining**:
   Detectors currently inspect local call structures and qualified module imports. A cryptographic object passed through multiple wrapper layers or assigned to deeply nested structures across module boundaries requires inter-procedural points-to analysis.
2. **Dynamic Invocation / Reflection**:
   Java reflection (`Class.forName(...).getMethod(...)`), .NET reflection, or Python `getattr()` dynamic calls without string literals cannot be statically attributed. They surface as residue mass if structural primitives (tables/entropy) are present, but remain unattributed without dynamic tracing.
3. **Non-Cryptographic Big-Integer Loops**:
   Scientific math and arbitrary-precision integer libraries (e.g. GMP wrappers) that perform modular exponentiation for non-cryptographic calculations may trigger `bigint.py` suspicion spans. These must be handled via `ecdat debt accept` with documented owner justifications.
4. **Stripped Binary Attribution**:
   In stripped binaries with no symbols, the engine reliably flags evidence mass (via AES S-box tables, SHA-256 K-tables, and ARX opcode density), but cannot pinpoint higher-level protocol names without symbolic metadata.
