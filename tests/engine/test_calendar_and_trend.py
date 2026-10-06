"""Calendar-linear daily series and the rising-trend rule. Synthetic data only."""

import pandas as pd
import pytest

from risk_kinematics import Tolerance, calculate_risk_kinetics, classify, has_rising_trend

from .conftest import flat_log, make_log, spike_log


def rising_ward() -> pd.DataFrame:
    """48 noisy days, then six climbing days; the latest day is still within normal range."""
    base = [["C"], ["F"], ["B"], ["G"], ["D"], ["A"], ["H"], ["C"]] * 6
    return make_log(base + [["B"], ["C"], ["D"], ["E"], ["F"], ["G"], ["G"]])


def test_zero_event_days_are_kept_as_zero() -> None:
    daily = calculate_risk_kinetics(make_log([["C"], [], [], ["C"], ["C"]]), 1, 2).daily
    assert list(daily["Date"]) == list(pd.date_range("2025-01-01", periods=5, freq="D"))
    assert list(daily["weighted_score"].iloc[1:3]) == [0.0, 0.0]
    assert list(daily["raw_level"].iloc[1:3]) == [0.0, 0.0]
    assert (daily["Date"].diff().dropna() == pd.Timedelta(days=1)).all()


def test_gaps_lower_the_per_calendar_day_mean() -> None:
    gappy = calculate_risk_kinetics(make_log([["E"], [], [], [], ["E"]]), 1, 2)
    dense = calculate_risk_kinetics(make_log([["E"], ["E"]]), 1, 2)
    assert len(gappy.daily) == 5
    assert gappy.mean < dense.mean


def test_dense_log_is_unchanged_by_reindexing(cyclic: pd.DataFrame) -> None:
    assert len(calculate_risk_kinetics(cyclic, 3, 2).daily) == 40


def test_rising_trend_is_flagged_and_never_within() -> None:
    k = calculate_risk_kinetics(rising_ward(), 3, 3)
    s = classify(k.daily, k.mean, k.std, 3)
    assert s.rising_trend
    assert s.z_score < 0.7 * 3  # the latest day alone would read WITHIN
    assert s.tolerance is Tolerance.MARGINAL


def test_flat_and_falling_are_not_flagged() -> None:
    k = calculate_risk_kinetics(flat_log(), 3, 2)
    assert not classify(k.daily, k.mean, k.std, 2).rising_trend
    falling = make_log([["F"], ["E"], ["D"], ["C"], ["B"], ["A"], ["A"], ["A"], ["A"]] * 3)
    k2 = calculate_risk_kinetics(falling, 3, 2)
    assert not has_rising_trend(k2.daily.iloc[:8])


def test_trend_never_lowers_outside() -> None:
    k = calculate_risk_kinetics(spike_log(), 3, 1)
    assert classify(k.daily, k.mean, k.std, 1).tolerance is Tolerance.OUTSIDE


@pytest.mark.parametrize("run_days", [1, 3, 6])
def test_short_series_is_not_flagged(run_days: int) -> None:
    daily = pd.DataFrame({"smooth": [1.0, 2.0]})
    assert has_rising_trend(daily, run_days) is (run_days == 1)
