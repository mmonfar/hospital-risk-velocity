"""Presentation of risk-kinematics results: status colours, directive copy, labels.

Status colours, prompt copy and momentum labels live here. Every number it shows comes from
``risk_kinematics``; nothing here computes a score, a limit or a classification.

Brand notes: state is carried by an explicit text
label first; colour only reinforces it. The original emoji prefixes are dropped because
the identity bans emoji in body text.
"""

from dataclasses import dataclass
from typing import cast

import pandas as pd
from risk_kinematics import TREND_RUN_DAYS, StrategicStatus, Tolerance

# ── Colours ───────────────────────────────────────────────────────────────────
# Brand colours (mmonfar. teal and ink).
TEAL = "#008080"
INK = "#17242B"
INK_2 = "rgba(23, 36, 43, 0.62)"  # canvas at 62%, the brand's secondary-text rule

# NON-BRAND semantic constants. The identity has one accent and no red or amber on
# purpose; these two are this app's own traffic-light states for "outside tolerance" and
# "marginal", kept local exactly as staff_planner_app does. Always paired with a label.
RED = "#b3402f"
AMBER = "#c98a1b"

# Momentum is "rising" above this acceleration, "cooling" below its negative (original
# app.py threshold). A display cut-off on a value risk_kinematics computed.
MOMENTUM_DEADBAND = 0.01


STATUS_RULE_BODY = (
    "The latest average over the chosen window is compared with the normal range for the "
    "period (the limit is set for an average, not for one day), and the trend line "
    "is checked too. If the trend line has gone up every day for the last {days} days, the "
    "status is at least Marginal variance, even when the latest average looks normal. "
    "A rising trend never lowers an alert."
)
STATUS_RULE = "How the status is decided: " + STATUS_RULE_BODY


def status_rule_body(days: int = TREND_RUN_DAYS) -> str:
    """The rule without its title, for the "How the status is decided" card."""
    return STATUS_RULE_BODY.format(days=days)


def status_rule(days: int = TREND_RUN_DAYS) -> str:
    """The status rule in plain words, for the tooltip."""
    return STATUS_RULE.format(days=days)


@dataclass(frozen=True)
class StatusView:
    label: str
    """Exactly ``Tolerance.value``: the UI never renames the engine's classification."""
    colour: str
    directive: str


def status_view(status: StrategicStatus) -> StatusView:
    """How one ``StrategicStatus`` is shown. Copy follows the original prompts."""
    t = status.tolerance
    if t is Tolerance.OUTSIDE:
        colour = RED
        directive = (
            f"Alert: risk exceeds the {status.confidence} stability threshold. Intervene now."
        )
    elif t is Tolerance.MARGINAL:
        colour = AMBER
        if status.rising_trend:
            directive = (
                f"Watch: the trend has risen for {TREND_RUN_DAYS} days in a row. Brief unit leads."
            )
        else:
            directive = "Watch: risk is trending toward the upper limit. Brief unit leads."
    elif t is Tolerance.WITHIN:
        colour = TEAL
        directive = "Stable: risk is within normal historical variation."
    else:
        colour = INK_2
        directive = "No complete days in this period. Widen the date range."
    return StatusView(label=t.value, colour=colour, directive=directive)


@dataclass(frozen=True)
class MomentumView:
    label: str
    context: str
    colour: str


def momentum_view(daily: pd.DataFrame, rising_trend: bool = False) -> MomentumView:
    """Label the latest complete day's acceleration (from ``calculate_risk_kinetics``).

    The card always says it is about the latest day and states the trend alongside, so a
    cooling latest day can never read as "all clear" while the trend line is still rising.
    """
    complete = daily.dropna()
    if complete.empty:
        return MomentumView("N/A", "Not enough days for a trend", INK_2)
    accel = float(complete.iloc[-1]["acceleration"])
    trend = (
        f"Trend: rising for {TREND_RUN_DAYS} days"
        if rising_trend
        else f"Trend: not rising for {TREND_RUN_DAYS} days"
    )
    if accel > MOMENTUM_DEADBAND:
        return MomentumView("Increasing", f"Latest day: accelerating. {trend}", RED)
    if accel < -MOMENTUM_DEADBAND:
        # Cooling on the latest day is not reassurance while the trend is rising.
        colour = AMBER if rising_trend else TEAL
        return MomentumView("Decreasing", f"Latest day: cooling. {trend}", colour)
    return MomentumView("Flat", f"Latest day: steady. {trend}", INK)


@dataclass(frozen=True)
class MomentumLines:
    """Two honest lines for the Momentum card: the latest day and the trend, with windows."""

    day: str
    trend: str
    colour: str


def _direction(value: float, up: str, down: str, flat: str) -> str:
    if value > MOMENTUM_DEADBAND:
        return up
    if value < -MOMENTUM_DEADBAND:
        return down
    return flat


def momentum_lines(daily: pd.DataFrame, window: int) -> MomentumLines:
    """Latest day (acceleration) and the ``window``-day trend (velocity), from the engine.

    The two can differ: risk can still be rising over the window while the latest day eases
    off. Both are always shown, so the card never reads "all clear" next to a rising chart.
    """
    complete = daily.dropna()
    if complete.empty:
        return MomentumLines("Latest day: n/a", f"{window}-day trend: n/a", INK_2)
    last = complete.iloc[-1]
    day = _direction(float(last["acceleration"]), "up", "down", "steady")
    trend = _direction(float(last["velocity"]), "rising", "falling", "flat")
    colour = TEAL
    if trend == "rising":
        colour = RED if day == "up" else AMBER
    elif day == "up":
        colour = AMBER
    elif trend == "flat" and day == "steady":
        colour = INK
    return MomentumLines(f"Latest day: {day}", f"{window}-day trend: {trend}", colour)


def status_reason(status: StrategicStatus, sigma: float) -> str:
    """One plain line: why the status is what it is (states the trend rule when it applied)."""
    t = status.tolerance
    if t is Tolerance.NO_DATA:
        return "Not enough complete days in this period."
    if t is Tolerance.OUTSIDE:
        return f"The latest average is above the {sigma:g} σ limit."
    if t is Tolerance.MARGINAL:
        if status.z_score > sigma * 0.7:
            return f"The latest average is within 30% of the {sigma:g} σ limit."
        return f"Raised by the trend: it rose {TREND_RUN_DAYS} days in a row."
    return "The latest average is inside the normal range."


def headline(status: StrategicStatus, sigma: float, scope: str) -> str:
    """The hero card title: what the chart shows, in words, from the engine status."""
    t = status.tolerance
    if t is Tolerance.NO_DATA:
        return f"Not enough days to judge risk in {scope}"
    if t is Tolerance.OUTSIDE:
        return f"Risk in {scope} is above the limit"
    if t is Tolerance.MARGINAL:
        if status.z_score > sigma * 0.7:
            return f"Risk in {scope} is close to the limit"
        return f"Risk in {scope} has risen {TREND_RUN_DAYS} days in a row"
    return f"Risk in {scope} is within its normal range"


def hotspot(df: pd.DataFrame) -> tuple[str, str]:
    """(unit, category) with the largest weighted-score total; ("N/A", "N/A") if empty."""
    if df.empty:
        return ("N/A", "N/A")
    totals = cast(pd.Series, df.groupby(["Unit", "Category"])["weighted_score"].sum())
    unit, category = cast(tuple[str, str], totals.idxmax())
    return (str(unit), str(category))
