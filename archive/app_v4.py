import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- 1. SETTINGS & CSS ---
st.set_page_config(page_title="Risk Intelligence Portal", layout="wide")

HARM_LABELS = {
    1: "No Harm / Near Miss", 2: "Minimal Harm", 3: "Low Harm",
    4: "Moderate Harm", 5: "Significant Harm", 6: "Severe Harm",
    7: "Life-Threatening Harm", 8: "Death / Sentinel Event", 9: "Catastrophic Harm"
}

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA !important; }
    .dashboard-header {
        width: 100%; margin-bottom: 30px; padding: 40px;
        background: white; border: 1px solid #E9ECEF; border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .exec-brief {
        margin-top: 20px; padding: 20px;
        background: #F8F9FA; border-radius: 12px; border-left: 5px solid #1D1D1F;
        font-size: 1.1rem; line-height: 1.6;
    }
    .metric-box {
        background: white; border: 1px solid #E9ECEF; border-radius: 12px;
        padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        height: 180px; display: flex; flex-direction: column;
        justify-content: space-between; margin-bottom: 25px;
    }
    .m-label { color: #86868B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
    .m-value { color: #1D1D1F; font-size: 2.2rem; font-weight: 700; line-height: 1; }
    .m-context { color: #86868B; font-size: 0.85rem; border-top: 1px solid #F1F3F5; padding-top: 10px; margin-top: auto; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def get_processed_data():
    # hospital_risk_data.csv must be in your directory
    df = pd.read_csv('hospital_risk_data.csv', parse_dates=['Date'])
    harm_weights = {chr(65+i): (i+1)**2 for i in range(9)}
    df['weighted_score'] = df['Harm_Level'].map(harm_weights)
    df['raw_level'] = df['Harm_Level'].map({chr(65+i): i+1 for i in range(9)})
    return df

df = get_processed_data()

# --- 3. SIDEBAR (Risk Appetite Controls) ---
with st.sidebar:
    st.markdown("### 🎛️ Surveillance Engine")
    scope = st.radio("Analysis Scope", ["Whole Hospital", "Single Unit"])
    selected_unit = st.selectbox("Unit Select", sorted(df["Unit"].unique())) if scope == "Single Unit" else None
    
    min_date = df['Date'].min().to_pydatetime()
    max_date = df['Date'].max().to_pydatetime()
    selected_dates = st.date_input("Analysis Period", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    
    window = st.select_slider("Kinetic Window (Smoothing)", options=[3, 7, 15], value=7)
    
    st.markdown("---")
    # Mapping Sigma to Executive Language
    sigma_map = {
        "Zero Tolerance (1σ)": 1,
        "Standard (2σ)": 2,
        "Critical Only (3σ)": 3
    }
    
    selected_sigma_label = st.select_slider(
        "Risk Tolerance Mode",
        options=list(sigma_map.keys()),
        value="Standard (2σ)",
        help="Zero Tolerance: Alerts on 32% of deviations. Standard: Alerts on top 5%. Critical: Alerts on top 0.3%."
    )
    sigma_val = sigma_map[selected_sigma_label]

# --- 4. DATA FILTERING & MATH ---
if len(selected_dates) == 2:
    start_date, end_date = selected_dates
    df_f = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)].copy()
else:
    df_f = df.copy()

if scope == "Single Unit":
    df_f = df_f[df_f["Unit"] == selected_unit]

# Calculations
daily = df_f.groupby('Date').agg({'weighted_score': 'sum', 'raw_level': 'mean'}).reset_index()
daily['smooth'] = daily['weighted_score'].rolling(window, center=True, min_periods=1).mean()
daily['velocity'] = daily['smooth'].diff(window) / window
daily['acceleration'] = daily['velocity'].diff(window) / window

# Baseline Stats
mean_val = daily['weighted_score'].mean()
std_val = daily['weighted_score'].std()
ucl_value = mean_val + (sigma_val * std_val)

# --- 5. EXECUTIVE ACTION LOGIC ---
confidence_levels = {1: "68%", 2: "95%", 3: "99.7%"}
conf_pct = confidence_levels[sigma_val]

if not daily.dropna().empty:
    latest = daily.dropna().iloc[-1]
    z_score = (latest['weighted_score'] - mean_val) / std_val
    hotspot = df_f.groupby(["Unit", "Category"])["weighted_score"].sum().idxmax()
    
    # Directive Logic
    if z_score > sigma_val:
        exec_status, status_color = "OUTSIDE TOLERANCE", "#FF3B30"
        action_prompt = f"🔴 ALERT: Risk exceeds the {conf_pct} stability threshold. Immediate intervention required."
    elif z_score > (sigma_val * 0.7):
        exec_status, status_color = "MARGINAL VARIANCE", "#FF9500"
        action_prompt = "🟡 WATCH: Risk is trending toward the upper limit. Brief unit leads on preventative measures."
    else:
        exec_status, status_color = "WITHIN TOLERANCE", "#28A745"
        action_prompt = "🟢 STABLE: Risk levels are within normal historical variations for this period."
    
    avg_harm_idx = int(round(latest['raw_level']))
    harm_desc = HARM_LABELS.get(avg_harm_idx, "Unknown")
else:
    exec_status, status_color, z_score, action_prompt = "NO DATA", "#86868B", 0, "Select a valid date range."
    hotspot = ("N/A", "N/A")
    latest = {'acceleration': 0}

# --- 6. HEADER & STRATEGIC BRIEF ---
st.markdown(f"""
<div class="dashboard-header">
    <h1 style="margin:0; font-size: 2.2rem;">{scope if scope == 'Whole Hospital' else selected_unit} Risk Intelligence</h1>
    <div style="display: flex; gap: 20px; margin-top: 15px; font-size: 0.85rem; color: #86868B;">
        <span>🛡️ <b>Tolerance Mode:</b> {selected_sigma_label}</span>
        <span>📈 <b>Trigger Sensitivity:</b> Outliers beyond {conf_pct} probability</span>
    </div>
    <div class="exec-brief" style="border-left-color: {status_color};">
        <div style="font-size: 0.75rem; text-transform: uppercase; color: {status_color}; font-weight: 700; letter-spacing: 0.5px;">Strategic Directive</div>
        <div style="font-size: 1.25rem; font-weight: 600; margin-top: 5px; color: #1D1D1F;">{action_prompt}</div>
        <div style="margin-top: 10px; font-size: 0.95rem; color: #424245;">
            The system is currently <b>{exec_status}</b>. Primary driver: <b>{hotspot[1]}</b> in <b>{hotspot[0]}</b>.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# KPI Cards
k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f"""<div class="metric-box"><div class="m-label">Surveillance Status</div><div class="m-value" style="color:{status_color}; font-size:1.8rem;">{exec_status}</div>
    <div class="m-context">Variance vs Base: <b>{z_score:.2f} σ</b></div></div>""", unsafe_allow_html=True)
with k2:
    accel_val = latest['acceleration']
    accel_label = "Increasing" if accel_val > 0.01 else ("Decreasing" if accel_val < -0.01 else "Flat")
    accel_action = "Risk momentum is rising" if accel_val > 0.01 else "Risk momentum is cooling"
    st.markdown(f"""<div class="metric-box"><div class="m-label">Risk Momentum</div><div class="m-value" style="color:{'#FF3B30' if accel_val > 0.01 else '#28A745'}">{accel_label}</div>
    <div class="m-context">Context: <b>{accel_action}</b></div></div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class="metric-box"><div class="m-label">Resource Priority</div><div class="m-value" style="font-size:1.6rem;">{hotspot[0]}</div>
    <div class="m-context">Primary Threat: <b>{hotspot[1]}</b></div></div>""", unsafe_allow_html=True)

# --- 7. ALIGNED GRAPHS ---
col_l, col_r = st.columns([1.8, 1.2], gap="large")

with col_l:
    # SPC Chart
    with st.container(border=True):
        fig_m = go.Figure()
        fig_m.add_trace(go.Scatter(x=daily["Date"], y=daily["weighted_score"], name="Daily", line=dict(color="#E5E5E7")))
        fig_m.add_trace(go.Scatter(x=daily["Date"], y=daily["smooth"], name="Trend", line=dict(color="#1D1D1F", width=3)))
        fig_m.add_hline(y=ucl_value, line_dash="dot", line_color="#FF3B30", annotation_text=f"Tolerance ({sigma_val}σ)")
        fig_m.update_layout(title="<b>STATISTICAL CONTROL (SPC)</b>", height=280, template="plotly_white", margin=dict(t=40, b=20, l=40, r=20), showlegend=False)
        st.plotly_chart(fig_m, use_container_width=True, config={'displayModeBar': False})

    # Momentum Chart
    with st.container(border=True):
        fig_a = px.area(daily, x="Date", y="acceleration")
        fig_a.update_traces(line_color="#FF3B30", fillcolor="rgba(255, 59, 48, 0.1)")
        fig_a.update_layout(title="<b>TREND ACCELERATION</b>", height=200, template="plotly_white", margin=dict(t=40, b=20, l=40, r=20), xaxis_title="", yaxis_title="")
        st.plotly_chart(fig_a, use_container_width=True, config={'displayModeBar': False})

with col_r:
    # Bar Chart (Aligned Height)
    with st.container(border=True):
        cat_sum = df_f.groupby("Category")["weighted_score"].sum().sort_values()
        fig_b = go.Figure(go.Bar(
            x=cat_sum.values, y=cat_sum.index, orientation='h',
            marker=dict(color="#1D1D1F", cornerradius=10),
            text=[f"<b>{cat}</b> | {val:,.0f} RPN" for cat, val in zip(cat_sum.index, cat_sum.values)],
            textposition='inside', insidetextanchor='end', textfont=dict(size=14, color="white"),
        ))
        fig_b.update_layout(
            title="<b>HARM DISTRIBUTION</b>", height=530, bargap=0.2,
            template="plotly_white", showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False),
            margin=dict(t=60, b=20, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_b, use_container_width=True, config={'displayModeBar': False})

# --- 8. MATRIX ---
st.markdown("### Weekly Intensity Matrix")

pivot = df_f.groupby(['Date', 'Unit'])['weighted_score'].sum().unstack().fillna(0)
heat_data = pivot.resample('W').sum().T
fig_h = px.imshow(heat_data, color_continuous_scale="YlOrRd")
fig_h.update_layout(height=300, yaxis_title="", coloraxis_showscale=False, margin=dict(t=10, b=10))
st.plotly_chart(fig_h, use_container_width=True, config={'displayModeBar': False})