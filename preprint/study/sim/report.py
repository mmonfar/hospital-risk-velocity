"""Tables (CSV + markdown) and figures (PNG) from a results folder (protocol P.4).

python -m study.sim.report --results study/results/full [--sensitivity study/results/full/bootstrap_sensitivity]

Reads summary.csv and weights_summary.csv (written by run.py). Writes into <results>/tables and
<results>/figures. Figures are drawn with Pillow (matplotlib is not installed in the study venv).
Synthetic data only.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from study.sim import charts, dgm, shipped

LABEL = {
    "M1a_out": "M1a as shipped k=2, OUTSIDE",
    "M1a_any": "M1a as shipped k=2, any alert",
    "M1b_out": "M1b as shipped k=3, OUTSIDE",
    "M1b_any": "M1b as shipped k=3, any alert",
    "M2": "M2 revised (quantile)",
    "M3": "M3 Shewhart XmR",
    "M4": "M4 EWMA",
    "M5": "M5 CUSUM",
    "M6": "M6 g-chart",
    "M7": "M7 count chart",
}
IC_IDS = [f"IC{i}" for i in range(1, 10)]
OOC_IDS = ["S15", "S2", "S2-small", "S2-large", "S2-theta1", "S2-Pois", "R60", "SEV", "REP"]
SCHEMES = ["squared", "linear", "exponential", "harm_only"]
# Okabe-Ito colour-blind-safe palette
COLOURS = {
    "M1a_out": "#D55E00",
    "M1a_any": "#E69F00",
    "M1b_out": "#CC79A7",
    "M2": "#0072B2",
    "M3": "#56B4E9",
    "M4": "#009E73",
    "M5": "#F0E442",
    "M7": "#000000",
    "M6": "#7F7F7F",
    "M1b_any": "#999999",
}


def _fmt(v: float, nd: int = 1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    return f"{v:,.{nd}f}"


def _with_mcse(v: float, se: float, nd: int = 1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    return f"{_fmt(v, nd)} ({_fmt(se, nd)})" if not math.isnan(se) else _fmt(v, nd)


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def _methods(df: pd.DataFrame) -> list[str]:
    return [m for m in LABEL if m in set(df["method"])]


# ---- tables -----------------------------------------------------------------------------------


def table1(summary: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    t = summary[summary["scenario"].isin(IC_IDS) & (summary["weights"] == "squared")].copy()
    keep = ["scenario", "method", "n", "arl0", "arl0_mcse", "km_median", "fa365", "fa365_mcse",
            "alarm_days_per_year", "alarm_days_per_year_mcse", "episodes_per_year", "episodes_per_year_mcse", "censored_share"]
    long = t[keep].copy()
    md = ["## Table 1. In control (IC1-IC9)", ""]
    for title, col, se, nd in [
        ("ARL0 in days, estimate (MCSE); target 365 for M2-M7", "arl0", "arl0_mcse", 0),
        ("False alarms per ward-year (alarm episodes), estimate (MCSE)", "episodes_per_year", "episodes_per_year_mcse", 2),
        ("FA365: P(at least one alarm in 365 days)", "fa365", "fa365_mcse", 3),
        ("Alarm-days per ward-year", "alarm_days_per_year", "alarm_days_per_year_mcse", 1),
    ]:
        rows = []
        for m in _methods(t):
            row = {"method": LABEL[m]}
            for sid in IC_IDS:
                g = t[(t.scenario == sid) & (t.method == m)]
                row[sid] = _with_mcse(g[col].iloc[0], g[se].iloc[0], nd) if len(g) else "n/a"
            rows.append(row)
        md += [f"**{title}**", "", md_table(pd.DataFrame(rows)), ""]
    md.append("Scenarios: IC1-IC3 mu0=0.5 (theta 1, 2, Poisson); IC4-IC6 mu0=2; IC7-IC9 mu0=8. IC5 is the core scenario (mu0=2, theta=2).")
    return long, "\n".join(md)


def table2(summary: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    t = summary[summary["scenario"].isin(OOC_IDS) & (summary["weights"] == "squared")].copy()
    keep = ["scenario", "method", "n", "pre_tau_fa", "pre_tau_fa_mcse", "n_eligible", "ced", "ced_mcse",
            "pod14", "pod14_mcse", "pod30", "pod30_mcse", "censored_share"]
    long = t[keep].copy()
    md = ["## Table 2. Out of control", ""]
    for title, col, se, nd, ids in [
        ("CED in days after the change, estimate (MCSE), among replicates with no alarm before the change", "ced", "ced_mcse", 1, OOC_IDS[:-1]),
        ("POD30: P(first alarm within 30 days of the change), estimate (MCSE)", "pod30", "pod30_mcse", 2, OOC_IDS[:-1]),
        ("POD14: P(first alarm within 14 days of the change)", "pod14", "pod14_mcse", 2, OOC_IDS[:-1]),
        ("Pre-change false alarm: P(alarm before the change), estimate (MCSE)", "pre_tau_fa", "pre_tau_fa_mcse", 2, OOC_IDS[:-1]),
        ("REP (reporting rises, harm constant): every alarm is a false signal about harm. Lower is better", None, None, 2, ["REP"]),
    ]:
        rows = []
        for m in _methods(t):
            row = {"method": LABEL[m]}
            if col is None:
                g = t[(t.scenario == "REP") & (t.method == m)]
                if len(g):
                    row["POD30"] = _with_mcse(g["pod30"].iloc[0], g["pod30_mcse"].iloc[0], 2)
                    row["POD14"] = _with_mcse(g["pod14"].iloc[0], g["pod14_mcse"].iloc[0], 2)
                    row["pre-change alarm"] = _with_mcse(g["pre_tau_fa"].iloc[0], g["pre_tau_fa_mcse"].iloc[0], 2)
                    row["CED"] = _with_mcse(g["ced"].iloc[0], g["ced_mcse"].iloc[0], 1)
            else:
                for sid in ids:
                    g = t[(t.scenario == sid) & (t.method == m)]
                    row[sid] = _with_mcse(g[col].iloc[0], g[se].iloc[0], nd) if len(g) else "n/a"
            rows.append(row)
        md += [f"**{title}**", "", md_table(pd.DataFrame(rows)), ""]
    md.append("The M1a/M1b rows alarm before the change in most replicates, so their CED and POD are measured on a small, selected group (see n_eligible in the CSV). Read them with the pre-change row.")
    return long, "\n".join(md)


def table3(wsum: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    keep = [c for c in ["scenario", "weights", "method", "n", "arl0", "arl0_mcse", "pod30", "pod30_mcse", "ced", "ced_mcse",
                        "pre_tau_fa", "episodes_per_year"] if c in wsum.columns]
    long = wsum[keep].copy()
    md = ["## Table 3. Weight schemes", ""]
    for title, sid, col, se, nd in [
        ("IC5 ARL0 in days, estimate (MCSE)", "IC5", "arl0", "arl0_mcse", 0),
        ("S2 POD30", "S2", "pod30", "pod30_mcse", 2),
        ("S2 CED in days", "S2", "ced", "ced_mcse", 1),
        ("SEV POD30 (severity shift, constant volume)", "SEV", "pod30", "pod30_mcse", 2),
        ("REP POD30 (false signal about harm)", "REP", "pod30", "pod30_mcse", 2),
    ]:
        rows = []
        for m in _methods(wsum):
            for sch in SCHEMES:
                g = wsum[(wsum.scenario == sid) & (wsum.method == m) & (wsum.weights == sch)]
                if len(g):
                    rows.append((m, sch, _with_mcse(g[col].iloc[0], g[se].iloc[0], nd)))
        piv = pd.DataFrame(rows, columns=["m", "s", "v"]).pivot(index="m", columns="s", values="v")
        piv = piv.reindex(index=[m for m in LABEL if m in piv.index], columns=SCHEMES)
        piv.insert(0, "method", [LABEL[m] for m in piv.index])
        md += [f"**{title}**", "", md_table(piv.reset_index(drop=True)), ""]
    md.append("Schemes: squared (shipped, 1..81), linear (1..9), exponential (2^(i-1)), harm_only (0 for A-D, squared for E-I).")
    return long, "\n".join(md)


def sensitivity_table(primary: pd.DataFrame, boot: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """IC ARL0 under oracle (primary) and bootstrap calibration, M2-M7."""
    a = primary[primary.scenario.isin(IC_IDS) & (primary.weights == "squared") & primary.method.isin(["M2", "M3", "M4", "M5", "M7"])]
    b = boot[boot.scenario.isin(IC_IDS) & (boot.weights == "squared") & boot.method.isin(["M2", "M3", "M4", "M5", "M7"])]
    m = a[["scenario", "method", "arl0", "arl0_mcse", "fa365"]].merge(
        b[["scenario", "method", "arl0", "arl0_mcse", "fa365"]], on=["scenario", "method"], suffixes=("_oracle", "_bootstrap"))
    rows = []
    for meth in ("M2", "M3", "M4", "M5", "M7"):
        row = {"method": LABEL[meth]}
        for sid in IC_IDS:
            g = m[(m.scenario == sid) & (m.method == meth)]
            if len(g):
                row[sid] = f"{_fmt(g.arl0_oracle.iloc[0], 0)} / {_fmt(g.arl0_bootstrap.iloc[0], 0)}"
        rows.append(row)
    md = ["## Table S1. Calibration sensitivity: ARL0 (days), oracle / bootstrap", "", md_table(pd.DataFrame(rows))]
    return m, "\n".join(md)


# ---- figures (Pillow) -------------------------------------------------------------------------


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # old Pillow
        return ImageFont.load_default()


class Canvas:
    def __init__(self, w: int = 1400, h: int = 800, left: int = 90, right: int = 330, top: int = 70, bottom: int = 110) -> None:
        self.w, self.h, self.l, self.r, self.t, self.b = w, h, left, right, top, bottom
        self.im = Image.new("RGB", (w, h), "white")
        self.d = ImageDraw.Draw(self.im)
        self.f = _font(16)
        self.fs = _font(13)
        self.fb = _font(20)

    def px(self, x: float) -> float:  # x in 0..1
        return self.l + x * (self.w - self.l - self.r)

    def py(self, y: float) -> float:  # y in 0..1 (0 bottom)
        return self.h - self.b - y * (self.h - self.t - self.b)

    def frame(self, title: str, ylabel: str) -> None:
        self.d.text((self.l, 20), title, fill="black", font=self.fb)
        self.d.line([(self.l, self.py(0)), (self.px(1), self.py(0))], fill="#444", width=2)
        self.d.line([(self.l, self.py(0)), (self.l, self.py(1))], fill="#444", width=2)
        self.d.text((8, self.t - 30), ylabel, fill="#222", font=self.f)

    def legend(self, items: list[tuple[str, str]]) -> None:
        x0, y0 = self.w - self.r + 25, self.t
        for i, (name, col) in enumerate(items):
            y = y0 + i * 26
            self.d.ellipse([x0, y, x0 + 12, y + 12], fill=col, outline="#333")
            self.d.text((x0 + 20, y - 3), name, fill="#222", font=self.fs)

    def save(self, path: Path) -> None:
        self.im.save(path, format="PNG")


def figure1(summary: pd.DataFrame, path: Path) -> None:
    """ARL0 by method across IC1-IC9 (log scale), reference 365."""
    t = summary[summary.scenario.isin(IC_IDS) & (summary.weights == "squared")]
    ms = [m for m in _methods(t) if m != "M1b_any"]
    lo, hi = 0.7, 4.0  # log10 days
    c = Canvas()
    c.frame("Figure 1. In-control ARL0 by method (synthetic, log scale; dashed line = target 365 days)", "ARL0 (days)")
    ly = lambda v: c.py((math.log10(max(v, 1e-9)) - lo) / (hi - lo))  # noqa: E731
    for e in range(1, 5):
        for k in (1, 2, 5):
            v = k * 10 ** (e - 1)
            if 10**lo <= v <= 10**hi:
                c.d.line([(c.l, ly(v)), (c.px(1), ly(v))], fill="#eee")
                if k == 1 or v in (20, 50, 200, 500, 2000, 5000):
                    c.d.text((c.l - 55, ly(v) - 8), f"{v:,}", fill="#444", font=c.fs)
    y365 = ly(365)
    for x in range(int(c.l), int(c.px(1)), 14):
        c.d.line([(x, y365), (x + 7, y365)], fill="#b00020", width=2)
    n = len(IC_IDS)
    for i, sid in enumerate(IC_IDS):
        cx = c.px((i + 0.5) / n)
        sc = dgm.BY_ID[sid]
        th = "inf" if np.isinf(sc.theta) else f"{sc.theta:g}"
        c.d.text((cx - 28, c.py(0) + 8), sid, fill="black", font=c.f)
        c.d.text((cx - 38, c.py(0) + 30), f"mu0={sc.mu0:g}", fill="#444", font=c.fs)
        c.d.text((cx - 38, c.py(0) + 46), f"theta={th}", fill="#444", font=c.fs)
        for j, m in enumerate(ms):
            g = t[(t.scenario == sid) & (t.method == m)]
            if not len(g) or math.isnan(g.arl0.iloc[0]):
                continue
            x = cx + (j - (len(ms) - 1) / 2) * 11
            v, se = g.arl0.iloc[0], g.arl0_mcse.iloc[0]
            if not math.isnan(se):
                c.d.line([(x, ly(max(v - 1.96 * se, 1e-9 + 10**lo))), (x, ly(v + 1.96 * se))], fill=COLOURS[m], width=2)
            c.d.ellipse([x - 4, ly(v) - 4, x + 4, ly(v) + 4], fill=COLOURS[m], outline="#333")
    c.legend([(LABEL[m], COLOURS[m]) for m in ms])
    c.save(path)


def figure2(summary: pd.DataFrame, path: Path) -> None:
    """POD30 by method and scenario with 95% MCSE bars."""
    t = summary[summary.scenario.isin(OOC_IDS) & (summary.weights == "squared")]
    ms = [m for m in _methods(t) if m != "M1b_any"]
    c = Canvas()
    c.frame("Figure 2. POD30 by method and scenario (bars = 1.96 x MCSE). REP: high = false signal about harm", "POD30")
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        c.d.line([(c.l, c.py(v)), (c.px(1), c.py(v))], fill="#eee")
        c.d.text((c.l - 40, c.py(v) - 8), f"{v:.2f}", fill="#444", font=c.fs)
    n = len(OOC_IDS)
    for i, sid in enumerate(OOC_IDS):
        cx = c.px((i + 0.5) / n)
        c.d.text((cx - 30, c.py(0) + 8), sid, fill="black", font=c.f)
        for j, m in enumerate(ms):
            g = t[(t.scenario == sid) & (t.method == m)]
            if not len(g) or math.isnan(g.pod30.iloc[0]):
                continue
            x = cx + (j - (len(ms) - 1) / 2) * 11
            v, se = g.pod30.iloc[0], g.pod30_mcse.iloc[0]
            c.d.line([(x, c.py(max(0, v - 1.96 * se))), (x, c.py(min(1, v + 1.96 * se)))], fill=COLOURS[m], width=2)
            c.d.ellipse([x - 4, c.py(v) - 4, x + 4, c.py(v) + 4], fill=COLOURS[m], outline="#333")
    c.legend([(LABEL[m], COLOURS[m]) for m in ms])
    c.save(path)


def stream_alarms(sid: str = "S2", seed: int = dgm.ROOT_SEED, rep: int = 7) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """One synthetic stream and each method's alarm days over the monitoring period (oracle calibration)."""
    sc = dgm.BY_ID[sid]
    w = dgm.WEIGHT_SCHEMES["squared"]
    idx = dgm.SCENARIO_INDEX[sid]
    drng, _ = dgm.scenario_rngs(seed, idx, rep)
    counts = dgm.simulate_stream(sc, drng)
    p1 = dgm.PHASE1_DAYS
    x, n = counts @ w, counts.sum(axis=1)
    fit = charts.true_fit(sc, w)
    orng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(idx, 10**9)))
    which = tuple(m for m in charts.CHARTS if m != "M6")
    th = charts.thresholds(fit, w, orng, which, reps=300)
    al = charts.alarms(th, fit, x[p1:], n[p1:], counts[p1:, 4:].sum(axis=1))
    st = shipped.status(x, n, (2.0,))[2.0][p1:]
    al["M1a_any"] = st >= shipped.MARGINAL
    al["M1a_out"] = st == shipped.OUTSIDE
    return x[p1:], al


def figure3(path: Path) -> None:
    x, al = stream_alarms()
    order = ["M1a_any", "M1a_out", "M2", "M4", "M5", "M7"]
    c = Canvas(h=760)
    c.frame("Figure 3. One synthetic S2 stream (rate doubles at the dashed line); ticks = alarm days", "daily score")
    days = len(x)
    xmax = max(float(x.max()), 1.0)
    top_h = 0.45
    xs = lambda d: c.px(d / days)  # noqa: E731
    pts = [(xs(i), c.py(0.55 + top_h * min(v / xmax, 1.0))) for i, v in enumerate(x)]
    c.d.line(pts, fill="#0072B2", width=1)
    tau_x = xs(dgm.TAU - dgm.PHASE1_DAYS - 1)
    for yy in range(int(c.py(1)), int(c.py(0)), 12):
        c.d.line([(tau_x, yy), (tau_x, yy + 6)], fill="#b00020", width=2)
    c.d.text((tau_x + 6, c.py(1) - 2), "change", fill="#b00020", font=c.fs)
    for k, m in enumerate(order):
        yy = c.py(0.46 - k * 0.075)
        c.d.text((c.l + 4, yy - 22), LABEL[m], fill="#222", font=c.fs)
        c.d.line([(c.l, yy), (c.px(1), yy)], fill="#eee")
        for d in np.flatnonzero(al[m]):
            c.d.line([(xs(d), yy - 8), (xs(d), yy + 8)], fill=COLOURS[m], width=2)
    c.d.text((c.px(0), c.py(0) + 8), "monitoring day 1", fill="#444", font=c.fs)
    c.d.text((c.px(1) - 110, c.py(0) + 8), f"day {days}", fill="#444", font=c.fs)
    c.save(path)


# ---- driver -----------------------------------------------------------------------------------


def build(results: Path, sensitivity: Path | None = None) -> list[Path]:
    tdir, fdir = results / "tables", results / "figures"
    tdir.mkdir(exist_ok=True)
    fdir.mkdir(exist_ok=True)
    made: list[Path] = []
    summary = pd.read_csv(results / "summary.csv")
    md: list[str] = []
    for name, (long, text) in {"table1_in_control": table1(summary), "table2_out_of_control": table2(summary)}.items():
        long.to_csv(tdir / f"{name}.csv", index=False)
        md.append(text)
        made.append(tdir / f"{name}.csv")
    wpath = results / "weights_summary.csv"
    if wpath.exists():
        long, text = table3(pd.read_csv(wpath))
        long.to_csv(tdir / "table3_weights.csv", index=False)
        md.append(text)
        made.append(tdir / "table3_weights.csv")
    if sensitivity is not None and (sensitivity / "summary.csv").exists():
        long, text = sensitivity_table(summary, pd.read_csv(sensitivity / "summary.csv"))
        long.to_csv(tdir / "tableS1_calibration_sensitivity.csv", index=False)
        md.append(text)
        made.append(tdir / "tableS1_calibration_sensitivity.csv")
    (tdir / "tables.md").write_text("\n\n".join(md) + "\n", encoding="utf-8")
    made.append(tdir / "tables.md")
    figure1(summary, fdir / "figure1_arl0.png")
    figure2(summary, fdir / "figure2_pod30.png")
    figure3(fdir / "figure3_stream.png")
    made += [fdir / "figure1_arl0.png", fdir / "figure2_pod30.png", fdir / "figure3_stream.png"]
    return made


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default="study/results/full")
    ap.add_argument("--sensitivity", default=None, help="folder with the bootstrap-calibration summary.csv")
    a = ap.parse_args(argv)
    for p in build(Path(a.results), Path(a.sensitivity) if a.sensitivity else None):
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
