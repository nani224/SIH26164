# ECDAT Benchmark & Crypto Mass Conservation (CMC) Protocol

This document specifies the blind-labelling rules, conservation metrics, and exact steps required for any independent evaluator to reproduce ECDAT's benchmark results from scratch.

---

## 1. Principles & Non-Negotiables

### 1.1 Blind-Labelling Rule
1. **Ground Truth Before Rule Tuning**: Ground truth labels in `bench/truth.json` are established and committed in isolation before detector rules are run or tuned.
2. **Never Tune on HOLD**: Real-world evaluation datasets (`bench/real_world/`) serve as a strict HOLD corpus. No rule may be fitted to specific HOLD samples.
3. **Honest Accounting**: Residue is never silently discarded. A high residue figure indicates unexplained evidence mass and represents a real finding, not a failure to hide.

### 1.2 Adversarial Independence
1. **Extraction Independence**: The feature extractors (`backend/engine/extract/`) detect structural suspicion mass (entropy anomalies, bijection tables, ARX patterns, big-integer loop structures, framing shapes, and literal densities) without importing or knowing anything about algorithmic rules.
2. **CI-Enforced Boundary**: Any import from `engine.rules` or rule-specific logic into `engine.extract` fails CI immediately.

### 1.3 Conservation Invariant
Every artifact evaluated must satisfy the fundamental conservation invariant:
$$\text{attributed\_mass} + \text{excluded\_mass} + \text{residue\_mass} = \text{total\_suspicion\_mass}$$
- **Attributed Mass**: Suspicion intervals overlapping with verified cryptographic finding spans.
- **Excluded Mass**: Suspicion intervals matched against falsifiable exclusion predicates (e.g., CRC32 tables, Base64 character maps, dead/unreachable code).
- **Residue Mass**: Unexplained suspicion intervals, clustered by content hash for cross-estate stability.
- **Coverage Ratio**: $\frac{\text{attributed\_mass}}{\text{total\_suspicion\_mass}}$ (reported honestly in every CBOM).

---

## 2. Evaluation Metrics

### Detection Performance
- **True Positives ($TP$)**: Detections matching ground truth on `(path, family, function, line)`.
- **False Positives ($FP$)**: Detections produced by the engine not present in ground truth.
- **False Negatives ($FN$)**: Ground truth usages not discovered by the engine.
- **Precision**: $\frac{TP}{TP + FP}$ (CI-enforced floor: $\ge 0.9500$).
- **Recall**: $\frac{TP}{TP + FN}$.
- **F1 Score**: $\frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$.

### Coverage Performance
- **Total Suspicion Mass ($M_{\text{total}}$)**: Cumulative magnitude of all structural evidence spans.
- **Attributed Mass ($M_{\text{attr}}$)**: Evidence mass explained by rule findings.
- **Residue Mass ($M_{\text{res}}$)**: Unexplained evidence mass.
- **Coverage Ratio**: $\frac{M_{\text{attr}}}{M_{\text{total}}}$.

---

## 3. Reproduction Instructions

Any stranger can reproduce our numbers on Linux, macOS, or Windows by following these exact steps:

### Prerequisites
- Python 3.12+
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `winget install astral-sh.uv`)
- `git`

### Step 1: Clone Repository
```bash
git clone https://github.com/nani224/SIH26164.git
cd SIH26164
git checkout feature/cmc-engine
```

### Step 2: Install Dependencies
```bash
cd backend
uv sync
```

### Step 3: Run Full Benchmark
Execute the automated benchmark scorer:
```bash
# Option A: Via make (from repo root)
make benchmark

# Option B: Direct Python invocation (from backend directory)
uv run python bench/public/score.py --all
```

### Step 4: Validate Machine-Readable JSON Output
```bash
uv run python bench/public/score.py --all --json
```

### Step 5: Score Any External CycloneDX 1.6 CBOM
The scorer accepts arbitrary CycloneDX 1.6 CBOM files from any vendor:
```bash
uv run python bench/public/score.py --cbom /path/to/external_cbom.json --truth bench/truth.json
```

---

## 4. Verification Gates

1. **Precision Gate**:
   ```bash
   uv run python bench/check_precision_floor.py
   ```
   Must exit with code `0` and confirm precision $\ge 0.95$ on both starter and HOLD corpora.

2. **Kill Tests**:
   ```bash
   uv run pytest tests/test_kill_tests.py
   ```
   Must pass K1 Sensitivity ($\ge 90\%$), K2 Specificity ($< 5\%$ on benign code), K3 Non-Vacuity, and K4 Directional Validity.
