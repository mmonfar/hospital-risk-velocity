import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analytics import (
    load_and_quantize, aggregate_unit_daily, smooth_rpn, 
    compute_kinematics, interpret_acceleration
)

# ---------------------------------------------------------
# 1. CLEAN THEME & ULTRA-WIDE HEADER CSS
# ---------------------------------------------------------
st.set_page_config(page_title="Risk Intelligence Portal", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E9ECEF; }
    
    /* Full-Width Global Dashboard Header */
    .dashboard-header {
        text-align: center; 
        margin-bottom: 30px; 
        padding: 40px 20px;
        background: white; 
        border: 1px solid #E9ECEF; 
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }

    /* Ultra-Wide Executive Brief */
    .exec-brief {
        max-width: 1200px; 
        margin: 20px auto 0 auto; 
        padding: 20px 40px;
        background: #F8F9FA; 
        border-radius: 12px; 
        border: 1px solid #E9ECEF;
        font-size: 1.1rem; 
        color: #1D1D1F;
        line-height: 1.6;
        text-align: center;
    }

    /* KPI Cards */
    .metric-box {
        background: white; border: 1px solid #E9ECEF; border-radius: 12px;
        padding: 22px; flex: 1; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        height: 180px; display: flex; flex-direction: column;
    }
    
    .m-label { color: #86868B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; }
    .m-value { color: #1D1D1F; font-size: 2.2rem; font-weight: 700; margin-top: 8px; }
    .m-context { color: #86868B; font-size: 0.85rem; line-height: 1.4; margin-top: auto; border-top: 1px solid #F1F3F5; padding-top: 10px; }
    
    /* Ensuring native containers look like high-end cards */
    [data-testid="stElementContainer"] > div:has(div.stVerticalBlockBorderWrapper) {
        background-color: white;
        border-radius: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. DATA ENGINE
# ---------------------------------------------------------
df = load_and_quantize("hospital_risk_data.csv")

with st.sidebar:
    st.markdown("### 🎛️ Controls")
    scope = st.radio("Scope", ["Whole Hospital", "Single Unit"])
    selected_unit = st.selectbox("Unit", sorted(df["Unit"].unique())) if scope == "Single Unit" else None
    window = st.select_slider("Surveillance Window", options=[3, 7, 15], value=7)
    date_range = st.date_input("Analysis Period", value=(df["Date"].min(), df["Date"].max()))

mask = (df["Date"] >= pd.Timestamp(date_range[0])) & (df["Date"] <= pd.Timestamp(date_range[1]))
df_f = df.loc[mask].copy()
if scope == "Single Unit": df_f = df_f[df_f["Unit"] == selected_unit]

raw_daily = aggregate_unit_daily(df_f)
kinetics = compute_kinematics(smooth_rpn(raw_daily.copy(), window), window)
view_df = kinetics.groupby("Date").agg({"total_rpn": "sum", "rpn_smooth": "sum", "acceleration": "mean"}).reset_index() if scope == "Whole Hospital" else kinetics

pivot = df_f.groupby(['Date', 'Unit'])['harm_score'].sum().unstack().fillna(0)
heat_data = pivot.resample('W').sum().T
heat_data.columns = [d.strftime('%m/%d') for d in heat_data.columns]
cat_sum = df_f.groupby("Category")["harm_score"].sum().sort_values(ascending=True)

latest = view_df.iloc[-1]
accel = latest['acceleration']
status_brief = interpret_acceleration(accel).split("–")[0]
hotspot = df_f.groupby(["Unit", "Category"])["harm_score"].sum().idxmax()

# ---------------------------------------------------------
# 3. GLOBAL HEADER
# ---------------------------------------------------------
st.markdown(f"""
<div class="dashboard-header">
    <h1 style="margin:0; font-weight:700; color:#1D1D1F; font-size: 2.4rem; letter-spacing: -0.02em;">
        {scope if scope == 'Whole Hospital' else selected_unit} Risk Intelligence
    </h1>
    <p style="margin:10px 0 0 0; color:#86868B; font-weight:500; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.05em;">
        Data Window: {date_range[0].strftime('%d %b %Y')} — {date_range[1].strftime('%d %b %Y')}
    </p>
    <div class="exec-brief">
        <span style="font-weight:800; color:#1D1D1F; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; display: block; margin-bottom: 8px;">Executive Action Brief</span>
        Analysis confirms a <b>{status_brief.lower()}</b> trend across the current surveillance window. 
        Focus resources on <b>{hotspot[1]}</b> within <b>{hotspot[0]}</b> to mitigate immediate momentum.
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. KPI ROW
# ---------------------------------------------------------
k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f"""<div class="metric-box"><div class="m-label">Risk Magnitude</div><div class="m-value">{latest['total_rpn']:.0f} RPN</div>
    <div class="m-context"><b>Harm Magnitude:</b> Cumulative severity score.<br><span style="color:#28A745; font-weight:600;">Target: &lt; 20 RPN/Unit</span></div></div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class="metric-box"><div class="m-label">Risk Trajectory</div><div class="m-value" style="color:{'#FF3B30' if accel > 0 else '#28A745'}">{'↑' if accel > 0 else '↓'} {abs(accel):.2f}</div>
    <div class="m-context"><b>{status_brief}</b><br>Daily rate of harm accumulation.</div></div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class="metric-box"><div class="m-label">Primary Hotspot</div><div class="m-value" style="font-size:1.6rem;">{hotspot[1]}</div>
    <div class="m-context">Primary risk driver located in <b>{hotspot[0]}</b>.</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. SYNCHRONIZED VISUALIZATION CONTAINERS (NATIVE WRAP)
# ---------------------------------------------------------
col_l, col_r = st.columns([1.8, 1.2], gap="large")

with col_l:
    with st.container(border=True):
        # HARM VOLUME
        fig_v = go.Figure()
        fig_v.add_trace(go.Bar(x=view_df["Date"], y=view_df["total_rpn"], marker_color="rgba(200, 200, 200, 0.2)"))
        fig_v.add_trace(go.Scatter(x=view_df["Date"], y=view_df["rpn_smooth"], line=dict(color="#1D1D1F", width=3)))
        fig_v.update_layout(title="<b>HARM VOLUME SIGNAL</b>", height=280, margin=dict(l=60, r=20, t=50, b=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
        st.plotly_chart(fig_v, use_container_width=True, config={'displayModeBar': False})

        # ACCELERATION
        fig_a = go.Figure()
        fig_a.add_trace(go.Bar(x=view_df["Date"], y=view_df["acceleration"], marker_color="rgba(255, 59, 48, 0.1)"))
        fig_a.add_trace(go.Scatter(x=view_df["Date"], y=view_df["acceleration"], line=dict(color="#FF3B30", width=2)))
        fig_a.add_hline(y=0, line_dash="dot", line_color="#86868B")
        fig_a.update_layout(title="<b>RISK ACCELERATION</b>", height=250, margin=dict(l=60, r=20, t=40, b=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
        st.plotly_chart(fig_a, use_container_width=True, config={'displayModeBar': False})

with col_r:
    with st.container(border=True):
        # HEATMAP
        fig_h = px.imshow(heat_data, color_continuous_scale="YlOrRd", title="<b>WEEKLY RISK DENSITY</b>")
        fig_h.update_layout(height=280, margin=dict(l=10, r=10, t=50, b=40), coloraxis_showscale=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title="", yaxis_title="")
        st.plotly_chart(fig_h, use_container_width=True, config={'displayModeBar': False})

        # DISTRIBUTION
        fig_b = px.bar(cat_sum, orientation='h', title="<b>HARM DISTRIBUTION</b>")
        fig_b.update_traces(marker_color="#1D1D1F", texttemplate='  %{y} | %{x} RPN', textposition='inside', insidetextanchor='start', textfont=dict(color="white"))
        fig_b.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=40), xaxis_visible=False, yaxis_visible=False, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_b, use_container_width=True, config={'displayModeBar': False})