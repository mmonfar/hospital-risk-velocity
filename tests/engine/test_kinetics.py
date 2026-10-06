"""Characterisation tests: pinned reference values."""

import math

import pandas as pd
import pytest

from risk_kinematics import Tolerance, calculate_risk_kinetics, classify

from .conftest import flat_log, make_log, spike_log


@pytest.mark.parametrize(
    ("window", "sigma", "ucl", "velocity", "acceleration", "complete_days", "confidence"),
    [
        (3, 2, 111.7519923463403, 4.166666666666667, 2.9444444444444446, 34, "95%"),
        (7, 2, 111.7519923463403, -1.3367346938775506, -0.3104956268221573, 26, "95%"),
        (7, 1, 79.37599617317015, -1.3367346938775506, -0.3104956268221573, 26, "68%"),
        (15, 3, 144.12798851951044, -0.015000000000000095, 0.011444444444444426, 10, "99.7%"),
    ],
)
def test_pinned_outputs(
    cyclic: pd.DataFrame,
    window: int,
    sigma: int,
    ucl: float,
    velocity: float,
    acceleration: float,
    complete_days: int,
    confidence: str,
) -> None:
    k = calculate_risk_kinetics(cyclic, window, sigma)
    assert k.mean == pytest.approx(47.0)
    assert k.std == pytest.approx(32.37599617317015)
    assert k.ucl == pytest.approx(ucl)

    complete = k.daily.dropna()
    assert len(complete) == complete_days
    assert complete.iloc[-1]["velocity"] == pytest.approx(velocity)
    assert complete.iloc[-1]["acceleration"] == pytest.approx(acceleration)

    s = classify(k.daily, k.mean, k.std, sigma)
    assert s.z_score == pytest.approx(0.5559674489619727)
    assert s.tolerance is Tolerance.WITHIN
    assert s.confidence == confidence


def test_spike_is_outside_tolerance() -> None:
    k = calculate_risk_kinetics(spike_log(), 3, 1)
    assert classify(k.daily, k.mean, k.std, 1).tolerance is Tolerance.OUTSIDE


def test_period_shorter_than_two_windows_is_no_data() -> None:
    k = calculate_risk_kinetics(make_log([["A"]] * 10), 7, 2)
    s = classify(k.daily, k.mean, k.std, 2)
    assert s.tolerance is Tolerance.NO_DATA
    assert s.confidence == "N/A"


def test_zero_std_gives_nan_z_and_within_tolerance() -> None:
    k = calculate_risk_kinetics(flat_log(), 3, 2)
    s = classify(k.daily, k.mean, k.std, 2)
    assert k.std == 0
    assert math.isnan(s.z_score)
    assert s.tolerance is Tolerance.WITHIN


def test_non_integer_sigma_is_labelled_95_percent() -> None:
    """Documented behaviour: the label ignores sigma values outside 1-3."""
    k = calculate_risk_kinetics(spike_log(), 3, 1.5)
    assert classify(k.daily, k.mean, k.std, 1.5).confidence == "95%"


def test_window_must_be_positive() -> None:
    with pytest.raises(ValueError, match="window"):
        calculate_risk_kinetics(spike_log(), 0, 2)
