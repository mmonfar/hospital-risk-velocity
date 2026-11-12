"""Addendum 2 (2026-11-03): rolling slope alarms SL14 and SL28. EXPLORATORY.

python -m study.extra.run_slope --workers 10 --out study/results/extra

Reuses the streams, the M4/M5 thresholds, the V calibration pool and the measure functions of
run_derivatives (not changed). Gate: V, M4 and M5 must equal the addendum 1 files e1/e2 exactly;
if not, nothing is written. Synthetic data only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from study.extra import derivatives as dv
from study.extra import run_derivatives as rd
from study.extra import slope as sl
from study.sim import charts, dgm

SLOPES = tuple(sl.LENGTHS)
STATS = ("V", *SLOPES)
METHODS = ("M4", "M5", *STATS)
SCEN, WEIGHTS = rd.SCEN, rd.WEIGHTS


def thresholds(wname: str, reps: int = 1000, horizon: int = 1000) -> dict[str, float]:
    """Same pool as addendum 1 (same key and draws), so V gets the same threshold."""
    w = dgm.WEIGHT_SCHEMES[wname]
    rng = np.random.default_rng(np.random.SeedSequence(rd.SEED, spawn_key=(rd.DERIV_KEY, 900 + WEIGHTS.index(wname))))
    n = dgm.draw_n(rng, np.full((reps, horizon + rd.PAD), rd.CORE.mu0), rd.CORE.theta)
    x, _ = dgm.compound_days(rng, n, dgm.PI0, w)
    stats = {"V": dv.trailing(x)["V"], **sl.all_slopes(x)}
    return {k: charts.calibrate_threshold(dv.for_alarm(v)[:, rd.PAD :]) for k, v in stats.items()}


def _task(task: tuple) -> tuple[list[tuple], dict]:
    sid, n, dth = task
    t0 = time.perf_counter()
    counts = np.stack([rd.stream(sid, r) for r in range(n)])
    rows = []
    for wname in WEIGHTS:
        x = counts @ dgm.WEIGHT_SCHEMES[wname]
        fit, th = rd.primary_thresholds(sid, wname)
        P1 = rd.P1
        fa = {
            "M4": rd.first_day(charts.ewma_paths(x[:, P1:], charts.LAMBDA, fit.xbar) > th["M4"]),
            "M5": rd.first_day(charts.cusum_paths(x[:, P1:], fit.xbar + 0.5 * fit.sd) > th["M5"]),
            "V": rd.first_day(dv.for_alarm(dv.trailing(x)["V"])[:, P1:] > dth[wname]["V"]),
        }
        for k, v in sl.all_slopes(x).items():
            fa[k] = rd.first_day(dv.for_alarm(v)[:, P1:] > dth[wname][k])
        for m, f in fa.items():
            rows += [(sid, wname, r, m, int(f[r])) for r in range(n)]
    return rows, {"scenario": sid, "n": n, "seconds": round(time.perf_counter() - t0, 1)}


def paired(rep: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sid, wn), g in rep[rep.scenario != "IC5"].groupby(["scenario", "weights"], sort=False):
        piv = g.pivot(index="rep", columns="method", values="first_alarm")
        for st in SLOPES:
            for comp in ("M4", "M5"):
                a, b = piv[st].to_numpy(), piv[comp].to_numpy()
                ok = ~(((a > 0) & (a < rd.TAU)) | ((b > 0) & (b < rd.TAU)))
                a, b = a[ok], b[ok]
                before = (a > 0) & ((b == 0) | (a < b))
                lead = (b - a)[before & (b > 0)]
                p, e = rd._prop(int(before.sum()), a.size)
                rows.append({"scenario": sid, "weights": wn, "stat": st, "comparator": comp, "n_eligible": a.size,
                             "share_diff_strictly_first": p, "mcse": e, "n_both_alarm_diff_first": int(lead.size),
                             "median_lead_days": float(np.median(lead)) if lead.size else float("nan")})
    return pd.DataFrame(rows)


def gate(f1: pd.DataFrame, f2: pd.DataFrame, out: Path) -> bool:
    ok = True
    e1 = pd.read_csv(out / "e1_arl0.csv")
    e2 = pd.read_csv(out / "e2_detection.csv")
    meth = ["M4", "M5", "V"]
    a = f1[f1.method.isin(meth)].sort_values(["weights", "method"]).reset_index(drop=True)
    b = e1[e1.method.isin(meth)].sort_values(["weights", "method"]).reset_index(drop=True)
    cols = ["n", "alarmed", "arl0", "arl0_mcse"]
    same1 = bool(np.allclose(a[cols].to_numpy(), b[cols].to_numpy(), rtol=0, atol=1e-9)) and a.shape == b.shape
    c = f2[f2.method.isin(meth)].sort_values(["scenario", "weights", "method"]).reset_index(drop=True)
    d = e2[e2.method.isin(meth)].sort_values(["scenario", "weights", "method"]).reset_index(drop=True)
    cols2 = ["n", "n_eligible", "pod14", "pod30", "pod30_mcse", "ced", "uncond_first_alarm_d181_210", "uncond_any_alarm"]
    same2 = c.shape == d.shape and bool(np.allclose(c[cols2].to_numpy(float), d[cols2].to_numpy(float), rtol=0, atol=1e-9, equal_nan=True))
    print(f"GATE ARL0 (IC5, V/M4/M5, both weights) equal to e1: {same1}")
    print(f"GATE POD14/POD30/CED/unconditional (V/M4/M5, {c.scenario.nunique()} scenarios, both weights) equal to e2: {same2}")
    for wn in WEIGHTS:
        for m in meth:
            n1 = f2[(f2.scenario == "S2") & (f2.weights == wn) & (f2.method == m)].pod30.iloc[0]
            o1 = e2[(e2.scenario == "S2") & (e2.weights == wn) & (e2.method == m)].pod30.iloc[0]
            print(f"  S2 POD30 {wn} {m}: new {n1:.6f} e2 {o1:.6f}")
    ok = same1 and same2
    print("GATE PASS" if ok else "GATE FAIL", flush=True)
    return ok


def notes(f1: pd.DataFrame, f2: pd.DataFrame, f3: pd.DataFrame) -> str:
    hdr = ["| scenario | " + " | ".join(METHODS) + " |", "|---|" + "---|" * len(METHODS)]
    L = ["# Rolling slope alarms: numbers (addendum 2, exploratory)", "", "Synthetic data. Methods: SL14, SL28 = rolling slope; V = velocity; M4 = EWMA; M5 = CUSUM.", "",
         "## Achieved ARL0 in IC5 (days; target 365), side by side", "", "| weights | " + " | ".join(("SL14", "SL28", "V", "M4", "M5")) + " |", "|---|---|---|---|---|---|"]
    for wn in WEIGHTS:
        c = [f1[(f1.weights == wn) & (f1.method == m)].iloc[0] for m in ("SL14", "SL28", "V", "M4", "M5")]
        L.append(f"| {wn} | " + " | ".join(f"{r.arl0:.0f} ({r.arl0_mcse:.0f})" for r in c) + " |")
    for wn in WEIGHTS:
        sub = f2[f2.weights == wn]
        L += ["", f"## POD30 ({wn}), eligible replicates (MCSE)", ""] + hdr
        for sid in SCEN[1:]:
            c = [sub[(sub.scenario == sid) & (sub.method == m)].iloc[0] for m in METHODS]
            L.append(f"| {sid} | " + " | ".join(f"{r.pod30:.3f} ({r.pod30_mcse:.3f})" for r in c) + " |")
        L += ["", f"## POD14 / unconditional first alarm in days 181-210 ({wn})", ""] + hdr
        for sid in SCEN[1:]:
            c = [sub[(sub.scenario == sid) & (sub.method == m)].iloc[0] for m in METHODS]
            L.append(f"| {sid} | " + " | ".join(f"{r.pod14:.3f} / {r.uncond_first_alarm_d181_210:.3f}" for r in c) + " |")
        L += ["", f"## Paired lead ({wn}): share where the slope alarm fires strictly first (median lead days when both alarm)", "",
              "| scenario | stat | vs M4 | vs M5 |", "|---|---|---|---|"]
        s3 = f3[f3.weights == wn]
        for sid in SCEN[1:]:
            for st in SLOPES:
                c = [s3[(s3.scenario == sid) & (s3.stat == st) & (s3.comparator == comp)].iloc[0] for comp in ("M4", "M5")]
                L.append(f"| {sid} | {st} | " + " | ".join(f"{r.share_diff_strictly_first:.3f} ({r.median_lead_days:.0f})" for r in c) + " |")
    L += ["", "## Expectations in addendum 2 (computed from the tables above)", ""]
    for wn in WEIGHTS:
        def p(s: str, m: str, wn: str = wn) -> float:
            return float(f2[(f2.weights == wn) & (f2.scenario == s) & (f2.method == m)].pod30.iloc[0])

        e1 = {s: {k: p(s, k) > p(s, "V") for k in SLOPES} for s in ("S2", "R60")}
        e1ok = all(any(e1[s].values()) for s in e1)
        e2ok = {k: all(p(s, k) < min(p(s, "M4"), p(s, "M5")) for s in ("S15", "S2")) for k in SLOPES}
        gap = {k: {s: (p(s, "M4") + p(s, "M5")) / 2 - p(s, k) for s in ("S2", "R60")} for k in SLOPES}
        e3 = {k: gap[k]["R60"] < gap[k]["S2"] for k in SLOPES}
        L.append(f"- {wn}: (1) SL14 or SL28 above V on S2 and R60: {e1ok}; detail above V {e1}.")
        L.append(f"- {wn}: (2) below M4 and M5 on S15 and S2: {e2ok}.")
        L.append(f"- {wn}: (3) gap to mean of M4 and M5 smaller on R60 than on S2: {e3}; gaps " + ", ".join(f"{k} S2 {gap[k]['S2']:.3f} R60 {gap[k]['R60']:.3f}" for k in SLOPES) + ".")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="study/results/extra")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--n", type=int, default=1000)
    a = ap.parse_args(argv)
    out = Path(a.out)
    t0 = time.perf_counter()
    n_of = {s: 2 * a.n if s == "IC5" else a.n for s in SCEN}
    dth = {wn: thresholds(wn) for wn in WEIGHTS}
    print("thresholds", {w: {k: round(v, 4) for k, v in d.items()} for w, d in dth.items()}, flush=True)
    specs = sorted(((s, n_of[s], dth) for s in SCEN), key=lambda t: -t[1])
    rows, timing = [], []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r, t in ex.map(_task, specs):
            rows += r
            timing.append(t)
            print(t, flush=True)
    rep = pd.DataFrame(rows, columns=["scenario", "weights", "rep", "method", "first_alarm"])
    f1, f2, f3 = rd.e1_arl0(rep), rd.e2_detection(rep), paired(rep)
    if not gate(f1, f2, out):
        print("STOP: gate failed, nothing written", flush=True)
        return 1
    f1.to_csv(out / "f1_arl0.csv", index=False)
    f2.to_csv(out / "f2_detection.csv", index=False)
    f3.to_csv(out / "f3_paired_lead.csv", index=False)
    (out / "f_notes.md").write_text(notes(f1, f2, f3), encoding="utf-8")
    wall = time.perf_counter() - t0
    meta = {"exploratory": True, "addendum": "study/protocol_addendum_2_2026-11-03.md", "deriv_key": rd.DERIV_KEY, "seed": rd.SEED, "n": n_of,
            "slope_lengths": sl.LENGTHS, "thresholds": dth, "numpy": np.__version__, "pandas": pd.__version__, "python": sys.version.split()[0],
            "git_commit_at_run": rd.git_commit(), "wall_seconds": round(wall, 1), "timing": timing}
    (out / "f_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("finished", round(wall), "s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
