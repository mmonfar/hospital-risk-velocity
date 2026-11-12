"""Compare the larger run with the frozen results by the rules in RULES.md. Writes comparison.csv and prints the verdict.

Run from the repo root: py -3.11 study/larger_run/compare.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("study/results/full")
NEW = Path("study/larger_run")
KEYS = ["scenario", "weights", "method"]


def pair(name: str) -> pd.DataFrame:
    old, new = pd.read_csv(ROOT / name), pd.read_csv(NEW / name)
    rows = []
    for est, se in (("arl0", "arl0_mcse"), ("pod30", "pod30_mcse")):
        m = old[KEYS + [est, se]].merge(new[KEYS + [est, se, "n"]], on=KEYS, suffixes=("_old", "_new")).dropna(subset=[est + "_old", est + "_new"])
        m = m.rename(columns={est + "_old": "old", est + "_new": "new", se + "_old": "se_old", se + "_new": "se_new"})
        m["measure"] = est
        rows.append(m)
    d = pd.concat(rows)
    d["source"] = name
    return d


d = pd.concat([pair("summary.csv"), pair("weights_summary.csv")]).drop_duplicates(KEYS + ["measure"])
d["z"] = (d.new - d.old) / np.sqrt(d.se_old**2 + d.se_new**2)
d["flag_3se"] = d.z.abs() > 3
d["flag_practical"] = np.where(d.measure == "pod30", (d.new - d.old).abs() > 0.05, ((d.new - d.old) / d.old).abs() > 0.15)
d.round(4).to_csv("study/larger_run/comparison.csv", index=False)
print("comparisons", len(d), "| above 3 SE", int(d.flag_3se.sum()), "| practical", int(d.flag_practical.sum()), "| n", sorted(d.n.unique()))
print(d[d.flag_3se | d.flag_practical][KEYS + ["measure", "old", "new", "z", "flag_3se", "flag_practical"]].round(3).to_string(index=False))

w = pd.read_csv(NEW / "weights_summary.csv").set_index(["scenario", "weights", "method"])
s = pd.read_csv(NEW / "summary.csv").query("weights == 'squared'").set_index(["scenario", "method"])
wp = lambda sc, sch, me="M4": (w.loc[(sc, sch, me), "pod30"], w.loc[(sc, sch, me), "pod30_mcse"])
sp = lambda sc, me: (s.loc[(sc, me), "pod30"], s.loc[(sc, me), "pod30_mcse"])


def above(a, b):
    return bool(a[0] - b[0] > 2 * np.hypot(a[1], b[1]))


checks = {
    "S2 arithmetic > squared": above(wp("S2", "linear"), wp("S2", "squared")),
    "S2 squared > harm-only": above(wp("S2", "squared"), wp("S2", "harm_only")),
    "SEV harm-only > squared": above(wp("SEV", "harm_only"), wp("SEV", "squared")),
    "SEV squared > arithmetic": above(wp("SEV", "squared"), wp("SEV", "linear")),
    "REP arithmetic > squared": above(wp("REP", "linear"), wp("REP", "squared")),
    "REP squared > harm-only": above(wp("REP", "squared"), wp("REP", "harm_only")),
    "S2 M4 > M7": above(sp("S2", "M4"), sp("S2", "M7")),
    "S2 M5 > M7": above(sp("S2", "M5"), sp("S2", "M7")),
    "SEV M2 > M7": above(sp("SEV", "M2"), sp("SEV", "M7")),
    "SEV M4 > M7": above(sp("SEV", "M4"), sp("SEV", "M7")),
    "SEV M5 > M7": above(sp("SEV", "M5"), sp("SEV", "M7")),
}
for k, v in checks.items():
    print(f"{k}: {'holds' if v else 'DOES NOT HOLD'}")
