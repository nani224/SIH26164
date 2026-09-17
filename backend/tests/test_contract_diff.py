from __future__ import annotations

from scripts.contract_diff import diff


def test_no_contract_drift() -> None:
    problems = diff()
    assert problems == [], "\n".join(problems)
