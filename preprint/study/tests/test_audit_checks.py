"""Pins the direction of the step 3 audit findings (synthetic data only)."""

from study.audit_checks import (
    endpoint_revision,
    prospective_alarm_rates,
    severe_share,
    zero_days_dropped_at_end,
)


def test_in_control_ward_alerts_far_more_often_than_the_label_implies() -> None:
    rates = prospective_alarm_rates(range(3), step=6)
    assert rates["any_alert"] > 0.05  # a "95%" label suggests at most 5% of days


def test_latest_smoothed_points_are_revised_later() -> None:
    assert endpoint_revision(1) > 0.0


def test_severe_categories_dominate_the_score() -> None:
    s = severe_share(2)
    assert s["score_E_to_I"] > 2 * s["events_E_to_I"]


def test_trailing_quiet_days_are_not_in_the_series() -> None:
    assert zero_days_dropped_at_end()
