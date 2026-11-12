"""Gate 2 of RULES.md: generator moments of each arm, and M7 and C5 equal across the flat mixes where counts are equal.

Run from the repo root: py -3.11 -m study.severity_mix.arm_checks moments
                        py -3.11 -m study.severity_mix.arm_checks invariance study/severity_mix/output
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from study.severity_mix.run import ARMS, SCENARIOS, MIXES, mean_path, pi_after, simulate
from study.sim import dgm

N = 500
CHECK_SEED = 777  # apart from the study seeds


def moments() -> pd.DataFrame:
    rows = []
    for arm in ARMS.values():
        pi = MIXES[arm.mix]
        for sid in SCENARIOS:
            sc, idx = dgm.BY_ID[sid], dgm.SCENARIO_INDEX[sid]
            mu = mean_path(sc, pi, arm.weekday)
            before, after = [], []
            for r in range(N):
                drng, _ = dgm.scenario_rngs(CHECK_SEED, idx, r)
                c = simulate(sc, drng, pi, arm.weekday)
                before.append(c[: dgm.TAU - 1].sum(axis=0))
                after.append(c[dgm.TAU - 1 :].sum(axis=0))
            pairs = [(np.array(before, float), mu[: dgm.TAU - 1].sum() * pi), (np.array(after, float), mu[dgm.TAU - 1 :].sum() * pi_after(sc, pi))]
            z = np.concatenate([(a.mean(axis=0) - e) / (a.std(axis=0, ddof=1) / np.sqrt(N)) for a, e in pairs])
            rows.append({"arm": arm.name, "scenario": sid, "checks": z.size, "beyond_3_mcse": int((np.abs(z) > 3).sum()), "largest_abs_z": round(float(np.abs(z).max()), 2)})
    return pd.DataFrame(rows)


def invariance(out: Path) -> pd.DataFrame:
    cols = ["limits", "scenario", "rep", "method", "first_alarm"]

    def read(name: str) -> pd.DataFrame:
        d = pd.read_csv(out / name / "replicates.csv", usecols=cols)
        return d[(d.limits == "recalibrated") & d.method.isin(["M7", "C5"]) & d.scenario.isin(["IC5", "S2", "SEV"])]

    base = read("BASE")
    rows = []
    for arm in ARMS.values():
        if arm.weekday or arm.name == "BASE":
            continue
        j = base.merge(read(arm.name), on=["scenario", "rep", "method"], suffixes=("", "_arm"))
        rows.append({"arm": arm.name, "compared": len(j), "differ": int((j.first_alarm != j.first_alarm_arm).sum())})
    return pd.DataFrame(rows)


def main() -> None:
    if sys.argv[1] == "moments":
        m = moments()
        m.to_csv("study/severity_mix/arm_checks.csv", index=False)
        print("beyond 3 MCSE", m.beyond_3_mcse.sum(), "of", m.checks.sum(), "largest", m.largest_abs_z.max())
    else:
        i = invariance(Path(sys.argv[2]))
        i.to_csv("study/severity_mix/invariance.csv", index=False)
        print(i.to_string(index=False))


if __name__ == "__main__":
    main()
