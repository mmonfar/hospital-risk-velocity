"""CLI for the step 5 simulation: python -m study.sim.run --n 100 --out study/results/pilot.

Writes replicates.csv (one row per scenario x weights x replicate x method), summary.csv
(measures with MCSE), timing.csv and meta.json. --weights-study adds the Aim 5 runs
(IC5, S2, SEV, REP under four weight schemes) as weights_replicates.csv / weights_summary.csv.
Same --seed gives identical CSVs (timing.csv and meta.json aside).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from study.sim import charts, dgm, measures, shipped

# M6 (g-chart) is dropped from the compared set: protocol section 9 (c). Use --include-m6 to run it anyway.
COMPARED_CHARTS = tuple(m for m in charts.CHARTS if m != "M6")
ALL_METHODS = ("M1a_out", "M1a_any", "M1b_out", "M1b_any", *COMPARED_CHARTS)
WEIGHT_METHODS = ("M1a_out", "M1a_any", "M2", "M4", "M5")
WEIGHT_SCENARIOS = ("IC5", "S2", "SEV", "REP")
M1_VARIANTS = {"M1a_out": (2.0, "out"), "M1a_any": (2.0, "any"), "M1b_out": (3.0, "out"), "M1b_any": (3.0, "any")}


def _episodes(a: np.ndarray) -> int:
    return int((a & ~np.concatenate(([False], a[:-1]))).sum())


def evaluate_replicate(
    sc: dgm.Scenario,
    counts: np.ndarray,
    weights: np.ndarray,
    calib_rng: np.random.Generator,
    methods: tuple[str, ...],
    oracle: tuple[charts.Fit, dict[str, float]] | None = None,
) -> dict[str, tuple[int, int, int, float]]:
    """Return {method: (first_alarm_day or 0, alarm_days, episodes, revision)}."""
    p1 = dgm.PHASE1_DAYS
    x = counts @ weights
    n = counts.sum(axis=1)
    ne = counts[:, 4:].sum(axis=1)
    alarm: dict[str, np.ndarray] = {}
    rev: dict[str, float] = {}
    if any(m in M1_VARIANTS for m in methods):
        sigmas = tuple({M1_VARIANTS[m][0] for m in methods if m in M1_VARIANTS})
        st = shipped.status(x, n, sigmas)
        for m in methods:
            if m in M1_VARIANTS:
                sig, mode = M1_VARIANTS[m]
                s = st[sig][p1:]
                alarm[m] = (s == shipped.OUTSIDE) if mode == "out" else (s >= shipped.MARGINAL)
        if "M1a_out" in methods:
            ic_mean = sc.mu0 * float(dgm.PI0 @ weights)
            rev["M1a_out"] = shipped.endpoint_revision(x, p1, ic_mean)
    which = tuple(m for m in methods if m in charts.CHARTS)
    if which:
        if oracle is None:
            fit = charts.fit_phase1(counts[:p1], weights)
            th = charts.thresholds(fit, weights, calib_rng, which)
        else:
            fit, th = oracle
        alarm.update(charts.alarms({k: v for k, v in th.items() if k in which}, fit, x[p1:], n[p1:], ne[p1:]))
    out = {}
    for m in methods:
        a = alarm[m]
        first = p1 + 1 + int(a.argmax()) if a.any() else 0
        out[m] = (first, int(a.sum()), _episodes(a), rev.get(m, float("nan")))
    return out


ORACLE_REPS = 1000  # oracle pool: 1,000 continuations x 1,000 days (about 2% pool error on ARL0)


def _run_task(task: tuple) -> tuple[list[tuple], dict]:
    """One (scenario, weight scheme) cell: all replicates. Top-level so worker processes can run it."""
    sid, wname, n, seed, methods, calibration = task
    sc = dgm.BY_ID[sid]
    idx = dgm.SCENARIO_INDEX[sid]
    w = dgm.WEIGHT_SCHEMES[wname]
    t0 = time.perf_counter()
    oracle = None
    if calibration == "oracle":
        fit = charts.true_fit(sc, w)
        orng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(idx, 10**9)))
        which = tuple(m for m in methods if m in charts.CHARTS)
        oracle = (fit, charts.thresholds(fit, w, orng, which, reps=ORACLE_REPS) if which else {})
    rows = []
    for r in range(n):
        drng, crng = dgm.scenario_rngs(seed, idx, r)
        counts = dgm.simulate_stream(sc, drng)
        res = evaluate_replicate(sc, counts, w, crng, methods, oracle)
        for m, (first, ad, ep, rv) in res.items():
            rows.append((sid, wname, r, m, first, ad, ep, rv))
    return rows, {"scenario": sid, "weights": wname, "n": n, "seconds": round(time.perf_counter() - t0, 2)}


def run_scenarios(
    scenarios: list[dgm.Scenario],
    n_of: dict[str, int],
    seed: int,
    methods: tuple[str, ...],
    weight_names: tuple[str, ...],
    calibration: str,
    timing: list[dict],
    workers: int = 1,
) -> pd.DataFrame:
    tasks = [(sc.sid, wn, n_of[sc.sid], seed, methods, calibration) for sc in scenarios for wn in weight_names]
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=workers) as ex:
            results = ex.map(_run_task, tasks)  # results come back in task order: CSVs stay deterministic
            rows = []
            for r, t in results:
                rows += r
                timing.append(t)
                print(f"{t['scenario']} {t['weights']} n={t['n']} {t['seconds']}s", flush=True)
    else:
        rows = []
        for task in tasks:
            r, t = _run_task(task)
            rows += r
            timing.append(t)
            print(f"{t['scenario']} {t['weights']} n={t['n']} {t['seconds']}s", flush=True)
    return pd.DataFrame(rows, columns=["scenario", "weights", "rep", "method", "first_alarm", "alarm_days", "episodes", "revision"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=1000, help="replicates per scenario")
    ap.add_argument("--n-ic5", type=int, default=None, help="replicates for IC5 (default 2 x n)")
    ap.add_argument("--seed", type=int, default=dgm.ROOT_SEED)
    ap.add_argument("--scenarios", default="all", help="comma list of scenario ids, or 'all'")
    ap.add_argument("--out", default="study/results")
    ap.add_argument("--calibration", choices=["bootstrap", "oracle"], default="oracle", help="oracle = primary (protocol 9 b)")
    ap.add_argument("--workers", type=int, default=1, help="worker processes (one task = scenario x weight scheme)")
    ap.add_argument("--include-m6", action="store_true", help="also run the g-chart M6 (never reaches ARL0 365)")
    ap.add_argument("--weights-study", action="store_true", help="also run the Aim 5 weight-scheme runs")
    a = ap.parse_args(argv)

    ids = [s.sid for s in dgm.SCENARIOS] if a.scenarios == "all" else a.scenarios.split(",")
    unknown = [i for i in ids if i not in dgm.BY_ID]
    if unknown:
        ap.error(f"unknown scenarios: {unknown}")
    scenarios = [dgm.BY_ID[i] for i in ids]
    n_of = {s.sid: (a.n_ic5 if (s.sid == "IC5" and a.n_ic5) else (2 * a.n if s.sid == "IC5" else a.n)) for s in scenarios}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    timing: list[dict] = []

    methods = (*ALL_METHODS, "M6") if a.include_m6 else ALL_METHODS
    wmethods = (*WEIGHT_METHODS, "M6") if a.include_m6 else WEIGHT_METHODS
    rep = run_scenarios(scenarios, n_of, a.seed, methods, ("squared",), a.calibration, timing, a.workers)
    rep.to_csv(out / "replicates.csv", index=False)
    measures.summarise(rep).to_csv(out / "summary.csv", index=False)

    if a.weights_study:
        wsc = [dgm.BY_ID[i] for i in WEIGHT_SCENARIOS if i in ids or a.scenarios == "all"]
        wrep = run_scenarios(wsc, n_of, a.seed, wmethods, tuple(dgm.WEIGHT_SCHEMES), a.calibration, timing, a.workers)
        wrep.to_csv(out / "weights_replicates.csv", index=False)
        measures.summarise(wrep).to_csv(out / "weights_summary.csv", index=False)

    pd.DataFrame(timing).to_csv(out / "timing.csv", index=False)
    meta = {"seed": a.seed, "n": n_of, "calibration": a.calibration, "oracle_reps": ORACLE_REPS, "include_m6": a.include_m6, "numpy": np.__version__, "pandas": pd.__version__}
    (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
