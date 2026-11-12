"""Diagnostic added after the larger run: how much do results move between seeds at the frozen run size?

Each seed redraws both the data and the calibration pool. Monte Carlo standard errors cover the data only.
Run from the repo root: py -3.11 study/larger_run/seed_spread.py <temp_dir>
"""
import subprocess
import sys

import pandas as pd

tmp = sys.argv[1]
rows = []
for seed in range(20261201, 20261211):
    out = f"{tmp}/s{seed}"
    subprocess.run([sys.executable, "-m", "study.sim.run", "--n", "1000", "--seed", str(seed), "--scenarios", "IC5,S2,SEV,REP", "--workers", "4", "--out", out],
                   check=True, capture_output=True)
    d = pd.read_csv(f"{out}/summary.csv")
    d["seed"] = seed
    rows.append(d[d.method.isin(["M2", "M4", "M5", "M7"])])
d = pd.concat(rows)
d["value"] = d.arl0.fillna(d.pod30)
d["mcse"] = d.arl0_mcse.fillna(d.pod30_mcse)
s = d.groupby(["scenario", "method"]).agg(mean=("value", "mean"), sd_between_seeds=("value", "std"), mean_mcse=("mcse", "mean"), low=("value", "min"), high=("value", "max")).round(3).reset_index()
s["ratio"] = (s.sd_between_seeds / s.mean_mcse).round(2)
s.to_csv("study/larger_run/seed_spread.csv", index=False)
print(s.to_string(index=False))
