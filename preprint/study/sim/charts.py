"""Comparator charts M2-M7 and their calibration to ARL0 = 365 (protocol M and M.2).

Every threshold is set from a parametric bootstrap: 200 in-control continuations (default 1,000
days each) drawn from the model fitted to the stream's own Phase I days (bootstrap), or from
the true model (oracle). Alarm rule everywhere: statistic > threshold. No chart is reset after
an alarm. ARL0 in a pool is the days-at-risk / alarms estimator (handles censoring).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from study.sim import dgm

TARGET_ARL = 365.0
THETA_CAP = 1000.0
LAMBDA = 0.2
CUSUM_REF_SD = 0.5  # CUSUM reference value = baseline mean + CUSUM_REF_SD x SD
CHARTS = ("M2", "M3", "M4", "M5", "M6", "M7")


@dataclass(frozen=True)
class Fit:
    mean_n: float
    theta: float
    pi: np.ndarray
    xbar: float
    sd: float


def fit_phase1(counts1: np.ndarray, weights: np.ndarray) -> Fit:
    """Moment fit of Phase I: NB counts (theta capped), add-one severity mix, score mean/SD."""
    n1 = counts1.sum(axis=1).astype(float)
    m = float(n1.mean())
    v = float(n1.var(ddof=1))
    theta = min(m * m / (v - m), THETA_CAP) if v > m else THETA_CAP
    tot = counts1.sum(axis=0) + 1.0
    x1 = counts1 @ weights
    return Fit(m, theta, tot / tot.sum(), float(x1.mean()), float(x1.std(ddof=1)))


def true_fit(sc: dgm.Scenario, weights: np.ndarray) -> Fit:
    """Known-parameter ('oracle') baseline for scenario sc."""
    pi = dgm.PI0
    ew = float(pi @ weights)
    vw = float(pi @ weights**2) - ew**2
    vn = sc.mu0 + (0.0 if np.isinf(sc.theta) else sc.mu0**2 / sc.theta)
    return Fit(sc.mu0, sc.theta, pi, sc.mu0 * ew, float(np.sqrt(vn * ew**2 + sc.mu0 * vw)))


# ---- statistics -------------------------------------------------------------------------------


def ewma_paths(x: np.ndarray, lam: float, z0: float) -> np.ndarray:
    z = np.empty_like(x, dtype=float)
    prev = np.full(x.shape[:-1], z0, dtype=float)
    for t in range(x.shape[-1]):
        prev = lam * x[..., t] + (1 - lam) * prev
        z[..., t] = prev
    return z


def cusum_paths(x: np.ndarray, ref: float) -> np.ndarray:
    """Upper CUSUM C_t = max(0, C_{t-1} + x_t - ref) via the reflected random walk identity."""
    s = np.cumsum(x - ref, axis=-1)
    return s - np.minimum(0.0, np.minimum.accumulate(s, axis=-1))


def gap_stat(ne: np.ndarray) -> np.ndarray:
    """-(days since the previous E-I day) on days with E-I reports; 0 if >=2 reports that day.

    The first E-I day of a series has no predecessor and never alarms (stat -inf).
    """
    h = ne.shape[-1]
    idx = np.arange(h)
    last = np.maximum.accumulate(np.where(ne > 0, idx, -1), axis=-1)
    prev = np.concatenate([np.full(ne.shape[:-1] + (1,), -1), last[..., :-1]], axis=-1)
    gap = np.where(ne >= 2, 0.0, np.where((ne == 1) & (prev >= 0), idx - prev, np.inf))
    return -gap


def shewhart_limit(x1: np.ndarray, big_l: float) -> float:
    """XmR upper limit: mean + L * MRbar / 1.128."""
    mr = np.abs(np.diff(x1)).mean()
    return float(x1.mean() + big_l * mr / 1.128)


def nb_upper_quantile(mean: float, theta: float, prob: float) -> float:
    """Smallest k with P(N <= k) >= prob for NB(mean, size theta) (exact recurrence)."""
    if mean <= 0:
        return 0.0
    if np.isinf(theta):  # Poisson limit (theta = infinity)
        pmf = math.exp(-mean)
        cdf = pmf
        k = 0
        while cdf < prob and k < 100000:
            k += 1
            pmf *= mean / k
            cdf += pmf
        return float(k)
    p = theta / (theta + mean)
    pmf = p**theta
    cdf = pmf
    k = 0
    while cdf < prob and k < 100000:
        pmf *= (k + theta) / (k + 1) * (1 - p)
        cdf += pmf
        k += 1
    return float(k)


# ---- calibration ------------------------------------------------------------------------------


def _arl(cm: np.ndarray, c: float) -> float:
    hit = cm > c
    alarmed = hit[:, -1]
    k = int(alarmed.sum())
    if k == 0:
        return np.inf
    risk = np.where(alarmed, hit.argmax(axis=1) + 1, cm.shape[1]).sum()
    return float(risk / k)


def calibrate_threshold(stat: np.ndarray, target: float = TARGET_ARL, iters: int = 30) -> float:
    """Smallest threshold c (alarm if stat > c) whose pooled ARL0 estimate is >= target."""
    cm = np.maximum.accumulate(stat, axis=1)
    finite = stat[np.isfinite(stat)]
    if finite.size == 0:
        return float("inf")
    lo, hi = float(finite.min()) - 1.0, float(finite.max())
    if _arl(cm, lo) >= target:
        return lo
    for _ in range(iters):
        mid = (lo + hi) / 2
        if _arl(cm, mid) >= target:
            hi = mid
        else:
            lo = mid
    return hi


def thresholds(
    fit: Fit,
    weights: np.ndarray,
    rng: np.random.Generator,
    which: tuple[str, ...] = CHARTS,
    reps: int = 200,
    horizon: int = 1000,
    lam: float = LAMBDA,
    cusum_ref_sd: float = CUSUM_REF_SD,
) -> dict[str, float]:
    """Calibrate the requested charts to ARL0 = 365 on `reps` simulated continuations.

    lam (EWMA weight) and cusum_ref_sd (CUSUM reference, in SD above the mean) keep the primary
    values by default. Other values are used only in the post hoc addendum 3 (9 Nov 2026).
    """
    n = dgm.draw_n(rng, np.full((reps, horizon), fit.mean_n), fit.theta)
    x, ne = dgm.compound_days(rng, n, fit.pi, weights)
    th: dict[str, float] = {}
    if "M2" in which:  # (1 - 1/365) quantile of the pooled compound distribution
        th["M2"] = float(np.quantile(x, 1 - 1 / TARGET_ARL, method="inverted_cdf"))
    if "M3" in which:
        th["M3"] = calibrate_threshold(x)
    if "M4" in which:
        th["M4"] = calibrate_threshold(ewma_paths(x, lam, fit.xbar))
    if "M5" in which:
        th["M5"] = calibrate_threshold(cusum_paths(x, fit.xbar + cusum_ref_sd * fit.sd))
    if "M6" in which:
        th["M6"] = calibrate_threshold(gap_stat(ne))
    if "M7" in which:
        th["M7"] = nb_upper_quantile(fit.mean_n, fit.theta, 1 - 1 / TARGET_ARL)
    return th


def alarms(
    th: dict[str, float],
    fit: Fit,
    x: np.ndarray,
    n: np.ndarray,
    ne: np.ndarray,
    lam: float = LAMBDA,
    cusum_ref_sd: float = CUSUM_REF_SD,
) -> dict[str, np.ndarray]:
    """Boolean alarm arrays over the monitoring days for each calibrated chart."""
    out: dict[str, np.ndarray] = {}
    if "M2" in th:
        out["M2"] = x > th["M2"]
    if "M3" in th:
        out["M3"] = x > th["M3"]
    if "M4" in th:
        out["M4"] = ewma_paths(x, lam, fit.xbar) > th["M4"]
    if "M5" in th:
        out["M5"] = cusum_paths(x, fit.xbar + cusum_ref_sd * fit.sd) > th["M5"]
    if "M6" in th:
        out["M6"] = gap_stat(ne) > th["M6"]
    if "M7" in th:
        out["M7"] = n > th["M7"]
    return out
