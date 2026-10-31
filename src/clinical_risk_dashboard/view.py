"""HTML parts of the page (design v2). Pure functions: engine values in, HTML text out.

No number is computed here beyond layout (pixel positions, shares of a total). Every
figure shown comes from ``risk_kinematics`` through ``presentation`` or the app.
"""

import base64
import math
from html import escape
from pathlib import Path
from typing import cast

import pandas as pd
from risk_kinematics import StrategicStatus, Tolerance

from clinical_risk_dashboard import presentation

_STATIC = Path(__file__).resolve().parent / "static"

_TONE = {  # status colour -> CSS tone letter
    presentation.RED: "r",
    presentation.AMBER: "w",
    presentation.TEAL: "t",
}


def stylesheet() -> str:
    """The one CSS file, with the local font embedded (no CDN, no network)."""
    font = (_STATIC / "fonts" / "PlusJakartaSans-Variable.woff2").read_bytes()
    css = (_STATIC / "style.css").read_text(encoding="utf-8")
    return css.replace("{{FONT_B64}}", base64.b64encode(font).decode("ascii"))


def tone(colour: str) -> str:
    return _TONE.get(colour, "n")


def sigma_text(z: float) -> str:
    return "n/a" if not math.isfinite(z) else f"{z:.2f}"


def logo_html() -> str:
    return (
        '<div class="rw"><div class="rw-logo">mmonfar<i>.</i><small>Risk early warning</small>'
        "</div></div>"
    )


def nav_views_html() -> str:
    return (
        '<div class="rw"><div class="rw-navh">Views</div>'
        '<div class="rw-navitem"><svg viewBox="0 0 16 16"><path d="M2 12l4-5 3 3 5-7"/></svg>'
        "Risk velocity</div></div>"
    )


def nav_units_title_html() -> str:
    return '<div class="rw"><div class="rw-navh">Units (sigma now)</div></div>'


def header_html(scope: str) -> str:
    return (
        '<div class="rw rw-head"><div class="rw-m rw-mobrand">mmonfar<i>.</i></div>'
        '<div class="rw-eyebrow">Clinical risk · Risk velocity</div>'
        f'<h1 class="rw-h1">{escape(scope)}</h1>'
        '<div class="rw-quiet">Synthetic data. Not a medical device.</div></div>'
    )


def _kpi(title: str, sub: str, body: str) -> str:
    return (
        f'<div class="rw-card rw-kpi"><div><div class="rw-t">{escape(title)}</div>'
        f'<div class="rw-st">{escape(sub)}</div></div><div>{body}</div></div>'
    )


def kpis_html(
    *,
    n_reports: int,
    period_days: int,
    status: StrategicStatus,
    sigma: float,
    view: presentation.StatusView,
    reason: str,
    momentum: presentation.MomentumLines,
) -> str:
    z = status.z_score
    no_data = status.tolerance is Tolerance.NO_DATA
    if no_data or not math.isfinite(z):
        delta = ""
    elif z > sigma:
        delta = f'<span class="rw-delta r">{z - sigma:.2f} σ over limit</span>'
    else:
        cls = "w" if status.tolerance is Tolerance.MARGINAL else "t"
        delta = f'<span class="rw-delta {cls}">{sigma - z:.2f} σ to limit</span>'
    unit_sigma = "n/a" if no_data else f"{sigma_text(z)} σ"
    cards = [
        _kpi(
            "Incident reports",
            f"Count in the last {period_days} days",
            f'<div class="rw-v">{n_reports:,}</div>',
        ),
        _kpi(
            "Variance vs baseline",
            f"Limit is {sigma:g} σ",
            f'<div class="rw-row2"><div class="rw-v">{unit_sigma}</div>{delta}</div>',
        ),
        _kpi(
            "Status",
            f"Decided by the {sigma:g} σ rule",
            f'<div class="rw-v s"><span class="rw-sdot" style="background:{view.colour}"></span>'
            f"{escape(view.label.capitalize())}"
            f'</div><div class="rw-why1">{escape(reason)}</div>',
        ),
        _kpi(
            "Momentum",
            "Latest day and trend",
            f'<div class="rw-v s2"><span class="rw-sdot" '
            f'style="background:{momentum.colour}"></span>'
            f"{escape(momentum.day)}<br>"
            f"{escape(momentum.trend)}</div>",
        ),
    ]
    return f'<div class="rw rw-kpis">{"".join(cards)}</div>'


def _nice_max(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        return 10.0
    step = 10 ** math.floor(math.log10(value))
    for m in (1, 2, 2.5, 5, 10):
        if m * step >= value:
            return m * step
    return 10 * step


def _date_ticks(dates: pd.Series, count: int) -> list[tuple[int, str]]:
    """First day, month starts in between, last day; thinned so labels never touch."""
    n = len(dates)
    marks = [(0, _short(dates.iloc[0]))]
    for i in range(1, n - 1):
        if dates.iloc[i].day == 1:
            marks.append((i, _short(dates.iloc[i])))
    marks.append((n - 1, _short(dates.iloc[-1])))
    min_gap = max(1, n // (count + 1))
    kept = [marks[0]]
    for m in marks[1:-1]:
        if m[0] - kept[-1][0] >= min_gap and (n - 1) - m[0] >= min_gap:
            kept.append(m)
    kept.append(marks[-1])
    return kept


def _short(ts: pd.Timestamp) -> str:
    return f"{ts.day} {ts:%b}"


def trend_svg(
    daily: pd.DataFrame,
    ucl: float,
    z: float,
    sigma: float,
    scope: str,
    *,
    w: int,
    h: int,
    fs: int,
    pad: tuple[int, int, int, int],
) -> str:
    """The hero chart: one trend line, dashed limit, amber watch zone above it, Now dot.

    Vector parts carry classes (zone, limit, trend) so the risk video can reuse them.
    """
    smooth = [float(v) for v in daily["smooth"]]
    n = len(smooth)
    if n < 2:
        return '<div class="rw-st">Not enough days to draw a trend.</div>'
    left, right, top, bottom = pad
    pw, ph = w - left - right, h - top - bottom
    ymax = _nice_max(max(max(smooth) * 1.15, ucl * 1.5))

    def x(i: int) -> float:
        return left + pw * i / (n - 1)

    def y(v: float) -> float:
        return top + ph * (1 - min(max(v, 0.0), ymax) / ymax)

    label = f"{scope} trend of harm-weighted incident score against the {sigma:g} sigma limit"
    o = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{escape(label)}">']
    for v in (0, ymax / 2, ymax):
        o.append(
            f'<line x1="{left}" x2="{w - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" '
            'stroke="#ECEEED" stroke-width="1"/>'
            f'<text x="{left - 10}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="{fs}" '
            f'fill="#8A979D">{v:g}</text>'
        )
    ticks = _date_ticks(cast(pd.Series, daily["Date"]), 3 if w < 500 else 4)
    for idx, text in ticks:
        anchor = "end" if idx == n - 1 else ("start" if idx == 0 else "middle")
        o.append(
            f'<text x="{x(idx):.1f}" y="{h - 6}" text-anchor="{anchor}" font-size="{fs}" '
            f'fill="#8A979D">{escape(text)}</text>'
        )
    ly = y(ucl)
    o.append(
        f'<rect class="zone" x="{left}" y="{top}" width="{pw}" height="{ly - top:.1f}" '
        'fill="#C98A1B" opacity=".07"/>'
        f'<line class="limit" x1="{left}" x2="{w - right}" y1="{ly:.1f}" y2="{ly:.1f}" '
        'stroke="#17242B" stroke-opacity=".6" stroke-width="1.5" stroke-dasharray="6 5"/>'
        f'<text x="{left + 8}" y="{ly - 8:.1f}" font-size="{fs + 1}" font-weight="700" '
        f'fill="#17242B" fill-opacity=".8">Limit {ucl:.0f} ({sigma:g}σ)</text>'
    )
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(smooth))
    o.append(
        f'<polyline class="trend" points="{pts}" fill="none" stroke="#008080" '
        'stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>'
    )
    ex, ey = x(n - 1), y(smooth[-1])
    o.append(
        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="10" fill="#008080" opacity=".16"/>'
        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="5.5" fill="#008080" stroke="#fff" '
        'stroke-width="2"/>'
    )
    if math.isfinite(z):
        o.append(
            f'<text x="{ex - 16:.1f}" y="{top + fs + 6:.1f}" text-anchor="end" '
            f'font-size="{fs + 1}" font-weight="700" fill="#008080">Now: {z:.2f} σ</text>'
        )
    o.append("</svg>")
    return "".join(o)


def hero_action_html(
    *,
    daily: pd.DataFrame,
    ucl: float,
    status: StrategicStatus,
    sigma: float,
    scope: str,
    view: presentation.StatusView,
    reason: str,
    hot_unit: str,
    hot_category: str,
    chart_note: str,
) -> str:
    z = status.z_score
    t = tone(view.colour)
    chip = {"r": "ALERT", "w": "WATCH", "t": "STABLE"}.get(t, "NO DATA")
    head = presentation.headline(status, sigma, scope)
    desktop = trend_svg(daily, ucl, z, sigma, scope, w=760, h=300, fs=14, pad=(42, 18, 16, 30))
    phone = trend_svg(daily, ucl, z, sigma, scope, w=340, h=230, fs=14, pad=(32, 10, 12, 28))
    driver = (
        f"Primary driver: <b>{escape(hot_category)}</b> in <b>{escape(hot_unit)}</b>."
        if hot_unit != "N/A"
        else "No incidents in this period."
    )
    return (
        '<div class="rw rw-grid">'
        '<div class="rw-card rw-hero rw-c8"><div class="rw-qn">Is it good or bad?</div>'
        f'<div class="rw-t">{escape(head)}</div><div class="rw-st">{escape(chart_note)}</div>'
        f'<div class="rw-chart rw-d">{desktop}</div><div class="rw-chart rw-m">{phone}</div>'
        "</div>"
        f'<div class="rw-card rw-act {t} rw-c4"><div class="rw-qn">What do we do?</div>'
        '<div class="rw-t">Action for this week</div>'
        '<div class="rw-st" style="margin-top:-8px">Written by the engine from the status</div>'
        f'<div class="rw-chip {t}"><i></i>{chip}</div>'
        f'<div class="rw-dir">{escape(view.directive)}</div>'
        f'<div class="rw-ctx">{driver}</div>'
        f'<div class="rw-ctx">Why: {escape(reason)}</div></div></div>'
    )


def drivers_how_html(
    *, shares: list[tuple[str, float]], scope: str, period_text: str, rule: str
) -> str:
    if shares:
        top_name, top_share = shares[0]
        title = f"{top_name} is {top_share * 100:.0f}% of the harm score"
        top = shares[0][1] or 1.0
        bars = "".join(
            f'<div class="rw-drv"><span class="n">{escape(name)}</span>'
            f'<span class="rw-bar"><i style="width:{share / top * 100:.0f}%;'
            f'background:{"#008080" if j == 0 else "#BBDBD8"}"></i></span>'
            f'<span class="v">{share * 100:.0f}%</span></div>'
            for j, (name, share) in enumerate(shares)
        )
    else:
        title, bars = "No incidents in this period", ""
    return (
        '<div class="rw rw-grid"><div class="rw-card rw-c8"><div class="rw-qn">Why?</div>'
        f'<div class="rw-t">{escape(title)}</div>'
        f'<div class="rw-st">Share of harm score by category, {escape(scope)}, '
        f"{escape(period_text)}</div>"
        f'<div class="rw-drvs">{bars}</div></div>'
        '<div class="rw-card rw-how rw-c4"><div class="rw-t">How the status is decided</div>'
        f'<div class="rw-st">The rule in plain words</div><p>{escape(rule)}</p></div></div>'
    )


def footer_html() -> str:
    return (
        '<div class="rw"><div class="rw-foot"><span>Synthetic data. Prototype.</span>'
        "<span>Not a medical device. AGPL-3.0 code, CC BY-NC 4.0 content.</span></div>"
        '<div class="rw-notice">Research and demonstration software. Not a medical device and '
        "not intended for clinical decision-making, diagnosis or treatment. Provided "
        '"as is", without warranty of any kind; the author accepts no liability for any use. '
        "Uses synthetic data only. Personal project, not affiliated with any employer.</div>"
        "</div>"
    )
