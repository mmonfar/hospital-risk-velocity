"""Performance measures with Monte Carlo standard errors (protocol E and P.1)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from study.sim import dgm


def _km_median(times: np.ndarray, event: np.ndarray) -> float:
    order = np.argsort(times, kind="stable")
    t, e = times[order], event[order]
    at_risk = len(t)
    surv = 1.0
    for ti, ei in zip(t, e, strict=True):
        if ei:
            surv *= 1 - 1 / at_risk
            if surv <= 0.5:
                return float(ti)
        at_risk -= 1
    return float("nan")


def _prop(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    return p, float(np.sqrt(p * (1 - p) / n))


def summarise(rep: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sid, wname, method), g in rep.groupby(["scenario", "weights", "method"], sort=False):
        sc = dgm.BY_ID[sid]
        n = len(g)
        first = g["first_alarm"].to_numpy()
        alarmed = first > 0
        mon = sc.monitor_days
        run = np.where(alarmed, first - dgm.PHASE1_DAYS, mon)
        r: dict[str, object] = {"scenario": sid, "weights": wname, "method": method, "n": n}
        r["alarm_days_per_year"] = g["alarm_days"].mean() * 365 / mon
        r["alarm_days_per_year_mcse"] = g["alarm_days"].std(ddof=1) * 365 / mon / np.sqrt(n) if n > 1 else np.nan
        r["episodes_per_year"] = g["episodes"].mean() * 365 / mon
        r["episodes_per_year_mcse"] = g["episodes"].std(ddof=1) * 365 / mon / np.sqrt(n) if n > 1 else np.nan
        if sc.is_ic:
            k = int(alarmed.sum())
            arl = run.sum() / k if k else np.nan
            r["arl0"] = arl
            r["arl0_mcse"] = arl / np.sqrt(k) if k else np.nan
            r["km_median"] = _km_median(run.astype(float), alarmed)
            r["fa365"], r["fa365_mcse"] = _prop(int((alarmed & (run <= 365)).sum()), n)
            r["censored_share"] = 1 - k / n
        else:
            pre = alarmed & (first < dgm.TAU)
            r["pre_tau_fa"], r["pre_tau_fa_mcse"] = _prop(int(pre.sum()), n)
            elig = ~pre
            ne_ = int(elig.sum())
            det = elig & alarmed
            delay = (first - dgm.TAU)[det]
            r["n_eligible"] = ne_
            r["ced"] = delay.mean() if det.any() else np.nan
            r["ced_mcse"] = delay.std(ddof=1) / np.sqrt(det.sum()) if det.sum() > 1 else np.nan
            r["censored_share"] = 1 - det.sum() / ne_ if ne_ else np.nan
            r["pod14"], r["pod14_mcse"] = _prop(int((det & (first - dgm.TAU <= 13)).sum()), ne_)
            r["pod30"], r["pod30_mcse"] = _prop(int((det & (first - dgm.TAU <= 29)).sum()), ne_)
        if g["revision"].notna().any():
            r["endpoint_revision"] = g["revision"].mean()
            r["endpoint_revision_mcse"] = g["revision"].std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
        rows.append(r)
    return pd.DataFrame(rows)
