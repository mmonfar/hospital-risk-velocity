"""Two monitors run together: combine first alarms from the saved replicates of the simulation study.

No new simulation. A pair alarms on the day the first of its two charts alarms. The charts share data streams and
keep their own limits, set for one chart alone at an in-control average run length of 365 days. Measures follow the study: run length =
days at risk / first alarms, 1,095 days in control; POD30 among runs with no alarm before the change on day 181.

Run: py -3.11 docs/evidence/two_monitors.py <weights_replicates.csv> docs/evidence/two_monitors.csv
"""
import sys

import numpy as np
import pandas as pd

PHASE1_DAYS, TAU, MONITOR_IC = 120, 181, 1095
PAIRS = [("squared",), ("linear",), ("harm_only",), ("squared", "harm_only"), ("linear", "harm_only")]


def earliest(wide: pd.DataFrame, schemes: tuple[str, ...]) -> np.ndarray:
    # first_alarm 0 means no alarm in the run
    days = wide[list(schemes)].to_numpy(dtype=float, copy=True)
    days[days == 0] = np.inf
    first = days.min(axis=1)
    first[np.isinf(first)] = 0
    return first


def measures(first: np.ndarray, scenario: str) -> dict[str, float]:
    alarmed = first > 0
    if scenario == "IC5":
        run = np.where(alarmed, first - PHASE1_DAYS, MONITOR_IC)
        k = int(alarmed.sum())
        return {"arl0": run.sum() / k, "arl0_mcse": run.sum() / k / np.sqrt(k),
                "fa365": float((alarmed & (run <= 365)).mean())}
    eligible = ~(alarmed & (first < TAU))
    p = float((eligible & alarmed & (first - TAU <= 29)).sum() / eligible.sum())
    return {"pod30": p, "pod30_mcse": float(np.sqrt(p * (1 - p) / eligible.sum()))}


def main(source: str, out: str) -> None:
    rep = pd.read_csv(source)
    rows = []
    for (scenario, method), g in rep[rep.method.isin(["M2", "M4", "M5"])].groupby(["scenario", "method"]):
        wide = g.pivot(index="rep", columns="weights", values="first_alarm")
        for schemes in PAIRS:
            rows.append({"scenario": scenario, "method": method, "monitors": " + ".join(schemes),
                         **measures(earliest(wide, schemes), scenario)})
    pd.DataFrame(rows).round(4).to_csv(out, index=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
