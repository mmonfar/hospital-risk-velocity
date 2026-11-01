"""Characterisation tests: values pinned from the first release of the engine."""

import math

import pandas as pd
import pytest
from risk_kinematics import Tolerance, calculate_risk_kinetics, classify

from .conftest import flat_log, make_log, random_log, spike_log


@pytest.mark.parametrize(
    ("window", "sigma", "ucl", "velocity", "acceleration", "complete_days", "confidence", "z"),
    [
        (3, 2, 84.38458021172417, 10.888888888888891, 6.9259259259259265, 32, "95%", 0.4993145987182337),
        (7, 2, 71.47395266348202, -0.8775510204081627, 0.07288629737609341, 20, "95%", -0.45529454502392547),
        (7, 1, 59.23697633174101, -0.8775510204081627, 0.07288629737609341, 20, "68%", -0.45529454502392547),
        (13, 3, 73.93845714536712, 0.011834319526627177, 0.019572143832498855, 2, "99.7%", 0.02569960441950416),
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
    z: float,
) -> None:
    k = calculate_risk_kinetics(cyclic, window, sigma)
    assert k.mean == pytest.approx(47.0)
    assert k.std == pytest.approx(32.37599617317015)
    assert k.ucl == pytest.approx(ucl)

    complete = k.daily.dropna()
    assert len(complete) == complete_days
    assert complete.iloc[-1]["velocity"] == pytest.approx(velocity)
    assert complete.iloc[-1]["acceleration"] == pytest.approx(acceleration)

    s = classify(k.daily, k.mean, k.std, sigma, window)
    assert s.z_score == pytest.approx(z)
    assert s.tolerance is Tolerance.WITHIN
    assert s.confidence == confidence


def test_spike_is_outside_tolerance() -> None:
    k = calculate_risk_kinetics(spike_log(), 3, 1)
    assert classify(k.daily, k.mean, k.std, 1, 3).tolerance is Tolerance.OUTSIDE


def test_period_shorter_than_two_windows_is_no_data() -> None:
    k = calculate_risk_kinetics(make_log([["A"]] * 10), 7, 2)
    s = classify(k.daily, k.mean, k.std, 2, 7)
    assert s.tolerance is Tolerance.NO_DATA
    assert s.confidence == "N/A"


def test_zero_std_gives_nan_z_and_within_tolerance() -> None:
    k = calculate_risk_kinetics(flat_log(), 3, 2)
    s = classify(k.daily, k.mean, k.std, 2, 3)
    assert k.std == 0
    assert math.isnan(s.z_score)
    assert s.tolerance is Tolerance.WITHIN


def test_non_integer_sigma_is_labelled_95_percent() -> None:
    """Quirk kept from the original: the label ignores sigma values outside 1-3."""
    k = calculate_risk_kinetics(spike_log(), 3, 1.5)
    assert classify(k.daily, k.mean, k.std, 1.5, 3).confidence == "95%"


def test_window_must_be_positive() -> None:
    with pytest.raises(ValueError, match="window"):
        calculate_risk_kinetics(spike_log(), 0, 2)


def test_limit_formula_is_mean_plus_sigma_times_std_over_root_window(cyclic: pd.DataFrame) -> None:
    for window, sigma in [(3, 2), (7, 2), (7, 1), (15, 3)]:
        k = calculate_risk_kinetics(cyclic, window, sigma)
        assert k.limit_sd == pytest.approx(k.std / math.sqrt(window))
        assert k.ucl == pytest.approx(k.mean + sigma * k.std / math.sqrt(window))
    k7 = calculate_risk_kinetics(cyclic, 7, 2)
    assert (k7.ucl - k7.mean) / k7.std == pytest.approx(0.756, abs=1e-3)  # 0.76 daily sd


@pytest.mark.parametrize("window", [1, 3, 7, 15])
def test_no_smooth_before_a_full_window(cyclic: pd.DataFrame, window: int) -> None:
    smooth = calculate_risk_kinetics(cyclic, window, 2).daily["smooth"]
    assert smooth.iloc[: window - 1].isna().all()
    assert smooth.iloc[window - 1 :].notna().all()
    assert smooth.iloc[window - 1] == pytest.approx(cyclic.groupby("Date")["weighted_score"].sum().iloc[:window].mean())


@pytest.mark.parametrize("window", [3, 7])
def test_no_data_below_three_windows(window: int) -> None:
    need = 3 * window
    short = calculate_risk_kinetics(make_log([["A"], ["I"]] * 30)[lambda d: d["Date"] < pd.Timestamp("2025-01-01") + pd.Timedelta(days=need - 1)], window, 2)
    assert len(short.daily) == need - 1
    assert classify(short.daily, short.mean, short.std, 2, window).tolerance is Tolerance.NO_DATA
    enough = calculate_risk_kinetics(make_log([["A"], ["I"]] * 30)[lambda d: d["Date"] < pd.Timestamp("2025-01-01") + pd.Timedelta(days=need)], window, 2)
    assert classify(enough.daily, enough.mean, enough.std, 2, window).tolerance is not Tolerance.NO_DATA


@pytest.mark.parametrize("window", [3, 7, 15])
@pytest.mark.parametrize("sigma", [1, 2, 3])
@pytest.mark.parametrize("seed", range(6))
def test_status_and_chart_cannot_disagree(window: int, sigma: int, seed: int) -> None:
    k = calculate_risk_kinetics(random_log(seed, days=70), window, sigma)
    s = classify(k.daily, k.mean, k.std, sigma, window)
    assert s.tolerance is not Tolerance.NO_DATA
    last_line = float(k.daily.dropna().iloc[-1]["smooth"])
    assert (last_line > k.ucl) == (s.z_score > sigma)
    assert (s.tolerance is Tolerance.OUTSIDE) == (last_line > k.ucl)
