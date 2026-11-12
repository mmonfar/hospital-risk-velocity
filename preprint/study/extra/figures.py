"""Redrawn figures 1-3 (post hoc, 2 Nov 2026): Pillow only, 300 dpi, 2,100 px wide, plain, colour-blind-safe palette.

python -m study.extra.figures
Reads study/results/full/summary.csv (values equal the tables). Writes PNGs to study/results/extra/figures/.
Text sizes are chosen so that the smallest text is about 8 pt when the 2,100 px image is printed 17 cm wide.
Synthetic data only.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from study.sim import dgm, shipped
from study.sim.report import IC_IDS, LABEL, OOC_IDS, stream_alarms

OUT = Path("study/results/extra/figures")
W_PX = 2100
F_TICK, F_LAB, F_LEG = 36, 40, 36

# (colour, marker). Okabe-Ito palette, distinct markers, dark outline on every filled marker.
STYLE = {
    "M1a_out": ("#D55E00", "tri_up"), "M1a_any": ("#E69F00", "tri_down"), "M1b_out": ("#CC79A7", "square"),
    "M1b_any": ("#777777", "diamond"), "M2": ("#0072B2", "circle"), "M3": ("#56B4E9", "plus"),
    "M4": ("#009E73", "cross"), "M5": ("#F0E442", "hex"), "M7": ("#000000", "pent"),
}
SERIES = list(STYLE)


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=size)  # type: ignore[return-value]


def marker(d: ImageDraw.ImageDraw, shape: str, x: float, y: float, col: str, r: float = 9) -> None:
    def poly(n: int, rot: float = -90, rr: float = r) -> list[tuple[float, float]]:
        return [(x + rr * math.cos(math.radians(rot + 360 * i / n)), y + rr * math.sin(math.radians(rot + 360 * i / n))) for i in range(n)]

    if shape == "circle":
        d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline="black", width=2)
    elif shape == "square":
        d.rectangle([x - r * 0.85, y - r * 0.85, x + r * 0.85, y + r * 0.85], fill=col, outline="black", width=2)
    elif shape == "diamond":
        d.polygon(poly(4, -90, r * 1.2), fill=col, outline="black")
    elif shape == "tri_up":
        d.polygon(poly(3, -90, r * 1.2), fill=col, outline="black")
    elif shape == "tri_down":
        d.polygon(poly(3, 90, r * 1.2), fill=col, outline="black")
    elif shape == "pent":
        d.polygon(poly(5, -90, r * 1.1), fill=col, outline="black")
    elif shape == "hex":
        d.polygon(poly(6, 0, r * 1.1), fill=col, outline="black")
    elif shape == "plus":
        d.line([(x - r, y), (x + r, y)], fill=col, width=5)
        d.line([(x, y - r), (x, y + r)], fill=col, width=5)
    elif shape == "cross":
        d.line([(x - r, y - r), (x + r, y + r)], fill=col, width=5)
        d.line([(x - r, y + r), (x + r, y - r)], fill=col, width=5)


class Fig:
    def __init__(self, h: int, left: int, right: int = 50, top: int = 40, bottom: int = 300) -> None:
        self.w, self.h, self.l, self.r, self.t, self.b = W_PX, h, left, right, top, bottom
        self.im = Image.new("RGB", (self.w, h), "white")
        self.d = ImageDraw.Draw(self.im)
        self.ft, self.fl = font(F_TICK), font(F_LAB)

    def px(self, u: float) -> float:
        return self.l + u * (self.w - self.l - self.r)

    def py(self, v: float) -> float:
        return self.h - self.b - v * (self.h - self.t - self.b)

    def text_r(self, x: float, y: float, s: str, f: ImageFont.FreeTypeFont, fill: str = "black") -> None:
        self.d.text((x - self.d.textlength(s, font=f), y), s, fill=fill, font=f, anchor="la")

    def text_c(self, x: float, y: float, s: str, f: ImageFont.FreeTypeFont, fill: str = "black") -> None:
        self.d.text((x - self.d.textlength(s, font=f) / 2, y), s, fill=fill, font=f, anchor="la")

    def ylabel(self, s: str) -> None:
        tmp = Image.new("RGBA", (int(self.d.textlength(s, font=self.fl)) + 10, F_LAB + 14), (255, 255, 255, 0))
        ImageDraw.Draw(tmp).text((5, 2), s, fill="black", font=self.fl)
        rot = tmp.rotate(90, expand=True)
        mid = (self.py(0) + self.py(1)) / 2
        self.im.paste(rot, (12, int(mid - rot.size[1] / 2)), rot)

    def axes(self) -> None:
        self.d.line([(self.l, self.py(0)), (self.px(1), self.py(0))], fill="black", width=3)
        self.d.line([(self.l, self.py(0)), (self.l, self.py(1))], fill="black", width=3)

    def legend(self, keys: list[str], y0: float, cols: int = 3) -> None:
        colw = (self.w - 80) / cols
        rows = math.ceil(len(keys) / cols)
        for i, k in enumerate(keys):
            c, r = i // rows, i % rows
            x, y = 40 + c * colw, y0 + r * (F_LEG + 22)
            marker(self.d, STYLE[k][1], x + 18, y + F_LEG / 2 + 4, STYLE[k][0])
            self.d.text((x + 50, y), LABEL[k], fill="black", font=self.ft)

    def save(self, name: str) -> Path:
        OUT.mkdir(parents=True, exist_ok=True)
        p = OUT / name
        self.im.save(p, format="PNG", dpi=(300, 300))
        return p


def _slots(f: Fig, labels: list[list[str]]) -> list[float]:
    n = len(labels)
    cxs = []
    for i, lab in enumerate(labels):
        cx = f.px((i + 0.5) / n)
        cxs.append(cx)
        for j, s in enumerate(lab):
            f.text_c(cx, f.py(0) + 14 + j * (F_TICK + 6), s, f.ft if j == 0 else font(30), "black" if j == 0 else "#333333")
        if i:
            f.d.line([(f.px(i / n), f.py(0)), (f.px(i / n), f.py(0) + 8)], fill="black", width=2)
    return cxs


def _plot_points(f: Fig, t: pd.DataFrame, ids: list[str], cxs: list[float], col: str, se: str, to_y) -> None:
    n = len(SERIES)
    step = 19
    for sid, cx in zip(ids, cxs, strict=True):
        for j, m in enumerate(SERIES):
            g = t[(t.scenario == sid) & (t.method == m)]
            if not len(g) or math.isnan(g[col].iloc[0]):
                continue
            x = cx + (j - (n - 1) / 2) * step
            v, e = g[col].iloc[0], g[se].iloc[0]
            c, shape = STYLE[m]
            if not math.isnan(e):
                y1, y2 = to_y(v - 1.96 * e, True), to_y(v + 1.96 * e, False)
                f.d.line([(x, y1), (x, y2)], fill="black", width=3)
                for yy in (y1, y2):
                    f.d.line([(x - 5, yy), (x + 5, yy)], fill="black", width=3)
            marker(f.d, shape, x, to_y(v, False), c)


def figure1(summary: pd.DataFrame) -> Path:
    t = summary[summary.scenario.isin(IC_IDS) & (summary.weights == "squared")]
    f = Fig(1700, left=250, bottom=520)
    lo, hi = 0.7, 3.2
    ly = lambda v, low=False: f.py((math.log10(max(v, 10**lo * 1.0001 if low else 1e-9)) - lo) / (hi - lo))  # noqa: E731
    for v in (10, 20, 50, 100, 200, 500, 1000):
        f.d.line([(f.l, ly(v)), (f.px(1), ly(v))], fill="#dddddd", width=2)
        f.text_r(f.l - 14, ly(v) - F_TICK / 2 - 2, f"{v:,}", f.ft)
    f.axes()
    y365 = ly(365)
    for x in range(int(f.l), int(f.px(1)), 30):
        f.d.line([(x, y365), (x + 16, y365)], fill="#b00020", width=4)
    f.text_r(f.px(1) - 10, f.py(1) + 6, "red dashed line = target ARL0 of 365 days (M2 to M7)", f.ft, "#b00020")
    labels = []
    for sid in IC_IDS:
        sc = dgm.BY_ID[sid]
        labels.append([sid, f"mean {sc.mu0:g}", "theta " + ("inf" if np.isinf(sc.theta) else f"{sc.theta:g}")])
    cxs = _slots(f, labels)
    _plot_points(f, t, IC_IDS, cxs, "arl0", "arl0_mcse", ly)
    f.ylabel("ARL0 in days (log scale)")
    f.legend(SERIES, f.py(0) + 14 + 3 * (F_TICK + 6) + 20)
    f.d.text((40, f.h - 2 * (F_LEG + 8)), "Points = estimates. Vertical bars = 95% intervals (1.96 x MCSE). In control: higher is better. Synthetic data.", fill="#222222", font=font(34))
    f.d.text((40, f.h - (F_LEG + 8)), "mean = expected reports per day; theta = overdispersion (inf = Poisson).", fill="#222222", font=font(34))
    return f.save("figure1_arl0.png")


def figure2(summary: pd.DataFrame) -> Path:
    t = summary[summary.scenario.isin(OOC_IDS) & (summary.weights == "squared")]
    f = Fig(1700, left=250, bottom=520)
    ly = lambda v, low=False: f.py(min(max(v, 0.0), 1.0))  # noqa: E731
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        f.d.line([(f.l, ly(v)), (f.px(1), ly(v))], fill="#dddddd", width=2)
        f.text_r(f.l - 14, ly(v) - F_TICK / 2 - 2, f"{v:.2f}", f.ft)
    n = len(OOC_IDS)
    f.d.rectangle([f.px((n - 1) / n), f.py(1), f.px(1), f.py(0)], fill="#f0f0f0")
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        f.d.line([(f.px((n - 1) / n), ly(v)), (f.px(1), ly(v))], fill="#dddddd", width=2)
    f.axes()
    labels = [[s] if s != "REP" else ["REP", "high = bad"] for s in OOC_IDS]
    labels = [[s.replace("-", "-")] for s in OOC_IDS]
    labels[-1] = ["REP", "high = bad"]
    cxs = _slots(f, labels)
    _plot_points(f, t, OOC_IDS, cxs, "pod30", "pod30_mcse", ly)
    f.ylabel("POD30 (proportion of wards)")
    f.legend(SERIES, f.py(0) + 14 + 2 * (F_TICK + 6) + 20)
    f.d.text((40, f.h - 2 * (F_LEG + 8)), "Points = estimates. Vertical bars = 95% intervals (1.96 x MCSE). POD30 = P(first alarm within 30 days of the change),", fill="#222222", font=font(34))
    f.d.text((40, f.h - (F_LEG + 8)), "among wards with no alarm before the change. REP (reporting rises, harm unchanged): every alarm is false. Synthetic data.", fill="#222222", font=font(34))
    return f.save("figure2_pod30.png")


def figure3() -> Path:
    x, al = stream_alarms()
    sc, p1, idx = dgm.BY_ID["S2"], dgm.PHASE1_DAYS, dgm.SCENARIO_INDEX["S2"]
    drng, _ = dgm.scenario_rngs(dgm.ROOT_SEED, idx, 7)
    counts = dgm.simulate_stream(sc, drng)
    st3 = shipped.status(counts @ dgm.WEIGHT_SCHEMES["squared"], counts.sum(axis=1), (3.0,))[3.0][p1:]
    al["M1b_out"], al["M1b_any"] = st3 == shipped.OUTSIDE, st3 >= shipped.MARGINAL
    rows = [("M1a k=2, OUTSIDE", "M1a_out"), ("M1a k=2, any alert", "M1a_any"), ("M1b k=3, OUTSIDE", "M1b_out"), ("M1b k=3, any alert", "M1b_any"),
            ("M2 quantile", "M2"), ("M4 EWMA", "M4"), ("M5 CUSUM", "M5"), ("M7 count chart", "M7")]
    f = Fig(1500, left=540, top=110, bottom=170)
    days = len(x)
    ymax = float(math.ceil(x.max() / 50) * 50)
    top_frac = 0.40
    xs = lambda d: f.px(d / days)  # noqa: E731
    base = 1 - top_frac
    yv = lambda v: f.py(base + 0.04 + (top_frac - 0.04) * v / ymax)  # noqa: E731
    step = 50 if ymax <= 250 else 100
    for v in range(0, int(ymax) + 1, step):
        f.d.line([(f.l, yv(v)), (f.px(1), yv(v))], fill="#dddddd", width=2)
        f.text_r(f.l - 14, yv(v) - F_TICK / 2 - 2, str(v), f.ft)
    f.d.line([(f.l, yv(0)), (f.l, f.py(0))], fill="black", width=3)
    f.d.line([(f.l, f.py(0)), (f.px(1), f.py(0))], fill="black", width=3)
    f.d.line([(xs(i), yv(v)) for i, v in enumerate(x)], fill="#0072B2", width=3)
    tx = xs(dgm.TAU - p1 - 1)
    for yy in range(int(f.py(1)), int(f.py(0)), 24):
        f.d.line([(tx, yy), (tx, yy + 12)], fill="#b00020", width=3)
    f.d.text((tx + 10, f.py(1) - 4), "change (rate doubles)", fill="#b00020", font=f.ft)
    f.d.text((20, 20), "Daily score (points per day; squared severity weights 1 to 81)", fill="black", font=f.ft)
    for k, (lab, m) in enumerate(rows):
        yy = f.py(base - 0.015 - (k + 0.5) * (base - 0.03) / len(rows))
        f.text_r(f.l - 14, yy - F_TICK / 2 - 2, lab, f.ft)
        f.d.line([(f.l, yy), (f.px(1), yy)], fill="#dddddd", width=2)
        for d in np.flatnonzero(al[m]):
            f.d.line([(xs(d), yy - 15), (xs(d), yy + 15)], fill=STYLE[m][0] if m in STYLE else STYLE["M1a_out"][0], width=3)
    for dday in range(0, days + 1, 60):
        f.d.line([(xs(dday), f.py(0)), (xs(dday), f.py(0) + 10)], fill="black", width=3)
        f.text_c(xs(dday), f.py(0) + 14, str(dday), f.ft)
    f.text_c((f.px(0) + f.px(1)) / 2, f.py(0) + 14 + F_TICK + 14, "Monitoring day (day 1 = day 121 of the stream)", f.fl)
    f.d.text((40, f.h - F_LEG - 20), "One synthetic stream (ward 7). Each tick = a day on which the method raised an alarm. Synthetic data.", fill="#222222", font=font(34))
    return f.save("figure3_stream.png")


def main() -> None:
    summary = pd.read_csv("study/results/full/summary.csv")
    for p in (figure1(summary), figure2(summary), figure3()):
        print(p)


if __name__ == "__main__":
    main()
