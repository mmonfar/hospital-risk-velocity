"""Gate 1 of RULES.md: first alarms of BASE against the earlier runs, replicate by replicate. Exit 1 if any differ.

Run from the repo root: py -3.11 -m study.severity_mix.parity study/severity_mix/output/BASE/replicates.csv
"""
from __future__ import annotations

import json
import sys

import pandas as pd

KEYS = ["scenario", "rep", "method"]
OLD = {
    "larger_run weights": ("study/larger_run/output/weights_replicates.csv", ["M1a_out", "M1a_any", "M2", "M4", "M5"], True),
    "larger_run M7": ("study/larger_run/output/replicates.csv", ["M7"], False),
    "category test C4 C5": ("study/category_test/output/replicates.csv", ["C4", "C5"], False),
    "pair run C7": ("study/category_test/output_pairs/replicates.csv", ["C7"], False),
}


def main() -> int:
    new = pd.read_csv(sys.argv[1], usecols=["limits", "scenario", "weights", "rep", "method", "first_alarm"])
    new = new[new.limits == "recalibrated"]
    report: dict = {}
    bad = done = 0
    for label, (path, methods, by_weight) in OLD.items():
        s = new[new.method.isin(methods)]
        old = pd.read_csv(path, usecols=["scenario", "weights", "rep", "method", "first_alarm"])
        keys = KEYS + ["weights"] if by_weight else KEYS
        j = s.merge(old[keys + ["first_alarm"]], on=keys, how="left", suffixes=("", "_old"))
        missing, differ = int(j.first_alarm_old.isna().sum()), int((j.first_alarm != j.first_alarm_old).sum())
        report[label] = {"compared": len(j), "missing": missing, "differ": differ}
        bad += missing + differ
        done += len(j)
    report["rows in BASE"] = len(new)
    report["rows compared"] = done
    report["passed"] = bad == 0 and done == len(new)
    print(json.dumps(report, indent=1))
    with open("study/severity_mix/parity.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
