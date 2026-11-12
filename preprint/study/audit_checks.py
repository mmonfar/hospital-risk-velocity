"""Step 3 audit checks: quick, seeded, synthetic-only probes of the risk_kinematics engine.

These are not the simulation study (steps 4-5). They put rough numbers on the audit's
claims so each issue in review/methodology-audit.md is backed by a reproducible figure.
No real incident data is used; every log here is drawn from a seeded generator.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from risk_kinematics import HARM_LEVELS, add_harm_scores, calculate_risk_kinetics, classify
from risk_kinematics.kinetics import Tolerance

# Synthetic severity mix, skewed like published reporting (about 70% no harm, <1% severe).
LEVEL_PROBS = np.array([0.20, 0.25, 0.25, 0.15, 0.08, 0.04, 0.02, 0.007, 0.003])
LEVEL_PROBS = LEVEL_PROBS / LEVEL_PROBS.sum()


def null_log(seed: int, days: int = 240, mean_events: float = 2.0, k: float = 2.0) -> pd.DataFrame:
    """Stationary in-control ward: negative-binomial daily counts, fixed severity mix."""
    rng = np.random.default_rng(seed)
    p = k / (k + mean_events)
    counts = rng.negative_binomial(k, p, size=days)
    dates = pd.date_range("2025-01-01", periods=days, freq="D")
    rows = [
        {"Date": d, "Harm_Level": lvl}
        for d, n in zip(dates, counts, strict=True)
        for lvl in rng.choice(list(HARM_LEVELS), size=n, p=LEVEL_PROBS)
    ]
    return add_harm_scores(pd.DataFrame(rows))


def prospective_alarm_rates(
    seeds: range, window: int = 7, sigma: float = 2.0, burn_in: int = 60, step: int = 3
) -> dict[str, float]:
    """Re-run the engine as a user would each day (data up to that day) on in-control logs.

    Returns the share of evaluated days that were OUTSIDE, MARGINAL (any cause), and
    MARGINAL caused only by the rising-trend rule.
    """
    n = outside = marginal = trend_only = 0
    for seed in seeds:
        log = null_log(seed)
        last = log["Date"].max()
        for end in pd.date_range(log["Date"].min() + pd.Timedelta(days=burn_in), last)[::step]:
            k = calculate_risk_kinetics(log[log["Date"] <= end], window, sigma)
            s = classify(k.daily, k.mean, k.std, sigma)
            if s.tolerance is Tolerance.NO_DATA:
                continue
            n += 1
            outside += s.tolerance is Tolerance.OUTSIDE
            marginal += s.tolerance is Tolerance.MARGINAL
            trend_only += s.tolerance is Tolerance.MARGINAL and s.z_score <= 0.7 * sigma
    return {
        "days": float(n),
        "outside": outside / n,
        "marginal": marginal / n,
        "trend_only_marginal": trend_only / n,
        "any_alert": (outside + marginal) / n,
    }


def endpoint_revision(seed: int, window: int = 7, lag: int = 7) -> float:
    """Mean absolute change in a day's ``smooth`` between 'seen on the day' and 'seen lag days later',
    as a share of the series' mean score. Non-zero means the latest points get rewritten."""
    log = null_log(seed)
    dates = pd.date_range(log["Date"].min() + pd.Timedelta(days=30), log["Date"].max() - pd.Timedelta(days=lag))
    diffs = []
    for d in dates[::5]:
        now = calculate_risk_kinetics(log[log["Date"] <= d], window, 2).daily.set_index("Date")
        later = calculate_risk_kinetics(log[log["Date"] <= d + pd.Timedelta(days=lag)], window, 2).daily.set_index("Date")
        if d in now.index and d in later.index:
            diffs.append(abs(later.loc[d, "smooth"] - now.loc[d, "smooth"]))
    k = calculate_risk_kinetics(log, window, 2)
    return float(np.mean(diffs) / k.mean)


def severe_share(seed: int) -> dict[str, float]:
    """Share of events vs share of total weighted score coming from harm categories E-I."""
    log = null_log(seed, days=2000)
    harm = log["Harm_Level"].isin(list("EFGHI"))
    return {
        "events_E_to_I": float(harm.mean()),
        "score_E_to_I": float(log.loc[harm, "weighted_score"].sum() / log["weighted_score"].sum()),
        "A_reports_equal_one_I": float(81 / 1),
    }


def zero_days_dropped_at_end() -> bool:
    """True if trailing quiet days are invisible: the calendar stops at the last event."""
    log = add_harm_scores(pd.DataFrame({"Date": pd.to_datetime(["2025-01-01", "2025-01-02"]), "Harm_Level": ["C", "C"]}))
    return calculate_risk_kinetics(log, 1, 2).daily["Date"].max() == pd.Timestamp("2025-01-02")


if __name__ == "__main__":
    print("prospective null rates w=7 s=2:", prospective_alarm_rates(range(20)))
    print("prospective null rates w=7 s=3:", prospective_alarm_rates(range(20), sigma=3.0))
    print("endpoint revision (share of mean):", round(endpoint_revision(1), 3))
    print("severe share:", severe_share(2))
    print("trailing zero days dropped:", zero_days_dropped_at_end())
