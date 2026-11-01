"""Risk velocity and acceleration over daily weighted harm scores.

The arithmetic is pinned by tests. Presentation (status colours, emoji, alert copy) stays with
the dashboard.
"""

from dataclasses import dataclass
from enum import Enum
from typing import cast

import numpy as np
import pandas as pd

TREND_RUN_DAYS = 6
"""Days in a row the smoothed trend line must rise before the status reports a rising trend.

Six rising points in a row is used as a run-chart convention (general statistical
process control practice); it is not yet tied to a published source. It is judged on the same
smoothed "Trend" line the dashboard chart draws, so the status can never contradict the chart.
"""

CONFIDENCE_BY_SIGMA: dict[float, str] = {1: "68%", 2: "95%", 3: "99.7%"}


@dataclass(frozen=True)
class KineticSeries:
    daily: pd.DataFrame
    """One row per Date: weighted_score, raw_level, smooth, velocity, acceleration."""
    mean: float
    std: float
    ucl: float
    """Upper control limit for the smoothed line: mean + sigma * limit_sd."""
    limit_sd: float = 0.0
    """Spread of a ``window``-day average: std / sqrt(window). Used for ucl and for z."""


class Tolerance(Enum):
    OUTSIDE = "OUTSIDE TOLERANCE"
    MARGINAL = "MARGINAL VARIANCE"
    WITHIN = "WITHIN TOLERANCE"
    NO_DATA = "NO DATA"


@dataclass(frozen=True)
class StrategicStatus:
    z_score: float
    tolerance: Tolerance
    confidence: str
    """Label for sigma. Values outside 1-3 fall back to "95%"."""
    rising_trend: bool = False
    """True when the trend line rose every day for the last ``TREND_RUN_DAYS`` days."""


def calculate_risk_kinetics(df: pd.DataFrame, window: int, sigma: float) -> KineticSeries:
    """Aggregate events per day, then smooth and differentiate.

    ``df`` needs ``Date``, ``weighted_score`` and ``raw_level`` (see ``add_harm_scores``).
    The days are reindexed to a complete daily calendar from the first to the last event:
    a day with no events counts as zero (``weighted_score`` and ``raw_level`` both 0), so the
    x axis is calendar-linear and every rate, mean, limit and velocity is per calendar day.
    Velocity and acceleration are differences over ``window`` days, divided by ``window``.

    ``smooth`` is a trailing moving average: ``rolling(window, min_periods=window).mean()``,
    not centred. There is no value before a full window of ``window`` days. Trailing is
    chosen by logic only (monitoring needs a value for today, which a centred window cannot
    give); no source was consulted on trailing versus centred.

    ``mean`` and ``std`` come from the daily ``weighted_score`` (the process sd, not the sd
    of the smoothed line). The limit is drawn for the smoothed line, so its spread is that
    of an average of ``window`` days: ``limit_sd = std / sqrt(window)`` and
    ``ucl = mean + sigma * limit_sd``. Sources: NIST/SEMATECH e-Handbook 6.3.2.4 and SAS/QC
    EWMACHART documentation (vendor) give the weight r = 2/(w+1) for a w-day average; the
    sigma/sqrt(w) form used here is our own algebra from them, not quoted from either.
    Example: a 7-day average at 2 sigma has its limit at mean + 0.76 daily sd
    (2 / sqrt(7) = 0.756). Adjacent points share window-1 days, so they are not independent.
    """
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")

    daily = df.groupby("Date").agg({"weighted_score": "sum", "raw_level": "mean"}).reset_index()
    if not daily.empty:
        calendar = pd.date_range(daily["Date"].min(), daily["Date"].max(), freq="D", name="Date")
        daily = (
            daily.set_index("Date")
            .reindex(calendar, fill_value=0.0)
            .reset_index()
            .astype({"weighted_score": float, "raw_level": float})
        )
    daily["smooth"] = daily["weighted_score"].rolling(window, min_periods=window).mean()
    daily["velocity"] = daily["smooth"].diff(window) / window
    daily["acceleration"] = daily["velocity"].diff(window) / window

    scores = cast(pd.Series, daily["weighted_score"])
    mean = float(scores.mean())
    std = float(cast(float, scores.std()))
    limit_sd = std / float(np.sqrt(window))
    return KineticSeries(daily=daily, mean=mean, std=std, ucl=mean + sigma * limit_sd, limit_sd=limit_sd)


def classify(
    daily: pd.DataFrame, mean: float, std: float, sigma: float, window: int
) -> StrategicStatus:
    """Place the latest complete smoothed value against the risk appetite.

    "Latest complete" is the last row with no NaN in any column. ``smooth`` starts at day
    ``window``, velocity ``window`` days later and acceleration ``window`` days after that,
    so a period shorter than 3 x window days is NO_DATA. The z-score is
    ``(smooth - mean) / (std / sqrt(window))``, the same scale as the limit, so the chart
    line is over the limit exactly when ``z > sigma``. With ``std == 0`` the z-score is inf
    or nan. See ``calculate_risk_kinetics`` for sources.

    Trend rule (plain words): the status also looks at direction. If the smoothed trend
    line rose on each of the last ``TREND_RUN_DAYS`` days, a ward whose latest day is within
    normal variation is reported as MARGINAL, not WITHIN. The trend can only raise the
    status to MARGINAL; it never lowers one, and never overrides OUTSIDE.
    """
    confidence = CONFIDENCE_BY_SIGMA.get(sigma, "95%")
    complete = daily.dropna()
    if complete.empty:
        return StrategicStatus(z_score=0.0, tolerance=Tolerance.NO_DATA, confidence="N/A")

    latest = float(complete.iloc[-1]["smooth"])
    with np.errstate(divide="ignore", invalid="ignore"):
        z = float(np.float64(latest - mean) / (np.float64(std) / np.sqrt(window)))

    if z > sigma:
        tolerance = Tolerance.OUTSIDE
    elif z > sigma * 0.7:
        tolerance = Tolerance.MARGINAL
    else:
        tolerance = Tolerance.WITHIN
    rising = has_rising_trend(daily)
    if rising and tolerance is Tolerance.WITHIN:
        tolerance = Tolerance.MARGINAL
    return StrategicStatus(
        z_score=z, tolerance=tolerance, confidence=confidence, rising_trend=rising
    )


def has_rising_trend(daily: pd.DataFrame, run_days: int = TREND_RUN_DAYS) -> bool:
    """True if ``smooth`` rose on each of the last ``run_days`` consecutive days."""
    smooth = daily["smooth"].to_numpy(dtype=float)
    if len(smooth) < run_days + 1:
        return False
    steps = np.diff(smooth[-(run_days + 1) :])
    return bool(np.all(steps > 0))
