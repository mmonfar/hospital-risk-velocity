"""The badge never contradicts the trend rule. Synthetic only."""

import pandas as pd

from clinical_risk_dashboard import presentation
from risk_kinematics import Tolerance, add_harm_scores, calculate_risk_kinetics, classify


def test_rising_trend_ward_never_reads_within_tolerance() -> None:
    # noisy baseline, then six climbing days; latest day alone is within the normal range
    levels = ["C", "F", "B", "G", "D", "A", "H", "C"] * 6 + ["B", "B", "B", "C", "D", "E", "F", "G", "G"]
    log = add_harm_scores(
        pd.DataFrame(
            {
                "Date": pd.date_range("2025-01-01", periods=len(levels), freq="D"),
                "Harm_Level": levels,
            }
        )
    )
    k = calculate_risk_kinetics(log, 3, 3)
    status = classify(k.daily, k.mean, k.std, 3, 3)
    view = presentation.status_view(status)
    assert status.rising_trend
    assert view.label != Tolerance.WITHIN.value
    assert "risen" in view.directive


def test_status_rule_tooltip_is_plain_words() -> None:
    rule = presentation.status_rule()
    assert "every day" in rule
    assert "6 days" in rule
    assert "Marginal" in rule
