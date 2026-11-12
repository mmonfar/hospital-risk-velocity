"""POST HOC addendum 3 (9 Nov 2026): one more tuning each for EWMA (M4) and CUSUM (M5).

python -m study.extra.run_addendum3 --workers 10 --out study/results/extra

Rules fixed before the run: study/protocol_addendum_3_2026-11-09.md.
New tunings: M4 lambda = 0.10 (primary 0.20); M5 reference = 0.25 SD (primary 0.5 SD).
Scenarios S2, S15, SEV, REP, IC5. Oracle calibration only, same seed, same pool and same streams
as the primary run. Gate: the primary tuning must reproduce the primary replicates exactly.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from study.sim import charts, dgm, measures, run

SCENARIOS = ("S2", "S15", "SEV", "REP", "IC5")
LAM_NEW, REF_NEW = 0.10, 0.25
W = dgm.WEIGHT_SCHEMES["squared"]
COLS = ["scenario", "weights", "rep", "method", "first_alarm", "alarm_days", "episodes", "revision"]


def _task(sid: str) -> tuple[list[tuple], dict]:
    t0 = time.perf_counter()
    sc, idx = dgm.BY_ID[sid], dgm.SCENARIO_INDEX[sid]
    n = 2000 if sid == "IC5" else 1000
    fit = charts.true_fit(sc, W)
    seed = dgm.ROOT_SEED

    def pool():  # the same oracle pool as the primary run
        return np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(idx, 10**9)))

    th0 = charts.thresholds(fit, W, pool(), ("M4", "M5"), reps=run.ORACLE_REPS)
    th1 = charts.thresholds(fit, W, pool(), ("M4", "M5"), reps=run.ORACLE_REPS, lam=LAM_NEW, cusum_ref_sd=REF_NEW)
    rows = []
    for r in range(n):
        drng, _ = dgm.scenario_rngs(seed, idx, r)
        counts = dgm.simulate_stream(sc, drng)
        p1 = dgm.PHASE1_DAYS
        x, nn, ne = counts @ W, counts.sum(axis=1), counts[:, 4:].sum(axis=1)
        a0 = charts.alarms(th0, fit, x[p1:], nn[p1:], ne[p1:])
        a1 = charts.alarms(th1, fit, x[p1:], nn[p1:], ne[p1:], lam=LAM_NEW, cusum_ref_sd=REF_NEW)
        for name, a in (("M4", a0["M4"]), ("M5", a0["M5"]), ("M4_lam010", a1["M4"]), ("M5_ref025", a1["M5"])):
            first = p1 + 1 + int(a.argmax()) if a.any() else 0
            rows.append((sid, "squared", r, name, first, int(a.sum()), run._episodes(a), float("nan")))
    return rows, {"scenario": sid, "n": n, "seconds": round(time.perf_counter() - t0, 1)}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="study/results/extra")
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    out = Path(a.out)
    t0 = time.perf_counter()
    rows, timing = [], []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r, t in ex.map(_task, SCENARIOS):
            rows += r
            timing.append(t)
            print(t, flush=True)
    rep = pd.DataFrame(rows, columns=COLS)
    prim = pd.read_csv("study/results/full/replicates.csv")
    prim = prim[prim.scenario.isin(SCENARIOS) & prim.method.isin(["M4", "M5"]) & (prim.weights == "squared")]
    mine = rep[rep.method.isin(["M4", "M5"])]
    key = ["scenario", "rep", "method"]
    m = prim.merge(mine, on=key, suffixes=("_p", "_n"))
    ok = len(m) == len(prim) == len(mine) and all((m[c + "_p"] == m[c + "_n"]).all() for c in ("first_alarm", "alarm_days", "episodes"))
    print("GATE (primary tuning reproduces primary run):", "PASS" if ok else "FAIL", flush=True)
    if not ok:
        return 1
    rep.to_csv(out / "g1_replicates.csv", index=False)
    measures.summarise(rep).to_csv(out / "g1_summary.csv", index=False)
    pd.DataFrame(timing).to_csv(out / "g1_timing.csv", index=False)
    meta = {"post_hoc": True, "lambda_new": LAM_NEW, "cusum_ref_sd_new": REF_NEW, "scenarios": SCENARIOS, "gate": "PASS",
            "wall_seconds": round(time.perf_counter() - t0, 1), "numpy": np.__version__, "pandas": pd.__version__}
    (out / "g1_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(meta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
