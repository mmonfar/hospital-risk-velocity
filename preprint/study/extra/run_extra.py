"""POST HOC simulations, added 2 Nov 2026 after publication review. NOT in the pre-specified protocol.

python -m study.extra.run_extra --workers 10 --out study/results/extra

D1  New scenario S127: step rise of ALL levels by 1.267 times, so the mean score rises by the same
    amount as in REP (verified in code below). M2, M4, M5, M7 with oracle thresholds taken from the
    in-control model (the S2 in-control model is identical, so the S2 oracle pool is reused).
D2  Released rule (48c467f) tuned: OUTSIDE with k found by bisection so that ARL0 = 365 days in IC5
    (tuning set), then checked on a fresh test set, then used in S2, S15, S127, SEV, REP.
D3  Trailing version (engine c3cee22): replica gated by tests/test_trailing_parity.py. OUTSIDE and
    any-alert (includes the 6-rises trend rule) in IC1-IC9, S2 and REP, k = 2 and 3.

Random numbers: own child key EXTRA_KEY, so the primary streams are never changed. S2, S15, SEV, REP,
IC1-IC9 use the PRIMARY streams (read only): same wards as the primary run (common random numbers).
S127 (new) uses EXTRA_KEY streams. Synthetic data only.
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

from study.extra import replicas
from study.sim import charts, dgm, measures, run, shipped

EXTRA_KEY = 20261102
SEED = dgm.ROOT_SEED
P1 = dgm.PHASE1_DAYS
W = dgm.WEIGHT_SCHEMES["squared"]
S127 = dgm.Scenario("S127", "step", 2.0, 2.0, 1.267)
dgm.BY_ID["S127"] = S127  # registered for measures.summarise only; dgm.SCENARIOS and the seed index are untouched
TARGET = 365.0


def mean_score_rise_rep() -> float:
    """Post/pre ratio of the expected daily score in REP (all-level rise 1.5 on A-D only)."""
    rep = dgm.BY_ID["REP"]
    return float(((dgm.PI0 * dgm.level_multiplier(rep)) @ W) / (dgm.PI0 @ W))


def streams(sid: str, r: int) -> tuple[np.random.Generator, np.random.Generator]:
    if sid == "S127":
        return tuple(np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(EXTRA_KEY, 127, r, k))) for k in (0, 1))  # type: ignore[return-value]
    return dgm.scenario_rngs(SEED, dgm.SCENARIO_INDEX[sid], r)


def _alarm_row(a: np.ndarray) -> tuple[int, int, int]:
    first = P1 + 1 + int(a.argmax()) if a.any() else 0
    return first, int(a.sum()), run._episodes(a)


def _task(spec: tuple) -> tuple[str, list[tuple], float]:
    kind, sid, n, k = spec
    sc = dgm.BY_ID[sid]
    t0 = time.perf_counter()
    rows: list[tuple] = []
    oracle = None
    if kind == "D1":
        s2 = dgm.BY_ID["S2"]  # same in-control model, same oracle pool as the primary S2
        fit = charts.true_fit(s2, W)
        orng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(dgm.SCENARIO_INDEX["S2"], 10**9)))
        which = ("M2", "M4", "M5", "M7")
        oracle = (fit, charts.thresholds(fit, W, orng, which, reps=run.ORACLE_REPS))
    for r in range(n):
        drng, crng = streams(sid, r)
        counts = dgm.simulate_stream(sc, drng)
        x, nn = counts @ W, counts.sum(axis=1)
        if kind == "D1":
            for m, (first, ad, ep, rv) in run.evaluate_replicate(sc, counts, W, crng, which, oracle).items():
                rows.append((sid, "squared", r, m, first, ad, ep, rv))
        elif kind == "D2":
            z = np.nan_to_num(replicas.shipped_z(x, nn)[P1:], nan=-np.inf)
            rows.append((sid, "squared", r, "M1_tuned_out", *_alarm_row(z > k), np.nan))
        else:  # D3
            st = replicas.trailing_status(x, nn, (2.0, 3.0))
            for kk in (2, 3):
                s = st[float(kk)][P1:]
                rows.append((sid, "squared", r, f"T{kk}_out", *_alarm_row(s == shipped.OUTSIDE), np.nan))
                rows.append((sid, "squared", r, f"T{kk}_any", *_alarm_row(s >= shipped.MARGINAL), np.nan))
    return f"{kind} {sid}", rows, round(time.perf_counter() - t0, 1)


def _z_matrix(n: int, tag: int) -> np.ndarray:
    sc = dgm.BY_ID["IC5"]
    out = np.empty((n, dgm.MONITOR_IC))
    for r in range(n):
        rng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(EXTRA_KEY, tag, r, 0)))
        c = dgm.simulate_stream(sc, rng)
        out[r] = np.nan_to_num(replicas.shipped_z(c @ W, c.sum(axis=1))[P1:], nan=-np.inf)
    return out


def arl0_at(cm: np.ndarray, k: float) -> tuple[float, int]:
    """ARL0 = days at risk / number of first alarms (censored at the end of the stream); cm = running max of z."""
    hit = cm > k
    alarmed = hit[:, -1]
    ev = int(alarmed.sum())
    if ev == 0:
        return float("inf"), 0
    days = np.where(alarmed, hit.argmax(axis=1) + 1, cm.shape[1]).sum()
    return float(days / ev), ev


def tune_k(cm: np.ndarray, lo: float = 2.0, hi: float = 20.0, iters: int = 50) -> float:
    """Smallest k whose ARL0 on the tuning set is >= 365 (ARL0 never falls as k rises)."""
    if arl0_at(cm, hi)[0] < TARGET:
        raise RuntimeError("no k below hi reaches ARL0 365")
    for _ in range(iters):
        mid = (lo + hi) / 2
        if arl0_at(cm, mid)[0] >= TARGET:
            hi = mid
        else:
            lo = mid
    return hi


def uncond(rep: pd.DataFrame, tau: int = dgm.TAU) -> pd.DataFrame:
    rows = []
    for (sid, m), g in rep.groupby(["scenario", "method"], sort=False):
        f = g.first_alarm.to_numpy()
        n = f.size
        a, b = int(((f >= tau) & (f <= tau + 29)).sum()), int((f > 0).sum())
        rows.append({"scenario": sid, "method": m, "n": n, "p_first_alarm_d181_210": a / n, "mcse_d181_210": math.sqrt(a / n * (1 - a / n) / n),
                     "p_any_alarm_by_485": b / n, "mcse_any_by_485": math.sqrt(b / n * (1 - b / n) / n)})
    return pd.DataFrame(rows)


COLS = ["scenario", "weights", "rep", "method", "first_alarm", "alarm_days", "episodes", "revision"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="study/results/extra")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--n", type=int, default=1000, help="replicates per scenario (IC5 uses 2 x n in D3)")
    ap.add_argument("--n-tune", type=int, default=2000, help="IC5 streams for the k search, and again for the fresh test set")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()

    rise = mean_score_rise_rep()
    assert abs(rise - S127.factor) < 5e-4, (rise, S127.factor)
    print(f"REP mean-score rise: {rise:.4f}; S127 factor {S127.factor}; pre-mean {dgm.PI0 @ W:.4f}", flush=True)

    # ---- D2 stage 1: find k
    cm_tune = np.maximum.accumulate(_z_matrix(a.n_tune, 1001), axis=1)
    k = tune_k(cm_tune)
    z_test = _z_matrix(a.n_tune, 1002)
    cm_test = np.maximum.accumulate(z_test, axis=1)
    arl_tune, ev_tune = arl0_at(cm_tune, k)
    arl_test, ev_test = arl0_at(cm_test, k)
    days = (z_test > k).sum(axis=1)
    first365 = (cm_test[:, 364] > k).mean()
    tuning = {"k": k, "n_tune": a.n_tune, "arl0_tuning_set": arl_tune, "arl0_tuning_mcse": arl_tune / math.sqrt(ev_tune),
              "arl0_test_set": arl_test, "arl0_test_mcse": arl_test / math.sqrt(ev_test), "alarm_events_test": ev_test,
              "fa365_test": float(first365), "alarm_days_per_year_test": float(days.mean() * 365 / dgm.MONITOR_IC),
              "alarm_days_per_year_test_mcse": float(days.std(ddof=1) * 365 / dgm.MONITOR_IC / math.sqrt(days.size))}
    (out / "d2_tuning.json").write_text(json.dumps(tuning, indent=1), encoding="utf-8")
    print("D2 tuning", tuning, flush=True)

    # ---- stage 2: all cells in parallel
    d3_ids = [f"IC{i}" for i in range(1, 10)] + ["S2", "REP"]
    specs = [("D1", "S127", a.n, 0.0)]
    specs += [("D2", sid, a.n, k) for sid in ("S2", "S15", "S127", "SEV", "REP")]
    specs += [("D3", sid, 2 * a.n if sid == "IC5" else a.n, 0.0) for sid in d3_ids]
    specs.sort(key=lambda s: -s[2])
    rows: dict[str, list[tuple]] = {"D1": [], "D2": [], "D3": []}
    timing = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for name, r, sec in ex.map(_task, specs):
            rows[name.split()[0]] += r
            timing.append({"cell": name, "seconds": sec})
            print(f"{name} done {sec}s", flush=True)
    for kind, label in (("D1", "d1"), ("D2", "d2"), ("D3", "d3")):
        rep = pd.DataFrame(rows[kind], columns=COLS)
        rep.to_csv(out / f"{label}_replicates.csv", index=False)
        measures.summarise(rep).to_csv(out / f"{label}_summary.csv", index=False)
        if kind == "D1":
            prim = pd.read_csv("study/results/full/replicates.csv")
            prim = prim[(prim.scenario == "REP") & prim.method.isin(["M2", "M4", "M5", "M7"]) & (prim.weights == "squared")]
            uncond(pd.concat([rep, prim[COLS]])).to_csv(out / "d1_unconditional.csv", index=False)
    pd.DataFrame(timing).to_csv(out / "run_extra_timing.csv", index=False)
    meta = {"post_hoc": True, "extra_key": EXTRA_KEY, "seed": SEED, "n": a.n, "k_tuned": k, "mean_score_rise_REP": rise,
            "S127_factor": S127.factor, "numpy": np.__version__, "pandas": pd.__version__, "wall_seconds": round(time.perf_counter() - t_start, 1)}
    (out / "run_extra_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("finished", meta, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
