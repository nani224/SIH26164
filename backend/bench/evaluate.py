"""Runs engine.scanner.scan() over bench/fixtures/ and measures precision/
recall against bench/truth.json.

This is a small, hand-built *starter* fixture set (~15 labelled usages
across 8 files) -- NOT the brief's Layer A/B corpus or the Loop B1
DEV/HOLD split (>=150 labelled usages across 3 unseen real projects),
which doesn't exist yet. Treat these numbers as a Phase 1 sanity floor for
the rules that exist today, not a claim about general-codebase accuracy.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.models import Context, Criticality, Exposure, Policy  # noqa: E402
from engine.scanner import scan  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TRUTH_PATH = Path(__file__).parent / "truth.json"

_POLICY = Policy(
    id="bench_policy",
    name="Bench evaluation policy",
    crqcYears=10,
    default=Context(
        exposure=Exposure.INTERNAL, criticality=Criticality.MEDIUM, shelfLifeYears=5, migrationYears=3
    ),
    contexts=[],
)


def _truth_set() -> set[tuple[str, str, str, int]]:
    truth = json.loads(TRUTH_PATH.read_text())
    return {
        (path, entry["family"], entry["function"], entry["line"])
        for path, entries in truth.items()
        for entry in entries
    }


def _detected_set() -> set[tuple[str, str, str, int]]:
    result = scan(FIXTURES_DIR, _POLICY)
    return {
        (f.location.path, f.family.value if f.family else "", f.function.value, f.location.line or -1)
        for f in result.findings
    }


def evaluate() -> dict[str, Any]:
    truth = _truth_set()
    detected = _detected_set()

    true_positives = truth & detected
    false_positives = detected - truth
    false_negatives = truth - detected

    precision = len(true_positives) / len(detected) if detected else 1.0
    recall = len(true_positives) / len(truth) if truth else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": len(true_positives),
        "false_positives": sorted(false_positives),
        "false_negatives": sorted(false_negatives),
        "truth_count": len(truth),
        "detected_count": len(detected),
    }


def main() -> int:
    result = evaluate()
    print(f"precision={result['precision']} recall={result['recall']} f1={result['f1']}")
    print(f"truth={result['truth_count']} detected={result['detected_count']} tp={result['true_positives']}")
    if result["false_positives"]:
        print("false positives:")
        for fp in result["false_positives"]:
            print(f"  {fp}")
    if result["false_negatives"]:
        print("false negatives:")
        for fn in result["false_negatives"]:
            print(f"  {fn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
