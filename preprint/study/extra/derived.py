"""Numbers derived from the EXISTING result files (no new simulation). Post hoc, added 2 Nov 2026.

python -m study.extra.derived
Reads study/results/full (never changes it). Writes CSV and markdown to study/results/extra/.
Synthetic data only.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from study.sim import dgm
from study.sim.report import IC_IDS, LABEL, OOC_IDS, SCHEMES, md_table

FULL = Path("study/results/full")
OUT = Path("study/results/extra")
TAU, P1 = dgm.TAU, dgm.PHASE1_DAYS


def wilson(k: float, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def fmt(v: float, nd: int) -> str:
    return "n/a" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:,.{nd}f}"


def cell(v: float, se: float, nd: int, n_ev: float | None = None) -> str:
    """'value (MCSE)'. A cell resting on one event prints 'n/a (n=1)' instead of a false 0.0."""
    if n_ev is not None and n_ev == 1:
        return "n/a (n=1)"
    if v is None or math.isnan(v):
        return "n/a"
    return f"{fmt(v, nd)} ({fmt(se, nd)})" if not math.isnan(se) else fmt(v, nd)


def km(times: np.ndarray, event: np.ndarray) -> dict[str, float]:
    """Kaplan-Meier with Greenwood SE. Quantile times (10, 50, 90 per cent of wards alarmed)."""
    order = np.argsort(times, kind="stable")
    t, e = times[order], event[order].astype(bool)
    ut = np.unique(t[e])
    if ut.size == 0:
        return {"km_q10": np.nan, "km_median": np.nan, "km_q90": np.nan, "km_median_lo": np.nan, "km_median_hi": np.nan, "share_no_alarm": 1.0}
    n_i = np.array([(t >= u).sum() for u in ut], dtype=float)
    d_i = np.array([((t == u) & e).sum() for u in ut], dtype=float)
    s = np.cumprod(1 - d_i / n_i)
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.cumsum(d_i / (n_i * (n_i - d_i)))
    se = s * np.sqrt(g)

    def first(mask: np.ndarray) -> float:
        i = np.flatnonzero(mask)
        return float(ut[i[0]]) if i.size else float("nan")

    out = {"km_q10": first(s <= 0.9), "km_median": first(s <= 0.5), "km_q90": first(s <= 0.1)}
    out["km_median_lo"] = first(s - 1.96 * se <= 0.5)
    out["km_median_hi"] = first(s + 1.96 * se <= 0.5)
    out["share_no_alarm"] = float(1 - e.mean())
    return out


def _in_window(f: np.ndarray) -> np.ndarray:
    return ((f >= TAU) & (f <= TAU + 29)).astype(float)


def paired(fa: np.ndarray, fb: np.ndarray, label: str) -> dict:
    ua, ub = _in_window(fa), _in_window(fb)
    d = ua - ub
    both = ~(((fa > 0) & (fa < TAU)) | ((fb > 0) & (fb < TAU)))  # neither alarmed before the change
    dc = d[both]
    ea, eb = (fa == 0) | (fa >= TAU), (fb == 0) | (fb >= TAU)
    pa, pb = ua[ea].mean(), ub[eb].mean()
    sea, seb = math.sqrt(pa * (1 - pa) / ea.sum()), math.sqrt(pb * (1 - pb) / eb.sum())
    return {"comparison": label, "n": d.size, "diff_unconditional": d.mean(), "mcse_unconditional": d.std(ddof=1) / math.sqrt(d.size),
            "n_both_eligible": int(both.sum()), "diff_pod30_both_eligible": dc.mean(), "mcse_both_eligible": dc.std(ddof=1) / math.sqrt(dc.size),
            "published_pod30_diff": pa - pb, "unpaired_mcse_of_published_diff": math.hypot(sea, seb)}


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summ = pd.read_csv(FULL / "summary.csv")
    wsum = pd.read_csv(FULL / "weights_summary.csv")
    rep = pd.read_csv(FULL / "replicates.csv")
    wrep = pd.read_csv(FULL / "weights_replicates.csv")
    bsum = pd.read_csv(FULL / "bootstrap_sensitivity" / "summary.csv")
    brep = pd.read_csv(FULL / "bootstrap_sensitivity" / "replicates.csv")
    sq = summ[summ.weights == "squared"]

    # 1. censored share beside every CED (Table 2 scenarios)
    t = sq[sq.scenario.isin(OOC_IDS)].copy()
    t["n_detected"] = (t.n_eligible * (1 - t.censored_share)).round().astype("Int64")
    t["n_censored"] = (t.n_eligible - t.n_detected).astype("Int64")
    c1 = t[["scenario", "method", "n", "n_eligible", "n_detected", "n_censored", "ced", "ced_mcse", "censored_share"]]
    c1.to_csv(OUT / "c1_ced_with_censored_share.csv", index=False)

    # 2. unconditional detection (all replicates)
    rows = []
    for sid in ["S2", "S15", "R60", "SEV", "REP"]:
        for m in ["M2", "M4", "M5", "M7"]:
            f = rep[(rep.scenario == sid) & (rep.method == m) & (rep.weights == "squared")].first_alarm.to_numpy()
            n = f.size
            a = int(((f >= TAU) & (f <= TAU + 29)).sum())
            b = int((f > 0).sum())  # monitoring ends at day 485 for every out-of-control stream
            r = {"scenario": sid, "method": m, "n": n, "p_first_alarm_d181_210": a / n, "p_first_alarm_d181_210_mcse": math.sqrt(a / n * (1 - a / n) / n),
                 "p_any_alarm_by_485": b / n, "p_any_alarm_by_485_mcse": math.sqrt(b / n * (1 - b / n) / n)}
            r["p_first_alarm_d181_210_wilson_lo"], r["p_first_alarm_d181_210_wilson_hi"] = wilson(a, n)
            r["p_any_alarm_by_485_wilson_lo"], r["p_any_alarm_by_485_wilson_hi"] = wilson(b, n)
            rows.append(r)
    pd.DataFrame(rows).to_csv(OUT / "c2_unconditional_detection.csv", index=False)

    # 3. paired differences (same streams: common random numbers)
    s2 = rep[(rep.scenario == "S2") & (rep.weights == "squared")].pivot(index="rep", columns="method", values="first_alarm")
    pr = [paired(s2.M4.to_numpy(), s2.M5.to_numpy(), "S2 POD30: M4 minus M5"), paired(s2.M2.to_numpy(), s2.M4.to_numpy(), "S2 POD30: M2 minus M4")]
    w2 = wrep[(wrep.scenario == "S2") & (wrep.method == "M4")].pivot(index="rep", columns="weights", values="first_alarm")
    for sch in SCHEMES[1:]:
        pr.append(paired(w2["squared"].to_numpy(), w2[sch].to_numpy(), f"S2 POD30, EWMA: squared minus {sch}"))
    pd.DataFrame(pr).to_csv(OUT / "c3_paired_differences.csv", index=False)

    # 4. Kaplan-Meier time to first alarm in IC5 (days after day 120; censored at 1,095)
    rows = []
    for m in ["M1a_out", "M1a_any", "M1b_out", "M1b_any", "M2", "M4", "M5"]:
        f = rep[(rep.scenario == "IC5") & (rep.method == m) & (rep.weights == "squared")].first_alarm.to_numpy()
        ev = f > 0
        times = np.where(ev, f - P1, dgm.MONITOR_IC).astype(float)
        rows.append({"method": m, "n": f.size, **km(times, ev)})
    pd.DataFrame(rows).to_csv(OUT / "c4_km_ic5.csv", index=False)

    # 5. bootstrap calibration: what the files allow
    rows = []
    for label, r in (("oracle", rep[rep.weights == "squared"]), ("bootstrap", brep[brep.weights == "squared"])):
        for m in ["M2", "M3", "M4", "M5", "M7"]:
            f = r[(r.scenario == "IC5") & (r.method == m)].first_alarm.to_numpy()
            ev = f > 0
            tt = np.where(ev, f - P1, dgm.MONITOR_IC).astype(float)
            rows.append({"calibration": label, "method": m, "n_wards": f.size, **km(tt, ev),
                         "share_no_alarm_1095d": 1 - ev.mean(), "arl0_est": tt.sum() / ev.sum() if ev.any() else np.nan})
    c5 = pd.DataFrame(rows)
    c5["note"] = "per-ward thresholds are not stored in the files, so the per-ward implied ARL0 cannot be computed; run-length spread is the available proxy"
    c5.to_csv(OUT / "c5_bootstrap_ic5_spread.csv", index=False)
    s1 = pd.read_csv(FULL / "tables" / "tableS1_calibration_sensitivity.csv")
    nb = {s: int(g.n.iloc[0]) for s, g in bsum[bsum.method == "M2"].groupby("scenario")}
    no = {s: int(g.n.iloc[0]) for s, g in sq[sq.method == "M2"].groupby("scenario")}
    s1["fa365_mcse_oracle"] = [math.sqrt(p * (1 - p) / no[s]) for p, s in zip(s1.fa365_oracle, s1.scenario, strict=True)]
    s1["fa365_mcse_bootstrap"] = [math.sqrt(p * (1 - p) / nb[s]) for p, s in zip(s1.fa365_bootstrap, s1.scenario, strict=True)]
    s1.to_csv(OUT / "c5_tableS1_with_mcse.csv", index=False)

    # 6. label table for the released method (normal labels vs observed)
    rows = []
    for k, m in ((2, "M1a_out"), (3, "M1b_out")):
        one = 0.5 * math.erfc(k / math.sqrt(2))
        for sid in IC_IDS:
            g = sq[(sq.scenario == sid) & (sq.method == m)].iloc[0]
            rate = g.alarm_days_per_year / 365
            rows.append({"k": k, "scenario": sid, "label_daily_rate_one_sided": one, "label_arl0_one_sided": 1 / one,
                         "label_daily_rate_two_sided": 2 * one, "label_arl0_two_sided": 1 / (2 * one),
                         "observed_alarm_days_per_year": g.alarm_days_per_year, "observed_alarm_days_per_year_mcse": g.alarm_days_per_year_mcse,
                         "observed_daily_rate": rate, "observed_arl0": g.arl0, "observed_arl0_mcse": g.arl0_mcse,
                         "observed_rate_over_one_sided_label": rate / one, "endpoint_revision": g.endpoint_revision,
                         "endpoint_revision_mcse": g.endpoint_revision_mcse})
    pd.DataFrame(rows).to_csv(OUT / "c6_label_table.csv", index=False)

    # 7. reprinted tables
    md = ["# Reprinted tables (derived from the existing result files; post hoc)", "",
          "ARL0 and MCSE to 1 decimal. A cell resting on one event prints n/a (n=1). Proportions whose MCSE prints 0.000 show a Wilson 95% interval.", ""]
    t1 = sq[sq.scenario.isin(IC_IDS)]
    rws = []
    for m in LABEL:
        if m in set(t1.method):
            r = {"method": LABEL[m]}
            for sid in IC_IDS:
                g = t1[(t1.scenario == sid) & (t1.method == m)]
                r[sid] = cell(g.arl0.iloc[0], g.arl0_mcse.iloc[0], 1) if len(g) else "n/a"
            rws.append(r)
    md += ["## Table 1A. In-control ARL0 in days, estimate (MCSE)", "", md_table(pd.DataFrame(rws)), ""]
    rws = []
    for m in LABEL:
        if m in set(t1.method):
            r = {"method": LABEL[m]}
            for sid in IC_IDS:
                g = t1[(t1.scenario == sid) & (t1.method == m)].iloc[0]
                if g.fa365_mcse >= 0.0005:
                    r[sid] = f"{g.fa365:.3f} ({g.fa365_mcse:.3f})"
                else:
                    lo, hi = wilson(g.fa365 * g.n, int(g.n))
                    r[sid] = f"{g.fa365:.3f} (Wilson {lo:.3f}-{hi:.3f})"
            rws.append(r)
    md += ["## Table 1C. FA365: P(at least one alarm in 365 days)", "", md_table(pd.DataFrame(rws)), ""]
    rws = []
    for m in ["M1a_out", "M1a_any", "M2", "M4", "M5"]:
        r = {"method": LABEL[m]}
        for sch in SCHEMES:
            g = wsum[(wsum.scenario == "IC5") & (wsum.method == m) & (wsum.weights == sch)]
            r[sch] = cell(g.arl0.iloc[0], g.arl0_mcse.iloc[0], 1) if len(g) else "n/a"
        rws.append(r)
    md += ["## Table 3A. IC5 ARL0 in days by weight scheme, estimate (MCSE)", "", md_table(pd.DataFrame(rws)), ""]
    rws = []
    for m in LABEL:
        if m in set(c1.method):
            r = {"method": LABEL[m]}
            for sid in OOC_IDS:
                g = c1[(c1.scenario == sid) & (c1.method == m)]
                if len(g):
                    r[sid] = cell(g.ced.iloc[0], g.ced_mcse.iloc[0], 1, None if pd.isna(g.n_detected.iloc[0]) else int(g.n_detected.iloc[0])) + f" [cens {g.censored_share.iloc[0]:.2f}]"
                else:
                    r[sid] = "n/a"
            rws.append(r)
    md += ["## Table 2A. CED in days, estimate (MCSE) [cens = share of eligible replicates with no alarm]", "", md_table(pd.DataFrame(rws)), ""]
    rws = []
    for m in LABEL:
        if m in set(t.method):
            r = {"method": LABEL[m]}
            for sid in OOC_IDS:
                g = t[(t.scenario == sid) & (t.method == m)]
                r[sid] = cell(g.pod30.iloc[0], g.pod30_mcse.iloc[0], 2, 1 if g.n_eligible.iloc[0] == 1 else None) if len(g) else "n/a"
            rws.append(r)
    md += ["## Table 2B. POD30, estimate (MCSE), among replicates with no alarm before the change", "", md_table(pd.DataFrame(rws)), ""]
    rws = []
    for m in ["M1a_out", "M1a_any", "M2", "M4", "M5"]:
        r = {"method": LABEL[m]}
        for sch in SCHEMES:
            g = wsum[(wsum.scenario == "S2") & (wsum.method == m) & (wsum.weights == sch)]
            if len(g):
                r[sch] = cell(g.ced.iloc[0], g.ced_mcse.iloc[0], 1, round(g.n_eligible.iloc[0] * (1 - g.censored_share.iloc[0])))
        rws.append(r)
    md += ["## Table 3B. S2 CED in days by weight scheme, estimate (MCSE)", "", md_table(pd.DataFrame(rws)), ""]
    rws = []
    for m in ["M2", "M3", "M4", "M5", "M7"]:
        r = {"method": LABEL[m]}
        for sid in IC_IDS:
            g = s1[(s1.scenario == sid) & (s1.method == m)]
            r[sid] = (f"{g.arl0_oracle.iloc[0]:.1f} ({g.arl0_mcse_oracle.iloc[0]:.1f}) / "
                      f"{g.arl0_bootstrap.iloc[0]:.1f} ({g.arl0_mcse_bootstrap.iloc[0]:.1f})") if len(g) else "n/a"
        rws.append(r)
    md += ["## Table S1. ARL0 (days), oracle (MCSE) / bootstrap (MCSE)", "", md_table(pd.DataFrame(rws)), ""]
    (OUT / "c7_tables_reprinted.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
