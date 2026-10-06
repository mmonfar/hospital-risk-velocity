"""The UI's status, momentum and hotspot views agree with risk_kinematics. Synthetic data only."""

from typing import cast

import pandas as pd
import pytest

from clinical_risk_dashboard import presentation
from clinical_risk_dashboard.sample_data import UNITS, generate_incidents
from risk_kinematics import StrategicStatus, Tolerance, calculate_risk_kinetics, classify


@pytest.mark.parametrize("tolerance", list(Tolerance))
def test_every_tolerance_has_a_view_labelled_with_the_engine_value(tolerance: Tolerance) -> None:
    view = presentation.status_view(StrategicStatus(1.0, tolerance, "95%"))
    assert view.label == tolerance.value
    assert view.directive


def test_state_colours_keep_the_traffic_light_order() -> None:
    def colour(t: Tolerance) -> str:
        return presentation.status_view(StrategicStatus(0.0, t, "95%")).colour

    assert colour(Tolerance.OUTSIDE) == presentation.RED
    assert colour(Tolerance.MARGINAL) == presentation.AMBER
    assert colour(Tolerance.WITHIN) == presentation.TEAL
    assert colour(Tolerance.NO_DATA) == presentation.INK_2


def test_outside_directive_names_the_engine_confidence() -> None:
    view = presentation.status_view(StrategicStatus(4.0, Tolerance.OUTSIDE, "99.7%"))
    assert "99.7%" in view.directive


SCOPES = [None, *UNITS]


@pytest.mark.parametrize("seed", [1, 7, 42])
@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("window", [3, 7, 15])
@pytest.mark.parametrize("sigma", [1, 2, 3])
def test_ui_status_matches_risk_kinematics(
    seed: int, scope: str | None, window: int, sigma: int
) -> None:
    """162 synthetic cases: the label shown is always the engine's own classification."""
    df = generate_incidents(seed=seed)
    if scope is not None:
        df = cast(pd.DataFrame, df[df["Unit"] == scope])
    k = calculate_risk_kinetics(df, window, sigma)
    status = classify(k.daily, k.mean, k.std, sigma)
    view = presentation.status_view(status)

    assert view.label == status.tolerance.value
    # The threshold rule the engine applies, restated: the UI never overrides it.
    if status.tolerance is not Tolerance.NO_DATA and status.z_score == status.z_score:
        if status.z_score > sigma:
            assert status.tolerance is Tolerance.OUTSIDE
        elif status.z_score > 0.7 * sigma:
            assert status.tolerance is Tolerance.MARGINAL
        else:
            # Trend rule: a rising trend lifts WITHIN to MARGINAL.
            expected = Tolerance.MARGINAL if status.rising_trend else Tolerance.WITHIN
            assert status.tolerance is expected


def _daily_with_final_acceleration(accel: float) -> pd.DataFrame:
    return pd.DataFrame({"acceleration": [0.0, accel], "velocity": [0.0, 0.0]})


@pytest.mark.parametrize(
    ("accel", "label"),
    [
        (0.5, "Increasing"),
        (0.011, "Increasing"),
        (0.01, "Flat"),
        (0.0, "Flat"),
        (-0.01, "Flat"),
        (-0.011, "Decreasing"),
    ],
)
def test_momentum_thresholds(accel: float, label: str) -> None:
    assert presentation.momentum_view(_daily_with_final_acceleration(accel)).label == label


def test_momentum_without_complete_days_is_na() -> None:
    daily = pd.DataFrame({"acceleration": [float("nan")]})
    assert presentation.momentum_view(daily).label == "N/A"


def test_hotspot_is_the_largest_unit_category_total() -> None:
    df = pd.DataFrame(
        {
            "Unit": ["A", "A", "B"],
            "Category": ["Fall", "Fall", "Medication"],
            "weighted_score": [4, 4, 9],
        }
    )
    assert presentation.hotspot(df) == ("B", "Medication")
    assert presentation.hotspot(df.iloc[0:0]) == ("N/A", "N/A")


def test_momentum_never_contradicts_a_rising_trend() -> None:
    daily = _daily_with_final_acceleration(-0.5)
    view = presentation.momentum_view(daily, rising_trend=True)
    assert view.label == "Decreasing"
    assert "Latest day" in view.context
    assert "Trend: rising" in view.context
    assert view.colour == presentation.AMBER  # not the reassuring teal
    calm = presentation.momentum_view(daily, rising_trend=False)
    assert "Trend: not rising" in calm.context
    assert calm.colour == presentation.TEAL


def test_ward_with_rising_trend_shows_trend_on_momentum_card() -> None:
    df = generate_incidents(seed=42)
    for unit in UNITS:
        k = calculate_risk_kinetics(cast(pd.DataFrame, df[df["Unit"] == unit]), 7, 2)
        status = classify(k.daily, k.mean, k.std, 2)
        view = presentation.momentum_view(k.daily, status.rising_trend)
        assert ("Trend: rising" in view.context) == status.rising_trend
