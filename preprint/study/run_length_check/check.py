"""Is the ARL0 estimator (days at risk / first alarms) close to the mean run length? Saved runs only; no new simulation.

Compares it with a survival-based mean: area under the Kaplan-Meier curve to day 1,095, plus an exponential tail
fitted to the hazard of the last 365 days. Added after the results and not in the protocol.
Run from the repo root, after the larger run and category test outputs exist: py -3.11 study/run_length_check/check.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

from study.sim import dgm

FILES = ["study/larger_run/output/replicates.csv", "study/larger_run/output/weights_replicates.csv", "study/category_test/output/replicates.csv", "study/category_test/output_pairs/replicates.csv"]
H = dgm.MONITOR_IC
rows = []
for f in FILES:
    d = pd.read_csv(f, usecols=["scenario", "weights", "method", "first_alarm"])
    d = d[d.scenario.str.startswith("IC")]
    for (sc, wt, m), g in d.groupby(["scenario", "weights", "method"]):
        e = g.first_alarm.values > 0
        if (~e).sum() < 5:
            continue  # almost nothing censored: the estimator is then the plain mean run length
        t = np.where(e, g.first_alarm.values - dgm.PHASE1_DAYS, H)
        surv = np.array([1 - ((t <= k) & e).mean() for k in range(H + 1)])
        hazard = -np.log(surv[H] / surv[H - 365]) / 365
        area = surv[:H].sum()
        rows.append((sc, wt, m, len(g), round(1 - e.mean(), 3), round(t.sum() / e.sum(), 1), round(area, 1), round(area + surv[H] / hazard, 1)))
o = pd.DataFrame(rows, columns=["scenario", "weights", "method", "n", "censored_share", "arl0_paper", "restricted_mean_1095", "mean_with_tail"]).drop_duplicates()
o["diff_pct"] = (100 * (o.mean_with_tail / o.arl0_paper - 1)).round(1)
o.to_csv(Path("study/run_length_check/run_length_check.csv"), index=False)
print(len(o), "rows; largest gap", o.diff_pct.abs().max(), "%")
print(o.reindex(o.diff_pct.abs().sort_values(ascending=False).index).head(6).to_string(index=False))
c = o[o.censored_share <= 0.10]
print("censored <=10%:", len(c), "largest gap", c.diff_pct.abs().max())
print(o[(o.scenario == "IC5") & (o.method.isin(["M2", "M4", "M5", "M7", "C4", "C5", "C7"]))&(o.weights.isin(["squared", "none"]))].to_string(index=False))
