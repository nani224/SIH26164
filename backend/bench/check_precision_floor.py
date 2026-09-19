"""CI gate: fail if precision drops below the Track CC floor (0.95) on
either corpus. See root CLAUDE.md: "Any rule that raises recall but
drops precision below 0.95 is wrong -- fix the rule's specificity or
drop it, never ship it anyway." This script is what turns that rule from
a norm into something CI actually enforces, wired into
.github/workflows/backend-ci.yml.

Only checks precision (never recall -- a recall regression is a real,
worth-noticing miss, but it's not what the floor is about, and gating on
it would create pressure to guess instead of leaving an honest gap).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench.evaluate import evaluate as evaluate_layer_a  # noqa: E402
from bench.real_world.evaluate import evaluate as evaluate_real_world  # noqa: E402

_PRECISION_FLOOR = 0.95


def main() -> int:
    failed = False
    for name, evaluate in (("Layer A (bench/fixtures)", evaluate_layer_a), ("real_world (HOLD)", evaluate_real_world)):
        result = evaluate()
        precision = result["precision"]
        status = "PASS" if precision >= _PRECISION_FLOOR else "FAIL"
        print(f"{name}: precision={precision} (floor {_PRECISION_FLOOR}) -- {status}")
        if precision < _PRECISION_FLOOR:
            failed = True
            for fp in result["false_positives"]:
                print(f"  false positive: {fp}")
    if failed:
        print(f"\nPRECISION FLOOR ({_PRECISION_FLOOR}) VIOLATED -- see root CLAUDE.md's Track CC rules.")
        return 1
    print(f"\nPrecision floor ({_PRECISION_FLOOR}) satisfied on both corpora.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
