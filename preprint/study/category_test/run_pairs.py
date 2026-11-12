"""Charts C7 and C8: two count EWMAs held to one false-alarm target. See RULES_ADDENDUM.md.

Run from the repo root: py -3.11 -m study.category_test.run_pairs --out study/category_test/output_pairs
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from study.category_test.run import LAM, SCENARIOS, _episodes
from study.sim import charts, dgm, measures

GROUPS = {"C7": (np.arange(9), np.arange(4, 9)), "C8": (np.arange(4), np.arange(4, 9))}


def _params(sc: dgm.Scenario, idx: np.ndarray) -> tuple[float, float]:
    mean = float(sc.mu0 * dgm.PI0[idx].sum())
    var = mean + (0.0 if np.isinf(sc.theta) else mean**2 / sc.theta)
    return mean, float(np.sqrt(var * LAM / (2 - LAM)))


def _stat(sc: dgm.Scenario, counts: np.ndarray, groups: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    best = None
    for idx in groups:
        mean, sd = _params(sc, idx)
        z = (charts.ewma_paths(counts[..., idx].sum(axis=-1).astype(float), LAM, mean) - mean) / sd
        best = z if best is None else np.maximum(best, z)
    return best


def run_task(task: tuple[str, int, int]) -> list[tuple]:
    sid, n, seed = task
    sc = dgm.BY_ID[sid]
    idx = dgm.SCENARIO_INDEX[sid]
    rng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(idx, 10**9 + 7)))
    pool = rng.multinomial(dgm.draw_n(rng, np.full((1000, 1000), sc.mu0), sc.theta), dgm.PI0)
    th = {m: charts.calibrate_threshold(_stat(sc, pool, g)) for m, g in GROUPS.items()}
    rows = []
    for r in range(n):
        drng, _ = dgm.scenario_rngs(seed, idx, r)
        c = dgm.simulate_stream(sc, drng)[dgm.PHASE1_DAYS :]
        for m, g in GROUPS.items():
            a = _stat(sc, c, g) > th[m]
            first = dgm.PHASE1_DAYS + 1 + int(a.argmax()) if a.any() else 0
            rows.append((sid, "none", r, m, first, int(a.sum()), _episodes(a), float("nan")))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--n-ic5", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20261104)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tasks = [(s, a.n_ic5 if s == "IC5" else a.n, a.seed) for s in a.scenarios.split(",")]
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(run_task, tasks):
            rows += r
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = pd.DataFrame(rows, columns=["scenario", "weights", "rep", "method", "first_alarm", "alarm_days", "episodes", "revision"])
    rep.to_csv(out / "replicates.csv", index=False)
    measures.summarise(rep).to_csv(out / "summary.csv", index=False)


if __name__ == "__main__":
    main()
