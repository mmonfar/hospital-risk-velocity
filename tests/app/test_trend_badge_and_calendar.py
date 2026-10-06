"""The badge never contradicts the chart; charts use a complete daily calendar. Synthetic only."""

from typing import cast

import pandas as pd

from clinical_risk_dashboard import charts, presentation
from clinical_risk_dashboard.sample_data import generate_incidents
from risk_kinematics import Tolerance, add_harm_scores, calculate_risk_kinetics, classify


def test_rising_trend_ward_never_reads_within_tolerance() -> None:
    # noisy baseline, then six climbing days; latest day alone is within the normal range
    levels = ["C", "F", "B", "G", "D", "A", "H", "C"] * 6 + ["B", "C", "D", "E", "F", "G", "G"]
    log = add_harm_scores(
        pd.DataFrame(
            {
                "Date": pd.date_range("2025-01-01", periods=len(levels), freq="D"),
                "Harm_Level": levels,
            }
        )
    )
    k = calculate_risk_kinetics(log, 3, 3)
    status = classify(k.daily, k.mean, k.std, 3)
    view = presentation.status_view(status)
    assert status.rising_trend
    assert view.label != Tolerance.WITHIN.value
    assert "risen" in view.directive
    # the chart marks the same trend the badge reacted to
    fig = charts.spc_chart(k.daily, k.ucl, 3, status.rising_trend)
    assert "RISING TREND" in str(fig.to_json())


def test_status_rule_tooltip_is_plain_words() -> None:
    rule = presentation.status_rule()
    assert "every day" in rule
    assert "6 days" in rule
    assert "Marginal" in rule


def test_charts_use_a_complete_daily_calendar() -> None:
    df = generate_incidents(seed=3)
    gap_days = pd.DatetimeIndex(["2025-01-10", "2025-01-11"])
    sparse = cast(pd.DataFrame, df.loc[~df["Date"].isin(list(gap_days))])
    daily = calculate_risk_kinetics(sparse, 3, 2).daily
    xs = pd.Series(pd.to_datetime(list(charts.spc_chart(daily, 10.0, 2).to_dict()["data"][0]["x"])))
    assert (xs.diff().dropna() == pd.Timedelta(days=1)).all()
    assert len(charts.intensity_matrix(sparse).to_dict()["data"]) == 1
