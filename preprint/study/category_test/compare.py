"""Parity gate and comparison table for the count-by-harm-category test. See RULES.md.

Run from the repo root: py -3.11 study/category_test/compare.py
The gate needs study/larger_run/output/replicates.csv (regenerated from seed 20261104).
"""
from pathlib import Path

import pandas as pd

HERE = Path("study/category_test")
OUT = HERE / "output"
LARGER = Path("study/larger_run")
if not (OUT / "summary.csv").exists():
    OUT = HERE
SCEN = ["IC2", "IC5", "IC8", "S15", "S2", "S2-small", "S2-large", "R60", "SEV", "REP"]

c = pd.read_csv(OUT / "summary.csv")
gate_file = OUT / "replicates.csv"
if gate_file.exists():
    d = pd.read_csv(gate_file, usecols=["scenario", "rep", "method", "first_alarm"])
    d = d[d.method == "M7"]
    o = pd.read_csv(LARGER / "output" / "replicates.csv", usecols=["scenario", "weights", "rep", "method", "first_alarm"])
    o = o[(o.method == "M7") & (o.weights == "squared") & o.scenario.isin(d.scenario.unique())]
    m = d.merge(o, on=["scenario", "rep"], suffixes=("", "_o"))
    print("GATE rows", len(m), "of", len(d), "mismatch", int((m.first_alarm != m.first_alarm_o).sum()))

s = pd.read_csv(LARGER / "summary.csv")
w = pd.read_csv(LARGER / "weights_summary.csv")
rows = []
for _, r in c[c.scenario.isin(SCEN)].iterrows():
    rows.append({"scenario": r.scenario, "chart": r.method, "arl0": r.arl0, "fa365": r.fa365, "pod30": r.pod30, "pod30_mcse": r.pod30_mcse, "pre_tau_fa": r.pre_tau_fa})
for me in ["M2", "M4", "M5", "M7"]:
    for _, r in s[(s.method == me) & s.scenario.isin(SCEN) & (s.weights == "squared")].iterrows():
        rows.append({"scenario": r.scenario, "chart": me + " squared" if me != "M7" else "M7 larger", "arl0": r.arl0, "fa365": r.fa365, "pod30": r.pod30, "pod30_mcse": r.pod30_mcse, "pre_tau_fa": r.pre_tau_fa})
for me in ["M2", "M4", "M5"]:
    for sch in ["linear", "harm_only"]:
        for _, r in w[(w.method == me) & (w.weights == sch)].iterrows():
            rows.append({"scenario": r.scenario, "chart": f"{me} {sch}", "arl0": r.arl0, "fa365": r.fa365, "pod30": r.pod30, "pod30_mcse": r.pod30_mcse, "pre_tau_fa": r.pre_tau_fa})
t = pd.DataFrame(rows)
t.round(4).to_csv(HERE / "comparison.csv", index=False)

show = ["C1", "C2", "C3", "C4", "C5", "C6", "M7", "M2 squared", "M2 linear", "M2 harm_only", "M4 squared", "M4 linear", "M4 harm_only", "M5 squared", "M5 linear"]
core = t[t.chart.isin(show)]
pod = core[core.scenario.isin(SCEN[3:])].pivot(index="chart", columns="scenario", values="pod30").reindex(show)[[x for x in SCEN[3:]]]
arl = core[core.scenario.isin(SCEN[:3])].pivot(index="chart", columns="scenario", values="arl0").reindex(show)[SCEN[:3]]
fa = core[core.scenario == "IC5"].set_index("chart").fa365.reindex(show)
print(pd.concat([arl.round(0), fa.round(2).rename("FA365"), pod.round(3)], axis=1).to_string())
