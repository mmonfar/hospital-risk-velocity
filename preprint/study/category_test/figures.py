"""Figures 4-6 of the paper, from saved results only; no new simulation. Okabe-Ito colours as figures 1-3.

Run from the repo root: py -3.11 study/category_test/figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.text as mtext
import pandas as pd

OUT = Path("paper/figures")
HERE = Path("study/category_test")
L = Path("study/larger_run")
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans"})
NOTE = "Synthetic data. Alarm within 30 days of the change, among wards with no earlier alarm."
BLUE, GREEN, ORANGE, BLACK, PINK, SKY = "#0072B2", "#009E73", "#D55E00", "#000000", "#CC79A7", "#56B4E9"


def check_text(fig, name: str) -> None:
    """Stop the build if any label, title, legend or note overlaps another or runs off the page."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    boxes = [t for t in fig.findobj(mtext.Text) if t.get_visible() and t.get_text().strip()]
    legends = [lg for ax in fig.axes if (lg := ax.get_legend())]
    inside = [t for lg in legends for t in lg.findobj(mtext.Text)]
    items = [(t.get_text(), mtext.Text.get_window_extent(t, r)) for t in boxes if t not in inside]
    items += [("legend", lg.get_window_extent(r)) for lg in legends]
    w, h = fig.canvas.get_width_height()
    for i, (a, ba) in enumerate(items):
        assert ba.x0 >= 0 and ba.y0 >= 0 and ba.x1 <= w and ba.y1 <= h, f"{name}: off the page: {a}"
        for b, bb in items[i + 1 :]:
            assert not ba.overlaps(bb), f"{name}: overlap: {a!r} and {b!r}"


def save(fig, name: str) -> None:
    check_text(fig, name)
    fig.savefig(OUT / name, dpi=300, facecolor="white")
    plt.close(fig)


def scatter(ax, pts, x, y, xlabel, ylabel) -> None:
    for label, v, colour, marker, dx, dy, ha in pts:
        ax.scatter(100 * v[x], 100 * v[y], s=80, color=colour, marker=marker, edgecolors="black", linewidths=0.6, zorder=3)
        arrow = dict(arrowstyle="-", color="#555555", linewidth=0.7) if abs(dy) > 12 else None
        ax.annotate(label, (100 * v[x], 100 * v[y]), xytext=(dx, dy), textcoords="offset points", fontsize=9.5, ha=ha, va="center", arrowprops=arrow)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.grid(color="#dddddd", linewidth=0.7)
    ax.set_axisbelow(True)


def values(df: pd.DataFrame, method: str, weights: str | None = None) -> dict[str, float]:
    g = df[df.method == method]
    if weights:
        g = g[g.weights == weights]
    return {sc: float(g[g.scenario == sc].pod30.iloc[0]) for sc in ("S2", "SEV", "REP")}


s = pd.read_csv(L / "summary.csv")
s = s[s.weights == "squared"]
w = pd.read_csv(L / "weights_summary.csv")
c = pd.read_csv(HERE / "summary.csv")
p = pd.read_csv(HERE / "summary_pairs.csv")

# ---- Figure 5: weights trade-off
fig, ax = plt.subplots(figsize=(7, 5.67))
schemes = [("squared", "Squared", BLUE, -8, 0, "right"), ("linear", "Linear", ORANGE, -8, 0, "right"), ("exponential", "Exponential", PINK, -8, 0, "right"), ("harm_only", "Harm-only", GREEN, 8, 0, "left")]
pts = [(f"{n}, EWMA", values(w, "M4", k), col, "o", dx, dy, ha) for k, n, col, dx, dy, ha in schemes]
pts += [(f"{n}, single-day", values(w, "M2", k), col, "s", 8, 0, "left") for k, n, col, _, _, _ in schemes]
scatter(ax, pts, "S2", "SEV", "All incidents double: wards with an alarm (%)", "More severe, same volume: wards with an alarm (%)")
ax.set_title("Weights trade one kind of detection for the other", loc="left", fontsize=12, fontweight="bold")
fig.text(0.02, 0.012, NOTE + " Larger run.", fontsize=8.5)
fig.tight_layout(rect=(0, 0.035, 1, 1))
save(fig, "figure5_weights.png")

# ---- Figure 6: score against counts
charts5 = [
    ("Squared score", values(w, "M4", "squared"), BLUE, "o"),
    ("Linear score", values(w, "M4", "linear"), ORANGE, "o"),
    ("Harm-only score", values(w, "M4", "harm_only"), GREEN, "o"),
    ("Total count", values(c, "C5"), BLACK, "D"),
    ("E-I count", values(c, "C4"), SKY, "D"),
    ("Two counts (total + E-I)", values(p, "C7"), PINK, "*"),
]
offset_a = [(-10, 0, "right"), (-10, 0, "right"), (-10, 0, "right"), (-10, 0, "right"), (10, 8, "left"), (-10, 0, "right")]
offset_b = [(-10, 0, "right"), (-24, 20, "right"), (-10, 0, "right"), (-10, 0, "right"), (10, 0, "left"), (-24, -20, "right")]
fig, axes = plt.subplots(2, 1, figsize=(7, 8.4))
scatter(axes[0], [(n, v, col, mk, *o) for (n, v, col, mk), o in zip(charts5, offset_a)], "S2", "SEV", "All incidents double: wards with an alarm (%)", "More severe, same volume (%)")
scatter(axes[1], [(n, v, col, mk, *o) for (n, v, col, mk), o in zip(charts5, offset_b)], "S2", "REP", "All incidents double: wards with an alarm (%)", "More no-harm reports only (%)")
axes[0].set_title("a  Top right is best", loc="left", fontsize=11, fontweight="bold")
axes[1].set_title("b  Bottom right is best: this false signal should stay low", loc="left", fontsize=11, fontweight="bold")
fig.text(0.02, 0.026, NOTE, fontsize=8.5)
fig.text(0.02, 0.008, "Smoothed (EWMA) charts, in-control run lengths 354-380 days.", fontsize=8.5)
fig.tight_layout(rect=(0, 0.05, 1, 1))
save(fig, "figure6_counts.png")

# ---- Figure 4: alarm types
e = pd.read_csv("study/results/extra/e2_detection.csv")
f = pd.read_csv("study/results/extra/f2_detection.csv")
d = pd.concat([e, f[f.method.isin(["SL14", "SL28"])]])
d = d[d.weights == "squared"]
methods = [("M4", "EWMA", GREEN, "o"), ("M5", "CUSUM", "#F0E442", "h"), ("SL28", "Slope, 28 days", BLUE, "s"), ("SL14", "Slope, 14 days", SKY, "s"), ("V", "Velocity", ORANGE, "^"), ("A", "Acceleration", PINK, "v"), ("J", "Jerk", "#777777", "D")]
scen = [("S15", "Rise 1.5 times"), ("S2", "Doubling"), ("R60", "60-day ramp"), ("SEV", "More severe"), ("REP", "More no-harm\nreports\n(high = bad)")]
fig, ax = plt.subplots(figsize=(7, 4.9))
for j, (m, label, col, mk) in enumerate(methods):
    xs, ys, es = [], [], []
    for i, (sc, _) in enumerate(scen):
        g = d[(d.method == m) & (d.scenario == sc)]
        xs.append(i + (j - 3) * 0.1)
        ys.append(100 * float(g.pod30.iloc[0]))
        es.append(100 * 1.96 * float(g.pod30_mcse.iloc[0]))
    ax.errorbar(xs, ys, yerr=es, fmt=mk, color=col, ecolor="black", elinewidth=0.8, capsize=2, markersize=6.5, markeredgecolor="black", markeredgewidth=0.5, linestyle="none", label=label)
ax.set_xticks(range(len(scen)), [b for _, b in scen])
ax.set_ylim(0, 100)
ax.set_ylabel("Wards with an alarm within 30 days (%)")
ax.grid(axis="y", color="#dddddd", linewidth=0.7)
ax.set_axisbelow(True)
ax.axvspan(3.5, 4.5, color="#f0f0f0", zorder=0)
ax.set_title("Alarms on speed or its changes detected less than EWMA and CUSUM", loc="left", fontsize=10.5, fontweight="bold")
ax.legend(ncol=4, fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.24))
fig.text(0.02, 0.012, "Synthetic data. Primary-run addenda, squared weights. Bars are 95% intervals (1.96 x MCSE).", fontsize=8)
fig.tight_layout(rect=(0, 0.04, 1, 1))
save(fig, "figure4_alarm_types.png")
