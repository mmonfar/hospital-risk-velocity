"""Vectorised replica of risk_kinematics.calculate_risk_kinetics + classify, "re-run every day".

For each analysis day t the engine sees all reports up to day t. Quirks reproduced (protocol M.1):
the calendar runs from the first to the LAST REPORT (not to day t), so quiet trailing days are
invisible (audit issue 8); the centred 7-day smooth is truncated at the last report; mean and
SD (ddof=1) are over all calendar days so far; the status is judged on the last report day;
std == 0 gives z = nan (-> WITHIN) or +-inf; fewer than 15 calendar days gives NO_DATA; a smooth
line that rose 6 days in a row turns WITHIN into MARGINAL. Status codes: 0 NO_DATA, 1 WITHIN,
2 MARGINAL, 3 OUTSIDE. Day t without a new report keeps the previous day's status.
"""

from __future__ import annotations

import numpy as np

NO_DATA, WITHIN, MARGINAL, OUTSIDE = 0, 1, 2, 3
WINDOW = 7
RUN_DAYS = 6


def status(
    x: np.ndarray, n_reports: np.ndarray, sigmas: tuple[float, ...] = (2.0, 3.0)
) -> dict[float, np.ndarray]:
    """Daily status code per sigma for a stream of daily scores x and report counts."""
    x = np.asarray(x, dtype=float)
    t_n = x.size
    out = {s: np.zeros(t_n, dtype=np.int8) for s in sigmas}
    has = np.asarray(n_reports) > 0
    rep = np.flatnonzero(has)
    if rep.size == 0:
        return out
    first = rep[0]
    y = x[first:]
    m = y.size
    cs = np.concatenate(([0.0], np.cumsum(y)))
    cs2 = np.concatenate(([0.0], np.cumsum(y * y)))
    last = rep - first  # relative index of the last calendar day at each evaluation
    n = last + 1
    mean = cs[n] / n
    var = (cs2[n] - cs[n] ** 2 / n) / np.maximum(n - 1, 1)
    constant = np.maximum.accumulate(y)[last] == np.minimum.accumulate(y)[last]
    std = np.where(constant, 0.0, np.sqrt(np.maximum(var, 0.0)))
    d = y[last] - mean
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(
            std > 0,
            d / np.where(std > 0, std, 1.0),
            np.where(d > 0, np.inf, np.where(d < 0, -np.inf, np.nan)),
        )

    # rising trend: last RUN_DAYS+1 smooth values; the last 3 are truncated at the last report
    j = np.arange(RUN_DAYS + 1)
    pos = np.clip(last[:, None] - RUN_DAYS + j[None, :], 0, m - 1)
    lo = np.maximum(pos - 3, 0)
    hi = np.where(j[None, :] >= RUN_DAYS + 1 - 3, (last + 1)[:, None], np.minimum(pos + 4, m))
    smooth = (cs[hi] - cs[lo]) / (hi - lo)
    rising = (last >= RUN_DAYS) & np.all(np.diff(smooth, axis=1) > 0, axis=1)

    eligible = n >= 2 * WINDOW + 1
    idx = np.maximum.accumulate(np.where(has, np.arange(t_n), -1))
    for s in sigmas:
        code = np.where(z > s, OUTSIDE, np.where(z > 0.7 * s, MARGINAL, WITHIN))
        code = np.where((code == WITHIN) & rising, MARGINAL, code)
        code = np.where(eligible, code, NO_DATA).astype(np.int8)
        full = np.zeros(t_n, dtype=np.int8)
        full[rep] = code
        out[s] = np.where(idx >= 0, full[np.maximum(idx, 0)], 0).astype(np.int8)
    return out


def endpoint_revision(x: np.ndarray, start: int, in_control_mean: float) -> float:
    """Mean |smooth(data to t) - smooth(data to t+7)| over days t >= start, / in-control mean.

    start is the 0-based index of the first monitored day. Calendar assumed complete.
    """
    x = np.asarray(x, dtype=float)
    cs = np.concatenate(([0.0], np.cumsum(x)))
    i = np.arange(start, x.size - 7)
    trunc = (cs[i + 1] - cs[i - 3]) / 4
    full = (cs[i + 4] - cs[i - 3]) / 7
    return float(np.mean(np.abs(trunc - full)) / in_control_mean)
