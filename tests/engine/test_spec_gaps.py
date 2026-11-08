"""Engine rules the spec promises that no other test checked on its own. Synthetic data only."""

import math

import numpy as np
import pandas as pd
import pytest
from risk_kinematics import (
    Tolerance,
    add_harm_scores,
    calculate_risk_kinetics,
    classify,
    has_rising_trend,
)

from .conftest import make_log


def test_slope_velocity_is_the_daily_change_of_the_smooth_line() -> None:
    # Daily scores 1, 4, 9, 16, 25 (A..E squared). Window 1: velocity = day-to-day change.
    daily = calculate_risk_kinetics(make_log([["A"], ["B"], ["C"], ["D"], ["E"]]), 1, 2).daily
    assert list(daily["velocity"].iloc[1:]) == [3.0, 5.0, 7.0, 9.0]


def test_jerk_acceleration_is_the_change_of_velocity() -> None:
    # Squares have a constant second difference of 2. (The engine has no third derivative.)
    daily = calculate_risk_kinetics(make_log([["A"], ["B"], ["C"], ["D"], ["E"]]), 1, 2).daily
    assert list(daily["acceleration"].iloc[2:]) == [2.0, 2.0, 2.0]


def test_velocity_is_divided_by_the_window() -> None:
    # Window 2, scores 1,1,1,1,9,9: smooth 1,1,1,5,9 from day 2; last velocity = (9-1)/2 = 4.
    daily = calculate_risk_kinetics(make_log([["A"]] * 4 + [["C"]] * 2), 2, 2).daily
    assert daily["velocity"].iloc[-1] == pytest.approx((daily["smooth"].iloc[-1] - daily["smooth"].iloc[-3]) / 2)
    assert daily["velocity"].iloc[-1] == pytest.approx(4.0)


def test_squared_weights_for_every_level() -> None:
    out = add_harm_scores(pd.DataFrame({"Harm_Level": list("ABCDEFGHI")}))
    assert list(out["weighted_score"]) == [n * n for n in range(1, 10)]


def test_events_on_one_day_are_summed_with_squared_weights() -> None:
    daily = calculate_risk_kinetics(make_log([["B", "C"]]), 1, 2).daily
    assert daily["weighted_score"].iloc[0] == 4 + 9


def test_empty_series_is_no_data_and_does_not_raise() -> None:
    empty = add_harm_scores(pd.DataFrame({"Date": pd.to_datetime([]), "Harm_Level": []}))
    k = calculate_risk_kinetics(empty, 3, 2)
    assert k.daily.empty
    assert classify(k.daily, k.mean, k.std, 2, 3).tolerance is Tolerance.NO_DATA
    assert has_rising_trend(k.daily) is False


def test_one_data_point_is_no_data_with_no_spread() -> None:
    k = calculate_risk_kinetics(make_log([["E"]]), 1, 2)
    assert len(k.daily) == 1
    assert math.isnan(k.std)
    assert classify(k.daily, k.mean, k.std, 2, 1).tolerance is Tolerance.NO_DATA


def test_ties_do_not_count_as_rising() -> None:
    flat = pd.DataFrame({"smooth": [1.0, 2.0, 3.0, 4.0, 5.0, 5.0, 6.0]})
    assert has_rising_trend(flat) is False  # one equal step breaks the run of 6
    strict = pd.DataFrame({"smooth": [9.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})
    assert has_rising_trend(strict) is True


def test_exactly_six_rising_days_is_flagged_and_five_is_not() -> None:
    six = pd.DataFrame({"smooth": np.arange(7, dtype=float)})  # 6 steps
    five = pd.DataFrame({"smooth": np.arange(6, dtype=float)})  # 5 steps
    assert has_rising_trend(six) is True
    assert has_rising_trend(five) is False
