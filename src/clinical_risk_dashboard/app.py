"""Clinical risk dashboard: risk velocity and tolerance over incident reports.

Run from the repository root so ``.streamlit/config.toml`` (light theme, zero radius) is
picked up::

    streamlit run src/clinical_risk_dashboard/app.py

All risk arithmetic (harm weights,
kinetics, control limit, z-score, tolerance) comes from ``risk_kinematics``; this file
only filters, lays out and styles. Data is synthetic (``sample_data``).
"""

from html import escape
from typing import cast

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from clinical_risk_dashboard import brand, charts, presentation
from clinical_risk_dashboard.sample_data import generate_incidents
from risk_kinematics import calculate_risk_kinetics, classify

brand.apply(st, page_title="Clinical Risk Dashboard", page_icon="◼", layout="wide")

# App-local layout on top of the canonical stylesheet: cream ground, white raised
# panels, hairline borders, zero radius. Only brand values appear here.
st.markdown(
    """
<style>
  .stApp { background: #FDFBF7; color: #17242B; font-family: var(--mm-font-display); }
  section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E3E5E4; }
  .crd-head { padding: 8px 0 28px; border-bottom: 1px solid var(--mm-rule); margin-bottom: 28px; }
  .crd-head h1 { font: 800 2.4rem/1.05 var(--mm-font-display); letter-spacing: -0.04em;
                 color: #17242B; margin: 10px 0 14px; padding: 0; }
  .crd-meta { display: flex; flex-wrap: wrap; gap: 8px 28px; }
  .crd-meta .mm-tick { color: var(--mm-ink-2); font-size: 12px; }
  .crd-brief { margin-top: 22px; padding: 18px 22px; background: #FFFFFF;
               border: 1px solid #E3E5E4; border-left: 3px solid var(--crd-state); }
  .crd-brief .directive { font-size: 1.25rem; font-weight: 700; color: #17242B;
                          letter-spacing: -0.02em; margin-top: 6px; }
  .crd-brief .context { color: var(--mm-ink-2); margin-top: 6px; }
  .crd-card { background: #FFFFFF; border: 1px solid #E3E5E4; padding: 22px 24px;
              min-height: 168px; display: flex; flex-direction: column; margin-bottom: 20px; }
  .crd-card .value { font: 800 1.9rem/1.1 var(--mm-font-display); letter-spacing: -0.03em;
                     margin: 12px 0 auto; }
  .crd-card .context { color: var(--mm-ink-2); font-size: 14px; border-top: 1px solid
                       var(--mm-rule); padding-top: 10px; margin-top: 14px; }
  .crd-side .mm-wordmark { font-size: 30px; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    return generate_incidents()


df = load_data()

# ── Sidebar controls ─────────────────────────────────────────────────────────
SIGMA_OPTIONS = {"Zero tolerance (1σ)": 1, "Standard (2σ)": 2, "Critical only (3σ)": 3}

with st.sidebar:
    st.markdown(
        '<div class="crd-side mm-on-light"><span class="mm-wordmark">mmonfar'
        '<span class="mm-dot"></span></span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="mm-label-sm">Surveillance controls</div>', unsafe_allow_html=True)
    scope = st.radio("Analysis scope", ["Whole hospital", "Single unit"])
    units = sorted(df["Unit"].unique())
    selected_unit = st.selectbox("Unit", units) if scope == "Single unit" else None

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()
    selected_dates = st.date_input(
        "Analysis period", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    window = st.select_slider("Kinetic window (days)", options=[3, 7, 15], value=7)
    sigma_label = st.select_slider(
        "Risk tolerance mode",
        options=list(SIGMA_OPTIONS),
        value="Standard (2σ)",
        help="Alert sensitivity, as a statistical confidence interval.",
    )
    sigma = SIGMA_OPTIONS[sigma_label]
    st.markdown(
        '<div class="mm-tick" style="margin-top:24px">Prototype · synthetic data</div>',
        unsafe_allow_html=True,
    )

# ── Filtering ────────────────────────────────────────────────────────────────
mask = pd.Series(True, index=df.index)
if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
    day = df["Date"].dt.date
    mask &= (day >= start_date) & (day <= end_date)
if selected_unit is not None:
    mask &= df["Unit"] == selected_unit
df_f = cast(pd.DataFrame, df.loc[mask]).copy()

# ── Analytics: risk_kinematics only ──────────────────────────────────────────
kinetics = calculate_risk_kinetics(df_f, window, sigma)
status = classify(kinetics.daily, kinetics.mean, kinetics.std, sigma)

view = presentation.status_view(status)
momentum = presentation.momentum_view(kinetics.daily, status.rising_trend)
hot_unit, hot_category = presentation.hotspot(df_f)
scope_title = "Whole hospital" if selected_unit is None else selected_unit

# ── Header and directive ─────────────────────────────────────────────────────
st.markdown(
    f"""
<div class="mm-on-light crd-head">
  <div class="mm-label">Clinical risk · Risk velocity</div>
  <h1>{escape(scope_title)}</h1>
  <div class="crd-meta">
    <span class="mm-tick">Tolerance mode: {escape(sigma_label)}</span>
    <span class="mm-tick">Alert trigger: outliers beyond {escape(status.confidence)}</span>
    <span class="mm-tick">{len(df_f):,} incident reports</span>
  </div>
  <div class="crd-brief" style="--crd-state:{view.colour}">
    <div class="mm-label-sm" style="color:{view.colour}">Directive</div>
    <div class="directive">{escape(view.directive)}</div>
    <div class="context" title="{escape(presentation.status_rule())}">Surveillance status:
      <b>{escape(view.label)}</b>.
      Primary driver: <b>{escape(hot_category)}</b> in <b>{escape(hot_unit)}</b>.</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


def card(label: str, value: str, context: str, colour: str = "#17242B", tooltip: str = "") -> None:
    st.markdown(
        f"""<div class="mm-on-light crd-card" title="{escape(tooltip)}">
<div class="mm-label-sm">{escape(label)}</div>
<div class="value" style="color:{colour}">{escape(value)}</div>
<div class="context">{context}</div></div>""",
        unsafe_allow_html=True,
    )


k1, k2, k3 = st.columns(3)
with k1:
    card(
        "Surveillance status",
        view.label,
        f"Variance vs baseline: <b>{status.z_score:.2f} σ</b>",
        view.colour,
        presentation.status_rule(),
    )
with k2:
    card(
        "Risk momentum (latest day)",
        momentum.label,
        f"<b>{escape(momentum.context)}</b>",
        momentum.colour,
    )
with k3:
    card("Resource priority", hot_unit, f"Primary threat: <b>{escape(hot_category)}</b>")

# ── Charts ───────────────────────────────────────────────────────────────────


def show(fig: go.Figure) -> None:
    # theme=None: keep the mmonfar plotly template instead of Streamlit's own chart theme.
    with st.container(border=True):
        st.plotly_chart(fig, theme=None, config=charts.PLOT_CONFIG)


col_l, col_r = st.columns([1.8, 1.2], gap="large")
with col_l:
    show(charts.spc_chart(kinetics.daily, kinetics.ucl, sigma, status.rising_trend))
    show(charts.acceleration_chart(kinetics.daily))
with col_r:
    show(charts.harm_distribution_chart(df_f))

st.markdown(
    '<div class="mm-label" style="margin:12px 0 4px">Weekly intensity matrix</div>',
    unsafe_allow_html=True,
)
show(charts.intensity_matrix(df_f))

st.caption(
    "Research and demonstration software. Not a medical device and not intended for "
    'clinical decision-making, diagnosis or treatment. Provided "as is", without warranty '
    "of any kind; the author accepts no liability for any use. Uses synthetic data only. "
    "Personal project · not affiliated with any employer · synthetic data only."
)
