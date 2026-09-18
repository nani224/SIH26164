"""Precision/recall for bench/real_world/ -- see README.md in this
directory for what this is (and isn't) before trusting the number it
prints. Mirrors bench/evaluate.py's approach, pointed at real code
instead of the synthetic starter fixtures.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from api.models import Context, Criticality, Exposure, Policy  # noqa: E402
from engine.scanner import scan  # noqa: E402

_DIR = Path(__file__).parent
_SAMPLES_DIR = _DIR / "samples"
TRUTH_PATH = _DIR / "truth.json"

_POLICY = Policy(
    id="real_world_bench_policy",
    name="Real-world bench evaluation policy",
    crqcYears=10,
    default=Context(exposure=Exposure.INTERNAL, criticality=Criticality.MEDIUM, shelfLifeYears=5, migrationYears=3),
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
    result = scan(_SAMPLES_DIR, _POLICY)
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
    for fp in result["false_positives"]:
        print(f"  false positive: {fp}")
    for fn in result["false_negatives"]:
        print(f"  false negative: {fn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
