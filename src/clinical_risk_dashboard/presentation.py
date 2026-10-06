"""Presentation of risk-kinematics results: status colours, directive copy, labels.

Status colours, directive copy and the momentum label. Every number it shows comes from
``risk_kinematics``; nothing here computes a score, a limit or a classification.

Design notes: state is carried by an explicit text
label first; colour only reinforces it. No emoji are used in body text.
"""

from dataclasses import dataclass
from typing import cast

import pandas as pd

from clinical_risk_dashboard import brand as tokens
from risk_kinematics import TREND_RUN_DAYS, StrategicStatus, Tolerance

# ── Colours ───────────────────────────────────────────────────────────────────
# Brand colours come from the bundled theme module, not re-typed here.
TEAL = tokens.TEAL
INK = tokens.CANVAS
INK_2 = "rgba(23, 36, 43, 0.62)"  # canvas at 62%, the theme's secondary-text rule

# Semantic constants outside the theme's single teal accent: the traffic-light states for
# "outside tolerance" and "marginal". Always paired with a text label.
RED = "#b3402f"
AMBER = "#c98a1b"

# Momentum is "rising" above this acceleration, "cooling" below its negative. A display
# cut-off on a value risk_kinematics computed.
MOMENTUM_DEADBAND = 0.01


STATUS_RULE = (
    "How the status is decided: the latest day is compared with the normal range for the "
    "period, and the trend line is checked too. If the trend line has gone up every day "
    "for the last {days} days, the status is at least Marginal variance, even when the "
    "latest day looks normal. A rising trend never lowers an alert."
)


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
    """How one ``StrategicStatus`` is shown. Directive wording per state."""
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


def hotspot(df: pd.DataFrame) -> tuple[str, str]:
    """(unit, category) with the largest weighted-score total; ("N/A", "N/A") if empty."""
    if df.empty:
        return ("N/A", "N/A")
    totals = cast(pd.Series, df.groupby(["Unit", "Category"])["weighted_score"].sum())
    unit, category = cast(tuple[str, str], totals.idxmax())
    return (str(unit), str(category))
