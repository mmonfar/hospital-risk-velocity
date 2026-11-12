"""Extra vectorised replicas (post hoc, added 2 Nov 2026).

shipped_z: daily z of the released method at 48c467f (same arithmetic as study/sim/shipped.py,
returns z instead of a code, so any k can be tested without re-computing).
trailing_status: replica of engine commit c3cee22 (trailing 7-day average; limit and z on the
scale of the average, z = (latest average - mean) / (std / sqrt(window)); status needs 3 x window
= 21 calendar days; rising-trend rule on the trailing average). Status codes as in shipped.py.
Same calendar quirk: the calendar runs from the first to the LAST REPORT.
Synthetic data only.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

import numpy as np

from study.sim.shipped import MARGINAL, NO_DATA, OUTSIDE, RUN_DAYS, WINDOW, WITHIN

ENGINE_ROOT = Path(__file__).resolve().parents[1] / "engine_frozen"


def _z_stats(x: np.ndarray, n_reports: np.ndarray):
    """Shared part: calendar from first to last report; mean, SD (ddof=1) and last-day value per evaluation."""
    x = np.asarray(x, dtype=float)
    has = np.asarray(n_reports) > 0
    rep = np.flatnonzero(has)
    if rep.size == 0:
        return None
    y = x[rep[0] :]
    cs = np.concatenate(([0.0], np.cumsum(y)))
    cs2 = np.concatenate(([0.0], np.cumsum(y * y)))
    last = rep - rep[0]
    n = last + 1
    mean = cs[n] / n
    var = (cs2[n] - cs[n] ** 2 / n) / np.maximum(n - 1, 1)
    constant = np.maximum.accumulate(y)[last] == np.minimum.accumulate(y)[last]
    std = np.where(constant, 0.0, np.sqrt(np.maximum(var, 0.0)))
    return has, rep, y, cs, last, n, mean, std


def _z(d: np.ndarray, scale: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(scale > 0, d / np.where(scale > 0, scale, 1.0), np.where(d > 0, np.inf, np.where(d < 0, -np.inf, np.nan)))


def _forward(has: np.ndarray, rep: np.ndarray, vals: np.ndarray, fill: float) -> np.ndarray:
    t_n = has.size
    full = np.full(t_n, fill, dtype=float)
    full[rep] = vals
    idx = np.maximum.accumulate(np.where(has, np.arange(t_n), -1))
    return np.where(idx >= 0, full[np.maximum(idx, 0)], fill)


def shipped_z(x: np.ndarray, n_reports: np.ndarray) -> np.ndarray:
    """Daily z of 48c467f as the dashboard sees it; -inf where the status is NO_DATA; nan kept as nan."""
    s = _z_stats(x, n_reports)
    if s is None:
        return np.full(np.asarray(x).size, -np.inf)
    has, rep, y, cs, last, n, mean, std = s
    z = _z(y[last] - mean, std)
    z = np.where(n >= 2 * WINDOW + 1, z, -np.inf)
    return _forward(has, rep, z, -np.inf)


def trailing_status(x: np.ndarray, n_reports: np.ndarray, sigmas: tuple[float, ...] = (2.0, 3.0)) -> dict[float, np.ndarray]:
    """Daily status code per sigma for engine c3cee22 (trailing average)."""
    t_n = np.asarray(x).size
    out = {s: np.zeros(t_n, dtype=np.int8) for s in sigmas}
    st = _z_stats(x, n_reports)
    if st is None:
        return out
    has, rep, y, cs, last, n, mean, std = st
    m = y.size
    sm = np.full(m, np.nan)
    if m >= WINDOW:
        sm[WINDOW - 1 :] = (cs[WINDOW:] - cs[:-WINDOW]) / WINDOW
    cur = sm[last]
    z = _z(cur - mean, std / np.sqrt(WINDOW))
    j = np.arange(RUN_DAYS + 1)
    pos = np.clip(last[:, None] - RUN_DAYS + j[None, :], 0, m - 1)
    rising = (last >= RUN_DAYS + WINDOW - 1) & np.all(np.diff(sm[pos], axis=1) > 0, axis=1)
    eligible = n >= 3 * WINDOW
    for s in sigmas:
        code = np.where(z > s, OUTSIDE, np.where(z > 0.7 * s, MARGINAL, WITHIN))
        code = np.where((code == WITHIN) & rising, MARGINAL, code)
        code = np.where(eligible, code, NO_DATA)
        out[s] = _forward(has, rep, code.astype(float), 0.0).astype(np.int8)
    return out


@contextlib.contextmanager
def engine(name: str):
    """Temporarily import the frozen engine `name` (e.g. 'c3cee22') as risk_kinematics, then restore the previous one."""
    src = str(ENGINE_ROOT / name / "src")
    keys = [k for k in sys.modules if k == "risk_kinematics" or k.startswith("risk_kinematics.")]
    saved = {k: sys.modules.pop(k) for k in keys}
    sys.path.insert(0, src)
    try:
        import risk_kinematics

        yield risk_kinematics
    finally:
        sys.path.remove(src)
        for k in [k for k in sys.modules if k == "risk_kinematics" or k.startswith("risk_kinematics.")]:
            del sys.modules[k]
        sys.modules.update(saved)
