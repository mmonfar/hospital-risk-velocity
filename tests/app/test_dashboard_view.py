"""Honest momentum, status reason and page parts. Synthetic data only."""

from typing import cast

import pandas as pd
import pytest
from clinical_risk_dashboard import presentation, view
from clinical_risk_dashboard.sample_data import UNITS, generate_incidents
from risk_kinematics import (
    TREND_RUN_DAYS,
    StrategicStatus,
    Tolerance,
    calculate_risk_kinetics,
    classify,
)


def _daily(velocity: float, accel: float) -> pd.DataFrame:
    return pd.DataFrame({"velocity": [0.0, velocity], "acceleration": [0.0, accel]})


def test_momentum_lines_never_hide_a_rising_trend() -> None:
    lines = presentation.momentum_lines(_daily(velocity=2.8, accel=-0.4), 7)
    assert lines.day == "Latest day: down"
    assert lines.trend == "7-day trend: rising"
    assert lines.colour == presentation.AMBER  # not the reassuring teal


@pytest.mark.parametrize(
    ("velocity", "accel", "day", "trend"),
    [(1.0, 0.5, "up", "rising"), (-1.0, -0.5, "down", "falling"), (0.0, 0.0, "steady", "flat")],
)
def test_momentum_lines_words(velocity: float, accel: float, day: str, trend: str) -> None:
    lines = presentation.momentum_lines(_daily(velocity, accel), 3)
    assert lines.day == f"Latest day: {day}"
    assert lines.trend == f"3-day trend: {trend}"


def test_momentum_lines_without_days() -> None:
    empty = pd.DataFrame({"velocity": [float("nan")], "acceleration": [1.0]})
    assert "n/a" in presentation.momentum_lines(empty, 7).day


def test_reason_for_a_trend_raised_status_names_the_rule() -> None:
    status = StrategicStatus(-0.51, Tolerance.MARGINAL, "95%", rising_trend=True)
    text = presentation.status_reason(status, 2)
    assert "trend" in text
    assert str(TREND_RUN_DAYS) in text


def test_every_status_has_a_reason_and_a_headline() -> None:
    for t in Tolerance:
        s = StrategicStatus(1.5, t, "95%")
        assert presentation.status_reason(s, 2)
        assert "CICU" in presentation.headline(s, 2, "CICU")


@pytest.mark.parametrize("unit", UNITS)
def test_hero_and_kpi_parts_build_for_every_unit(unit: str) -> None:
    df = generate_incidents()
    part = cast(pd.DataFrame, df[df["Unit"] == unit])
    k = calculate_risk_kinetics(part, 7, 2)
    status = classify(k.daily, k.mean, k.std, 2, 7)
    reason = presentation.status_reason(status, 2)
    html = view.kpis_html(
        n_reports=len(part),
        period_days=90,
        status=status,
        sigma=2,
        view=presentation.status_view(status),
        reason=reason,
        momentum=presentation.momentum_lines(k.daily, 7),
    )
    assert f"{len(part):,}" in html
    assert reason in html
    pad = (42, 18, 16, 30)
    svg = view.trend_svg(k.daily, k.ucl, status.z_score, 2, unit, w=760, h=300, fs=12, pad=pad)
    assert svg.count("<polyline") == 1
    assert 'stroke-dasharray="6 5"' in svg


def test_stylesheet_embeds_the_local_font_and_no_cdn() -> None:
    css = view.stylesheet()
    assert "data:font/woff2;base64," in css
    assert "{{FONT_B64}}" not in css
    assert "http://" not in css
    assert "https://" not in css
