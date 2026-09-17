from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from engine.risk import band_for_score, compute_score, compute_urgency, rescore

_frac = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
_year = st.floats(min_value=1.0, max_value=50.0, allow_nan=False)
_delta = st.floats(min_value=0.0, max_value=20.0, allow_nan=False)
_vfek = st.fixed_dictionaries({"v": _frac, "f": _frac, "e": _frac, "k": _frac})


@given(vfek=_vfek, x=_year, y=_year, z=_year, broken=st.booleans())
def test_score_always_in_range(
    vfek: dict[str, float], x: float, y: float, z: float, broken: bool
) -> None:
    score, u, band = rescore(x=x, y=y, z=z, classically_broken=broken, **vfek)
    assert 0.0 <= score <= 100.0
    assert 0.05 <= u <= 1.0
    assert band in ("critical", "high", "medium", "low")


@given(x=_year, z=_year, y_low=_year, y_delta=_delta)
def test_urgency_non_decreasing_in_y(x: float, z: float, y_low: float, y_delta: float) -> None:
    u_low = compute_urgency(x, y_low, z, classically_broken=False)
    u_high = compute_urgency(x, y_low + y_delta, z, classically_broken=False)
    assert u_high >= u_low - 1e-12


@given(x=_year, y=_year, z_low=_year, z_delta=_delta)
def test_urgency_non_increasing_in_z(x: float, y: float, z_low: float, z_delta: float) -> None:
    u_low_z = compute_urgency(x, y, z_low, classically_broken=False)
    u_high_z = compute_urgency(x, y, z_low + z_delta, classically_broken=False)
    assert u_high_z <= u_low_z + 1e-12


@given(x=_year, y=_year, z1=_year, z2=_year)
def test_classically_broken_forces_urgency_one_regardless_of_z(
    x: float, y: float, z1: float, z2: float
) -> None:
    u1 = compute_urgency(x, y, z1, classically_broken=True)
    u2 = compute_urgency(x, y, z2, classically_broken=True)
    assert u1 == u2 == 1.0


@given(vfek=_vfek, x=_year, y=_year, z1=_year, z2=_year)
def test_classically_broken_never_changes_band_with_z(
    vfek: dict[str, float], x: float, y: float, z1: float, z2: float
) -> None:
    score1, _, band1 = rescore(x=x, y=y, z=z1, classically_broken=True, **vfek)
    score2, _, band2 = rescore(x=x, y=y, z=z2, classically_broken=True, **vfek)
    assert score1 == score2
    assert band1 == band2


def test_rescore_with_original_z_reproduces_stored_score() -> None:
    score, u, band = rescore(v=1.0, f=0.9, e=0.95, k=0.9, x=12, y=8, z=10, classically_broken=False)
    assert round(score, 2) == 76.95
    assert band == "critical"


def test_band_thresholds() -> None:
    assert band_for_score(60.0) == "critical"
    assert band_for_score(59.999) == "high"
    assert band_for_score(35.0) == "high"
    assert band_for_score(34.999) == "medium"
    assert band_for_score(15.0) == "medium"
    assert band_for_score(14.999) == "low"


def test_compute_score_matches_formula() -> None:
    assert compute_score(v=1.0, f=0.5, e=1.0, k=1.0, u=1.0) == 50.0
