"""Spread between seeds for charts C1-C6 at the original run size. See RULES.md.

Run from the repo root: py -3.11 study/category_test/seed_spread.py <folders holding s<seed>/summary.csv>
"""
import sys
from pathlib import Path

import pandas as pd

rows = []
for f in [g for a in sys.argv[1:] for g in sorted(Path(a).glob("s*/summary.csv"))]:
    d = pd.read_csv(f)
    d["seed"] = f.parent.name
    rows.append(d)
d = pd.concat(rows)
d["value"] = d.arl0.fillna(d.pod30)
d["mcse"] = d.arl0_mcse.fillna(d.pod30_mcse)
s = d.groupby(["scenario", "method"]).agg(seeds=("seed", "nunique"), mean=("value", "mean"), sd_between_seeds=("value", "std"), mean_mcse=("mcse", "mean"), low=("value", "min"), high=("value", "max")).round(3).reset_index()
s["ratio"] = (s.sd_between_seeds / s.mean_mcse).round(2)
s.to_csv("study/category_test/seed_spread.csv", index=False)
print(s.to_string(index=False))
