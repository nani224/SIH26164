"""Tests for the CI precision-floor gate (M5, Track CC)."""

from __future__ import annotations

import pytest

import bench.check_precision_floor as gate


def _fake_result(precision: float) -> dict[str, object]:
    return {"precision": precision, "false_positives": []}


def test_gate_passes_when_both_corpora_meet_the_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "evaluate_layer_a", lambda: _fake_result(1.0))
    monkeypatch.setattr(gate, "evaluate_real_world", lambda: _fake_result(0.96))
    assert gate.main() == 0


def test_gate_fails_when_layer_a_drops_below_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "evaluate_layer_a", lambda: _fake_result(0.89))
    monkeypatch.setattr(gate, "evaluate_real_world", lambda: _fake_result(1.0))
    assert gate.main() == 1


def test_gate_fails_when_real_world_drops_below_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "evaluate_layer_a", lambda: _fake_result(1.0))
    monkeypatch.setattr(gate, "evaluate_real_world", lambda: _fake_result(0.5))
    assert gate.main() == 1


def test_gate_passes_at_exactly_the_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "evaluate_layer_a", lambda: _fake_result(0.95))
    monkeypatch.setattr(gate, "evaluate_real_world", lambda: _fake_result(0.95))
    assert gate.main() == 0
