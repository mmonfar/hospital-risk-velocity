"""Count by harm category: charts C1-C6 on the same data as the larger run. See RULES.md.

Run from the repo root: py -3.11 -m study.category_test.run --out study/category_test/output
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from study.sim import charts, dgm, measures

SCENARIOS = ("IC2", "IC5", "IC8", "S15", "S2", "S2-small", "S2-large", "R60", "SEV", "REP")
LAM = charts.LAMBDA
TARGET = 365


def _level_params(sc: dgm.Scenario) -> tuple[np.ndarray, np.ndarray]:
    mean = sc.mu0 * dgm.PI0
    var = mean + (0.0 if np.isinf(sc.theta) else mean**2 / sc.theta)
    return mean, np.sqrt(var * LAM / (2 - LAM))


def _max_std_ewma(counts: np.ndarray, mean: np.ndarray, sd: np.ndarray) -> np.ndarray:
    """Largest standardised level EWMA per day. counts: (..., days, 9)."""
    moved = np.moveaxis(counts.astype(float), -1, 0)  # (9, ..., days)
    best = None
    for i in range(9):
        z = (charts.ewma_paths(moved[i], LAM, float(mean[i])) - mean[i]) / sd[i]
        best = z if best is None else np.maximum(best, z)
    return best


def calibrate(sc: dgm.Scenario, seed: int, idx: int, reps: int = 1000, horizon: int = 1000) -> dict[str, object]:
    rng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(idx, 10**9 + 7)))
    mean, sd = _level_params(sc)
    n = dgm.draw_n(rng, np.full((reps, horizon), sc.mu0), sc.theta)
    lev = rng.multinomial(n, dgm.PI0)
    e_i = lev[..., 4:].sum(axis=-1).astype(float)
    m_ei = float(mean[4:].sum())
    return {
        "C1": np.array([charts.nb_upper_quantile(float(m), sc.theta, 1 - 1 / TARGET) for m in mean]),
        "C2": np.array([charts.nb_upper_quantile(float(m), sc.theta, 1 - 1 / (9 * TARGET)) for m in mean]),
        "C3": charts.nb_upper_quantile(m_ei, sc.theta, 1 - 1 / TARGET),
        "C4": charts.calibrate_threshold(charts.ewma_paths(e_i, LAM, m_ei)),
        "C5": charts.calibrate_threshold(charts.ewma_paths(n.astype(float), LAM, sc.mu0)),
        "C6": charts.calibrate_threshold(_max_std_ewma(lev, mean, sd)),
        "M7": charts.nb_upper_quantile(sc.mu0, sc.theta, 1 - 1 / TARGET),
    }


def _episodes(a: np.ndarray) -> int:
    return int((a & ~np.concatenate(([False], a[:-1]))).sum())


def evaluate(sc: dgm.Scenario, counts: np.ndarray, th: dict[str, object]) -> dict[str, np.ndarray]:
    mean, sd = _level_params(sc)
    c = counts[dgm.PHASE1_DAYS :]
    n = c.sum(axis=1)
    e_i = c[:, 4:].sum(axis=1).astype(float)
    m_ei = float(mean[4:].sum())
    return {
        "C1": (c > th["C1"]).any(axis=1),
        "C2": (c > th["C2"]).any(axis=1),
        "C3": e_i > th["C3"],
        "C4": charts.ewma_paths(e_i, LAM, m_ei) > th["C4"],
        "C5": charts.ewma_paths(n.astype(float), LAM, sc.mu0) > th["C5"],
        "C6": _max_std_ewma(c, mean, sd) > th["C6"],
        "M7": n > th["M7"],
    }


def run_task(task: tuple[str, int, int]) -> tuple[list[tuple], dict]:
    sid, n, seed = task
    sc = dgm.BY_ID[sid]
    idx = dgm.SCENARIO_INDEX[sid]
    th = calibrate(sc, seed, idx)
    rows = []
    for r in range(n):
        drng, _ = dgm.scenario_rngs(seed, idx, r)
        res = evaluate(sc, dgm.simulate_stream(sc, drng), th)
        for m, a in res.items():
            first = dgm.PHASE1_DAYS + 1 + int(a.argmax()) if a.any() else 0
            rows.append((sid, "none", r, m, first, int(a.sum()), _episodes(a), float("nan")))
    lim = {k: (v.tolist() if isinstance(v, np.ndarray) else float(v)) for k, v in th.items()}
    return rows, {"scenario": sid, **lim}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--n-ic5", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=20261104)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tasks = [(s, a.n_ic5 if s == "IC5" else a.n, a.seed) for s in a.scenarios.split(",")]
    rows, limits = [], []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r, lim in ex.map(run_task, tasks):
            rows += r
            limits.append(lim)
            print(lim["scenario"], "done", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = pd.DataFrame(rows, columns=["scenario", "weights", "rep", "method", "first_alarm", "alarm_days", "episodes", "revision"])
    rep.to_csv(out / "replicates.csv", index=False)
    measures.summarise(rep).to_csv(out / "summary.csv", index=False)
    pd.DataFrame(limits).to_json(out / "limits.json", orient="records", indent=1)


if __name__ == "__main__":
    main()
