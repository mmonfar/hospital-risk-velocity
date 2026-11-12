"""Addendum 2026-11-03: alarms on velocity, acceleration and jerk of the smoothed score. EXPLORATORY.

python -m study.extra.run_derivatives --workers 10 --out study/results/extra
python -m study.extra.run_derivatives --gate          (parity gate only)

Own child key DERIV_KEY for the new difference-statistic pools and for P14. Scenarios IC5, S15, S2,
R60, SEV, REP use the PRIMARY data streams and the PRIMARY oracle pool for M4 and M5 (read only), so
M4 and M5 reproduce the published values exactly. P14 (all levels 2x for 14 days, then baseline) is
defined here, not in dgm.py. Synthetic data only.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from study.extra import derivatives as dv
from study.sim import charts, dgm, run

DERIV_KEY = 20261103
SEED = dgm.ROOT_SEED
P1 = dgm.PHASE1_DAYS
TAU = dgm.TAU
PAD = 28
P14_DAYS = 14
SCEN = ("IC5", "S15", "S2", "R60", "SEV", "REP", "P14")
WEIGHTS = ("squared", "linear")
METHODS = ("M4", "M5", *dv.STATS)
CORE = dgm.BY_ID["S2"]  # core setting mu0 = 2, theta = 2; same in-control model as IC5


def p14_stream(rng: np.random.Generator) -> np.ndarray:
    """(days, 9) counts: all levels 2x for P14_DAYS from day TAU, then back to baseline."""
    n_days = dgm.PHASE1_DAYS + dgm.MONITOR_OOC
    mu = np.full(n_days, CORE.mu0)
    mu[TAU - 1 : TAU - 1 + P14_DAYS] = CORE.mu0 * 2.0
    n = dgm.draw_n(rng, mu, CORE.theta)
    day = np.repeat(np.arange(n_days), n)
    lev = np.minimum(np.searchsorted(np.cumsum(dgm.PI0), rng.random(day.size), side="right"), 8)
    return np.bincount(day * 9 + lev, minlength=n_days * 9).reshape(n_days, 9)


def stream(sid: str, r: int) -> np.ndarray:
    if sid == "P14":
        return p14_stream(np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(DERIV_KEY, 14, r, 0))))
    drng, _ = dgm.scenario_rngs(SEED, dgm.SCENARIO_INDEX[sid], r)
    return dgm.simulate_stream(dgm.BY_ID[sid], drng)


def diff_thresholds(wname: str, reps: int = 1000, horizon: int = 1000) -> dict[str, float]:
    """Oracle calibration per statistic and weight scheme: pooled ARL0 >= 365 on reps x horizon days."""
    w = dgm.WEIGHT_SCHEMES[wname]
    rng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(DERIV_KEY, 900 + WEIGHTS.index(wname))))
    n = dgm.draw_n(rng, np.full((reps, horizon + PAD), CORE.mu0), CORE.theta)
    x, _ = dgm.compound_days(rng, n, dgm.PI0, w)
    return {k: charts.calibrate_threshold(dv.for_alarm(v)[:, PAD:]) for k, v in dv.all_stats(x).items()}


def primary_thresholds(sid: str, wname: str) -> tuple[charts.Fit, dict[str, float]]:
    """M4, M5 thresholds exactly as the primary run (same pool key); P14 reuses the S2 pool."""
    w = dgm.WEIGHT_SCHEMES[wname]
    sc = dgm.BY_ID["S2" if sid == "P14" else sid]
    fit = charts.true_fit(sc, w)
    orng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(dgm.SCENARIO_INDEX[sc.sid], 10**9)))
    return fit, charts.thresholds(fit, w, orng, ("M4", "M5"), reps=run.ORACLE_REPS)


def first_day(a: np.ndarray) -> np.ndarray:
    """First alarm day (1-based; day P1+1 = first monitoring day) per row, 0 if none. a: (reps, monitoring days)."""
    return np.where(a.any(axis=1), P1 + 1 + a.argmax(axis=1), 0)


def _task(task: tuple) -> tuple[list[tuple], dict]:
    sid, n, dth, which_methods = task
    t0 = time.perf_counter()
    counts = np.stack([stream(sid, r) for r in range(n)])  # (n, days, 9)
    rows = []
    for wname in WEIGHTS:
        w = dgm.WEIGHT_SCHEMES[wname]
        x = counts @ w
        fit, th = primary_thresholds(sid, wname)
        fa = {
            "M4": first_day(charts.ewma_paths(x[:, P1:], charts.LAMBDA, fit.xbar) > th["M4"]),
            "M5": first_day(charts.cusum_paths(x[:, P1:], fit.xbar + 0.5 * fit.sd) > th["M5"]),
        }
        if which_methods == "all":
            for k, v in dv.all_stats(x).items():
                fa[k] = first_day(dv.for_alarm(v)[:, P1:] > dth[wname][k])
        for m, f in fa.items():
            rows += [(sid, wname, r, m, int(f[r])) for r in range(n)]
    return rows, {"scenario": sid, "n": n, "seconds": round(time.perf_counter() - t0, 1)}


# ---- measures -----------------------------------------------------------------------------------


def _prop(k: int, n: int) -> tuple[float, float]:
    p = k / n if n else float("nan")
    return p, math.sqrt(p * (1 - p) / n) if n else float("nan")


def e1_arl0(rep: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (wn, m), g in rep[rep.scenario == "IC5"].groupby(["weights", "method"], sort=False):
        f = g.first_alarm.to_numpy()
        al = f > 0
        k = int(al.sum())
        days = np.where(al, f - P1, dgm.MONITOR_IC).sum()
        arl = days / k if k else float("nan")
        rows.append({"weights": wn, "method": m, "n": len(f), "alarmed": k, "arl0": arl,
                     "arl0_mcse": arl / math.sqrt(k) if k else float("nan"), "censored_share": 1 - k / len(f)})
    return pd.DataFrame(rows)


def e2_detection(rep: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sid, wn, m), g in rep[rep.scenario != "IC5"].groupby(["scenario", "weights", "method"], sort=False):
        f = g.first_alarm.to_numpy()
        n = f.size
        pre = (f > 0) & (f < TAU)
        elig = ~pre
        ne = int(elig.sum())
        det = elig & (f > 0)
        d = (f - TAU)[det]
        p14, e14 = _prop(int((det & (f - TAU <= 13)).sum()), ne)
        p30, e30 = _prop(int((det & (f - TAU <= 29)).sum()), ne)
        u30, eu = _prop(int(((f >= TAU) & (f <= TAU + 29)).sum()), n)
        ua, eua = _prop(int((f > 0).sum()), n)
        rows.append({"scenario": sid, "weights": wn, "method": m, "n": n, "n_eligible": ne, "pre_change_alarm": float(pre.mean()),
                     "pod14": p14, "pod14_mcse": e14, "pod30": p30, "pod30_mcse": e30,
                     "ced": float(d.mean()) if d.size else float("nan"),
                     "ced_mcse": float(d.std(ddof=1) / math.sqrt(d.size)) if d.size > 1 else float("nan"),
                     "uncond_first_alarm_d181_210": u30, "uncond_mcse": eu, "uncond_any_alarm": ua, "uncond_any_mcse": eua})
    return pd.DataFrame(rows)


def e3_paired(rep: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sid, wn), g in rep[rep.scenario != "IC5"].groupby(["scenario", "weights"], sort=False):
        piv = g.pivot(index="rep", columns="method", values="first_alarm")
        for st in dv.STATS:
            for comp in ("M4", "M5"):
                a, b = piv[st].to_numpy(), piv[comp].to_numpy()
                ok = ~(((a > 0) & (a < TAU)) | ((b > 0) & (b < TAU)))
                a, b = a[ok], b[ok]
                before = (a > 0) & ((b == 0) | (a < b))
                lead = (b - a)[before & (b > 0)]
                p, e = _prop(int(before.sum()), a.size)
                rows.append({"scenario": sid, "weights": wn, "stat": st, "comparator": comp, "n_eligible": a.size,
                             "share_diff_strictly_first": p, "mcse": e, "n_both_alarm_diff_first": int(lead.size),
                             "median_lead_days": float(np.median(lead)) if lead.size else float("nan")})
    return pd.DataFrame(rows)


def notes(e1: pd.DataFrame, e2: pd.DataFrame, e3: pd.DataFrame) -> str:
    hdr = ["| scenario | " + " | ".join(METHODS) + " |", "|---|" + "---|" * len(METHODS)]
    L = ["# Derivative alarms: numbers (addendum 2026-11-03, exploratory)", "",
         "Synthetic data. One window (w = 7), one core setting. M4 = EWMA, M5 = CUSUM.", "",
         "## ARL0 in IC5 (days; target 365)", "", "| weights | method | ARL0 | MCSE |", "|---|---|---|---|"]
    L += [f"| {r.weights} | {r.method} | {r.arl0:.0f} | {r.arl0_mcse:.0f} |" for r in e1.itertuples()]
    for wn in WEIGHTS:
        sub = e2[e2.weights == wn]
        L += ["", f"## POD30 ({wn} weights), eligible replicates (MCSE)", ""] + hdr
        for sid in SCEN[1:]:
            c = [sub[(sub.scenario == sid) & (sub.method == m)].iloc[0] for m in METHODS]
            L.append(f"| {sid} | " + " | ".join(f"{r.pod30:.3f} ({r.pod30_mcse:.3f})" for r in c) + " |")
        L += ["", f"## POD14 / unconditional first alarm in days 181-210 ({wn})", ""] + hdr
        for sid in SCEN[1:]:
            c = [sub[(sub.scenario == sid) & (sub.method == m)].iloc[0] for m in METHODS]
            L.append(f"| {sid} | " + " | ".join(f"{r.pod14:.3f} / {r.uncond_first_alarm_d181_210:.3f}" for r in c) + " |")
        L += ["", f"## Paired lead ({wn}): share where the difference alarm fires strictly first (median lead days when both alarm)", "",
              "| scenario | stat | vs M4 | vs M5 |", "|---|---|---|---|"]
        s3 = e3[e3.weights == wn]
        for sid in SCEN[1:]:
            for st in dv.STATS:
                c = [s3[(s3.scenario == sid) & (s3.stat == st) & (s3.comparator == comp)].iloc[0] for comp in ("M4", "M5")]
                L.append(f"| {sid} | {st} | " + " | ".join(f"{r.share_diff_strictly_first:.3f} ({r.median_lead_days:.0f})" for r in c) + " |")
    L += ["", "## Expectations in the addendum (computed from the tables above)", ""]
    for wn in WEIGHTS:
        def p(s: str, m: str, wn: str = wn) -> float:
            return float(e2[(e2.weights == wn) & (e2.scenario == s) & (e2.method == m)].pod30.iloc[0])

        sus = ("S15", "S2", "R60")
        e1ok = all(p(s, "V") < min(p(s, "M4"), p(s, "M5")) for s in sus)
        e1b = all(p(s, "A") < p(s, "V") and p(s, "J") < p(s, "V") for s in sus)
        e2ok = all(p(s, "J") <= min(p(s, "V"), p(s, "A")) for s in SCEN[1:])
        r14, r2 = p("P14", "V") / p("P14", "M4"), p("S2", "V") / p("S2", "M4")
        L.append(f"- {wn}: (1) V POD30 below M4 and M5 on S15, S2, R60: {e1ok}; A and J below V there: {e1b}.")
        L.append(f"- {wn}: (2) J has the lowest POD30 of V, A, J in every scenario: {e2ok}.")
        L.append(f"- {wn}: (3) V/M4 POD30 ratio higher on P14 than on S2: {r14 > r2} ({r14:.3f} vs {r2:.3f}).")
        L.append(f"- {wn}: (4) REP POD30 (any alarm is false): " + ", ".join(f"{m} {p('REP', m):.3f}" for m in METHODS) + ".")
    return "\n".join(L) + "\n"


# ---- gate and main ------------------------------------------------------------------------------


def gate(n_s2: int = 1000, n_ic5: int = 1000) -> bool:
    prim = pd.read_csv("study/results/full/replicates.csv")
    prim = prim[(prim.weights == "squared") & prim.method.isin(["M4", "M5"])]
    summ = pd.read_csv("study/results/full/summary.csv")
    ok = True
    for sid, n in (("S2", n_s2), ("IC5", n_ic5)):
        rows, _ = _task((sid, n, {}, "comparators"))
        mine = pd.DataFrame(rows, columns=["scenario", "weights", "rep", "method", "first_alarm"])
        mine = mine[mine.weights == "squared"]
        for m in ("M4", "M5"):
            a = mine[mine.method == m].first_alarm.to_numpy()
            b = prim[(prim.scenario == sid) & (prim.method == m)].sort_values("rep").first_alarm.to_numpy()[:n]
            same = bool(np.array_equal(a, b))
            ok &= same
            pub = summ[(summ.scenario == sid) & (summ.method == m) & (summ.weights == "squared")].iloc[0]
            if sid == "S2":
                v = e2_detection(mine)
                v = v[v.method == m].iloc[0]
                print(f"GATE S2 {m}: POD30 new {v.pod30:.3f} (MCSE {v.pod30_mcse:.3f}) published {pub.pod30:.3f}; replicates identical: {same}")
            else:
                v = e1_arl0(mine)
                v = v[v.method == m].iloc[0]
                print(f"GATE IC5 {m}: ARL0 new {v.arl0:.0f} (MCSE {v.arl0_mcse:.0f}, n={n}) published {pub.arl0:.0f}; first {n} replicates identical: {same}")
    print("GATE PASS" if ok else "GATE FAIL", flush=True)
    return ok


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="study/results/extra")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--n-ic5", type=int, default=None)
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--pilot", action="store_true", help="time only; writes nothing")
    a = ap.parse_args(argv)
    if a.gate:
        return 0 if gate() else 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    n_of = {s: (a.n_ic5 or 2 * a.n) if s == "IC5" else a.n for s in SCEN}
    dth = {wn: diff_thresholds(wn) for wn in WEIGHTS}
    print("thresholds", {w: {k: round(v, 4) for k, v in d.items()} for w, d in dth.items()}, f"{time.perf_counter() - t0:.0f}s", flush=True)
    specs = sorted(((s, n_of[s], dth, "all") for s in SCEN), key=lambda t: -t[1])
    rows, timing = [], []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r, t in ex.map(_task, specs):
            rows += r
            timing.append(t)
            print(t, flush=True)
    rep = pd.DataFrame(rows, columns=["scenario", "weights", "rep", "method", "first_alarm"])
    wall = time.perf_counter() - t0
    if a.pilot:
        print(f"PILOT wall {wall:.0f}s for n={a.n}")
        return 0
    e1, e2, e3 = e1_arl0(rep), e2_detection(rep), e3_paired(rep)
    e1.to_csv(out / "e1_arl0.csv", index=False)
    e2.to_csv(out / "e2_detection.csv", index=False)
    e3.to_csv(out / "e3_paired_lead.csv", index=False)
    (out / "e_notes.md").write_text(notes(e1, e2, e3), encoding="utf-8")
    meta = {"exploratory": True, "addendum": "study/protocol_addendum_2026-11-03.md", "deriv_key": DERIV_KEY, "seed": SEED, "n": n_of,
            "w": dv.W, "thresholds_difference_stats": dth, "numpy": np.__version__, "pandas": pd.__version__,
            "python": sys.version.split()[0], "git_commit_at_run": git_commit(), "wall_seconds": round(wall, 1), "timing": timing}
    (out / "e_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("finished", round(wall), "s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
