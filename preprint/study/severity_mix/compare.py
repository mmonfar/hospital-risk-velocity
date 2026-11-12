"""Applies the reading rule of RULES.md to the saved runs. No new simulation.

Run from the repo root: py -3.11 -m study.severity_mix.compare study/severity_mix/output study/severity_mix/output_seeds
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from study.severity_mix.run import ARMS, SCENARIOS

HERE = Path("study/severity_mix")
BAND = (310.0, 420.0)
FLOOR = 0.01
NOT_IN_BAND_RULE = ("M7", "M1a_out", "M1a_any")
SQ, LIN, HARM = "squared", "linear", "harm_only"
M4S, M5S, M2S, M4L, M4H = ("M4", SQ), ("M5", SQ), ("M2", SQ), ("M4", LIN), ("M4", HARM)
M7, C4, C5, C7 = ("M7", "none"), ("C4", "none"), ("C5", "none"), ("C7", "none")

# number, group, (scenario, chart) above (scenario, chart)
ORDERINGS = [
    (1, "A", "S2", M4L, "S2", M4S), (2, "A", "S2", M4S, "S2", M4H), (3, "A", "SEV", M4H, "SEV", M4S),
    (4, "A", "SEV", M4S, "SEV", M4L), (5, "A", "REP", M4S, "REP", M4H), (6, "A", "REP", M4L, "REP", M4S),
    (7, "B", "S2", M4S, "S2", M7), (8, "B", "S2", M5S, "S2", M7), (9, "B", "SEV", M2S, "SEV", M7),
    (10, "B", "SEV", M4S, "SEV", M7), (11, "B", "SEV", M5S, "SEV", M7),
    (12, "C", "S2", C5, "S2", M4S), (13, "C", "S2", M4S, "S2", C4), (14, "C", "SEV", C4, "SEV", M4S),
    (15, "C", "SEV", M4S, "SEV", C5), (16, "C", "REP", M4S, "REP", C4), (17, "C", "REP", C5, "REP", M4S),
    (18, "C", "SEV", M4L, "SEV", C5), (19, "C", "REP", C5, "REP", M4L),
    (20, "D", "S2", C7, "S2", M4S), (21, "D", "SEV", C7, "SEV", M4S), (22, "D", "REP", C7, "REP", M4S),
    (23, "E", "SEV", M4S, "REP", M4S),
]


def _value(d: pd.DataFrame) -> pd.Series:
    return d.arl0.where(d.scenario == "IC5", d.pod30)


def load(out: Path, seeds: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    main_runs = pd.concat(pd.read_csv(out / a / "summary.csv") for a in ARMS)
    main_runs["value"] = _value(main_runs)
    rows = []
    for f in seeds.glob("s*/*/summary.csv"):
        d = pd.read_csv(f)
        d["seed"] = f.parent.parent.name
        rows.append(d)
    s = pd.concat(rows)
    s = s[s.limits == "recalibrated"]
    s["value"] = _value(s)
    sd = s.groupby(["arm", "scenario", "weights", "method"]).agg(seeds=("seed", "nunique"), seed_mean=("value", "mean"), sd=("value", "std")).reset_index()
    return main_runs, sd


class Reader:
    def __init__(self, main_runs: pd.DataFrame, sd: pd.DataFrame) -> None:
        r = main_runs[main_runs.limits == "recalibrated"]
        self.v = r.set_index(["arm", "scenario", "method", "weights"])["value"].to_dict()
        self.sd = sd.set_index(["arm", "scenario", "method", "weights"])["sd"].to_dict()

    def val(self, arm: str, sid: str, chart: tuple[str, str]) -> float:
        return self.v[(arm, sid, *chart)]

    def spread(self, arm: str, sid: str, chart: tuple[str, str]) -> float:
        return self.sd[(arm, sid, *chart)]

    def in_band(self, arm: str, chart: tuple[str, str]) -> bool:
        if chart[0] in NOT_IN_BAND_RULE:
            return True
        return BAND[0] <= self.val(arm, "IC5", chart) <= BAND[1]


def status(gap: float, s: float, band_ok: bool) -> str:
    if not band_ok:
        return "Cannot say"
    if gap > 2 * s:
        return "Held"
    return "Flipped" if -gap > 2 * s else "Not separated"


def orderings(rd: Reader) -> pd.DataFrame:
    rows = []
    for no, grp, sa, a, sb, b in ORDERINGS:
        base_ok = None
        for arm in ARMS:
            va, vb = rd.val(arm, sa, a), rd.val(arm, sb, b)
            s = max(rd.spread(arm, sa, a), rd.spread(arm, sb, b), FLOOR)
            st = status(va - vb, s, rd.in_band(arm, a) and rd.in_band(arm, b))
            if arm == "BASE":
                base_ok = st == "Held"
            rows.append({"no": no, "group": grp, "arm": arm, "above": f"{sa} {a[0]} {a[1]}", "below": f"{sb} {b[0]} {b[1]}", "above_value": round(va, 3), "below_value": round(vb, 3), "gap": round(va - vb, 3), "s": round(s, 3), "two_s": round(2 * s, 3), "status": st, "read": base_ok})
    for arm in ARMS:
        v = rd.val(arm, "IC5", ("M1a_out", SQ))
        rows.append({"no": 24, "group": "F", "arm": arm, "above": "100 days", "below": "IC5 M1a_out ARL0", "above_value": 100.0, "below_value": round(v, 1), "gap": round(100 - v, 1), "s": float("nan"), "two_s": float("nan"), "status": "Held" if v < 100 else "Flipped", "read": True})
    return pd.DataFrame(rows)


def findings(o: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for grp, g in o.groupby("group"):
        read = g[g.read.astype(bool)]
        flipped = read[read.status == "Flipped"]
        all_held = (g.status == "Held").all()
        verdict = "changed" if len(flipped) else ("held" if all_held else "cannot say")
        rows.append({"finding": grp, "verdict": verdict, "orderings": g.no.nunique(), "cells": len(g), "held": int((g.status == "Held").sum()), "flipped": int((g.status == "Flipped").sum()), "not_separated": int((g.status == "Not separated").sum()), "cannot_say": int((g.status == "Cannot say").sum()), "flips": "; ".join(f"{r.no} {r.arm}" for r in flipped.itertuples())})
    return pd.DataFrame(rows)


def c7_overall(o: pd.DataFrame, rd: Reader) -> pd.DataFrame:
    rows = []
    for arm in ARMS:
        g = o[o.arm == arm].set_index("no")
        band = rd.in_band(arm, C7) and rd.in_band(arm, M4S)
        better = bool(g.loc[20, "status"] == "Held" and g.loc[21, "status"] == "Held" and g.loc[22, "gap"] <= g.loc[22, "two_s"])
        rows.append({"arm": arm, "s2": g.loc[20, "status"], "sev": g.loc[21, "status"], "rep_gap": g.loc[22, "gap"], "rep_two_s": g.loc[22, "two_s"], "better_overall": "cannot say" if not band else better})
    return pd.DataFrame(rows)


def sizes(rd: Reader, main_runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    charts = main_runs[main_runs.limits == "recalibrated"][["method", "weights"]].drop_duplicates().itertuples(index=False)
    charts = [tuple(c) for c in charts]
    for arm, spec in ARMS.items():
        if arm == "BASE":
            continue
        ref = spec.mix if spec.weekday else "BASE"
        for sid in SCENARIOS[1:]:
            for c in charts:
                d = rd.val(arm, sid, c) - rd.val(ref, sid, c)
                s = max(rd.spread(arm, sid, c), rd.spread(ref, sid, c), FLOOR)
                if abs(d) > 0.05 and abs(d) > 2 * s:
                    rows.append({"arm": arm, "against": ref, "scenario": sid, "method": c[0], "weights": c[1], "value": round(rd.val(arm, sid, c), 3), "reference": round(rd.val(ref, sid, c), 3), "change": round(d, 3), "two_s": round(2 * s, 3)})
    return pd.DataFrame(rows)


def seed_parity(sd: pd.DataFrame) -> pd.DataFrame:
    """BASE at the 10 seeds against the earlier spread runs: same seeds and size, so the means must agree."""
    b = sd[sd.arm == "BASE"]
    rows = []
    for path, methods in ((HERE.parent / "larger_run/seed_spread.csv", {"M2": SQ, "M4": SQ, "M5": SQ, "M7": "none"}), (HERE.parent / "category_test/seed_spread.csv", {"C4": "none", "C5": "none"})):
        old = pd.read_csv(path)
        for r in old[old.method.isin(methods)].itertuples():
            new = b[(b.scenario == r.scenario) & (b.method == r.method) & (b.weights == methods[r.method])].seed_mean.iloc[0]
            rows.append({"scenario": r.scenario, "method": r.method, "old_mean": r.mean, "new_mean": round(new, 3), "differ": abs(new - r.mean) > 0.0011})
    return pd.DataFrame(rows)


def main() -> None:
    main_runs, sd = load(Path(sys.argv[1]), Path(sys.argv[2]))
    rd = Reader(main_runs, sd)
    sd.round(4).to_csv(HERE / "seed_spread.csv", index=False)
    keep = ["arm", "limits", "scenario", "weights", "method", "n", "arl0", "arl0_mcse", "fa365", "pre_tau_fa", "pod30", "pod30_mcse", "ced", "censored_share"]
    main_runs[keep].round(4).to_csv(HERE / "summary.csv", index=False)
    sp = seed_parity(sd)
    sp.to_csv(HERE / "seed_parity.csv", index=False)
    print("seed parity differ:", int(sp.differ.sum()), "of", len(sp))
    o = orderings(rd)
    o.to_csv(HERE / "orderings.csv", index=False)
    f = findings(o)
    f.to_csv(HERE / "findings.csv", index=False)
    c = c7_overall(o, rd)
    c.to_csv(HERE / "c7_overall.csv", index=False)
    z = sizes(rd, main_runs)
    z.to_csv(HERE / "size_changes.csv", index=False)
    print(f.to_string(index=False))
    print(c.to_string(index=False))
    print(o.pivot(index="no", columns="arm", values="status")[list(ARMS)].to_string())
    print("size changes:", len(z))


if __name__ == "__main__":
    main()
