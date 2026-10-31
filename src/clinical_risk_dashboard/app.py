"""Risk early warning dashboard (design v2): risk velocity and tolerance over incident reports.

Run from the repository root so ``.streamlit/config.toml`` is picked up (the root ``app.py`` starts this file)::

    streamlit run app.py

All risk arithmetic (harm weights,
kinetics, control limit, z-score, tolerance) comes from ``risk_kinematics``; this file
only filters and wires. Layout lives in ``view.py`` and ``static/style.css``. Data is
synthetic (``sample_data``).
"""

from typing import cast

import pandas as pd
import streamlit as st
from risk_kinematics import calculate_risk_kinetics, classify

from clinical_risk_dashboard import presentation, view
from clinical_risk_dashboard.sample_data import generate_incidents

st.set_page_config(page_title="Risk early warning", page_icon="◼", layout="wide")
# One stylesheet for the whole page, Local font inside.
st.html(f"<style>{view.stylesheet()}</style>")


def show(html: str) -> None:
    """Page parts go through st.markdown: st.html strips the inline SVG of the trend chart."""
    st.markdown(html, unsafe_allow_html=True)


@st.cache_data
def load_data():
    return generate_incidents()


df = load_data()

WHOLE = "Whole hospital"
SIGMA_OPTIONS = {"1σ  Zero tolerance": 1, "2σ  Standard": 2, "3σ  Critical only": 3}
WINDOWS = {"3 days": 3, "7 days": 7, "15 days": 15}
span_days = int((df["Date"].max() - df["Date"].min()).days) + 1
PERIODS = {f"{d} days": d for d in (30, 60, span_days) if d <= span_days}
units = sorted(df["Unit"].unique())
scopes = [WHOLE, *units]


def _scope_of(df_part: pd.DataFrame, scope: str, window: int, sigma: int):
    part = df_part if scope == WHOLE else cast(pd.DataFrame, df_part[df_part["Unit"] == scope])
    k = calculate_risk_kinetics(part, window, sigma)
    return classify(k.daily, k.mean, k.std, sigma)


# The unit is chosen in the left nav or in the header: two widgets, kept in step.
if "scope_nav" not in st.session_state:
    # Open on the unit with the highest sigma now (default window and tolerance): the one
    # that needs attention first. The nav shows every unit's sigma, and "Whole hospital" is
    # one click away.
    _z = {u: _scope_of(df, u, 7, 2).z_score for u in units}
    _first = max(_z, key=lambda u: _z[u])
    st.session_state["scope_nav"] = st.session_state["scope_hdr"] = _first


def _from_nav() -> None:
    st.session_state["scope_hdr"] = st.session_state["scope_nav"]


def _from_hdr() -> None:
    st.session_state["scope_nav"] = st.session_state["scope_hdr"]


# ── Header selectors (read first: the nav shows sigma for the chosen window and tolerance) ──
head_l, h_unit, h_period, h_window, h_tol = st.columns(
    [3.2, 1.3, 1.1, 1.1, 1.6], vertical_alignment="bottom"
)
with h_unit:
    st.selectbox("Unit", scopes, key="scope_hdr", on_change=_from_hdr)
with h_period:
    period_label = st.selectbox("Period", list(PERIODS), index=len(PERIODS) - 1, key="period")
with h_window:
    window = WINDOWS[st.selectbox("Window", list(WINDOWS), index=1, key="window")]
with h_tol:
    sigma_label = st.selectbox("Tolerance", list(SIGMA_OPTIONS), index=1, key="tolerance")
sigma = SIGMA_OPTIONS[sigma_label]

# ── Period filter ────────────────────────────────────────────────────────────────────
end_date = df["Date"].max()
start_date = end_date - pd.Timedelta(days=PERIODS[period_label] - 1)
in_period = cast(pd.DataFrame, df[df["Date"] >= start_date])


# ── Left nav: units with their sigma now (engine, same period, window and tolerance) ──────
def _nav_label(scope: str) -> str:
    s = _scope_of(in_period, scope, window, sigma)
    dot = {presentation.RED: ":red", presentation.AMBER: ":orange"}.get(
        presentation.status_view(s).colour, ":primary"
    )
    return f"{dot}[●]  {scope}   :gray[{view.sigma_text(s.z_score)} σ]"


with st.sidebar:
    show(view.logo_html())
    show(view.nav_views_html())
    show(view.nav_units_title_html())
    st.radio(
        "Unit",
        scopes,
        key="scope_nav",
        on_change=_from_nav,
        format_func=_nav_label,
        label_visibility="collapsed",
    )

selected = st.session_state["scope_nav"]
scope_title = selected

# ── Analytics: risk_kinematics only ──────────────────────────────────────────────────
df_f = (
    in_period if selected == WHOLE else cast(pd.DataFrame, in_period[in_period["Unit"] == selected])
)
kinetics = calculate_risk_kinetics(df_f, window, sigma)
status = classify(kinetics.daily, kinetics.mean, kinetics.std, sigma)

status_v = presentation.status_view(status)
reason = presentation.status_reason(status, sigma)
momentum = presentation.momentum_lines(kinetics.daily, window)
hot_unit, hot_category = presentation.hotspot(df_f)

with head_l:
    show(view.header_html(scope_title))

show(
    view.kpis_html(
        n_reports=len(df_f),
        period_days=PERIODS[period_label],
        status=status,
        sigma=sigma,
        view=status_v,
        reason=reason,
        momentum=momentum,
    )
)
show(
    view.hero_action_html(
        daily=kinetics.daily,
        ucl=kinetics.ucl,
        status=status,
        sigma=sigma,
        scope=scope_title,
        view=status_v,
        reason=reason,
        hot_unit=hot_unit,
        hot_category=hot_category,
        chart_note=(
            f"{window}-day trend of harm-weighted incident score. "
            f"The dashed line is the {sigma} σ limit."
        ),
    )
)

totals = cast(pd.Series, df_f.groupby("Category")["weighted_score"].sum()).sort_values(
    ascending=False
)
grand = float(totals.sum())
shares = [(str(k), float(v) / grand) for k, v in totals.items()] if grand > 0 else []
first, last = df_f["Date"].min(), df_f["Date"].max()
period_text = f"{first.day} {first:%b} to {last.day} {last:%b}" if not df_f.empty else "no days"
show(
    view.drivers_how_html(
        shares=shares,
        scope=scope_title,
        period_text=period_text,
        rule=presentation.status_rule_body(),
    )
)
show(view.footer_html())
