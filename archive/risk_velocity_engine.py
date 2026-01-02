import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Risk Velocity Engine", layout="wide")
APPLE_WHITE, APPLE_BLACK, IOS_RED, GRAY = "#F5F5F7", "#1D1D1F", "#FF3B30", "#86868B"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {APPLE_WHITE}; }}
    .stMetric {{ background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #D2D2D7; }}
    </style>
    """, unsafe_allow_index=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def load_and_process():
    df = pd.read_csv('hospital_risk_data.csv', parse_dates=['Date'])
    harm_mapping = {'A':1, 'B':2, 'C':3, 'D':4, 'E':5, 'F':6, 'G':7, 'H':8, 'I':9}
    df['Harm_Score'] = df['Harm_Level'].map(harm_mapping)
    return df

df = load_and_process()

# --- 3. SIDEBAR CONTROLS (Parameters) ---
st.sidebar.title("Control Center")
st.sidebar.markdown("Adjust the engine sensitivity and focus.")

selected_unit = st.sidebar.selectbox("Select Clinical Unit", options=df['Unit'].unique())

window = st.sidebar.select_slider(
    "Alert Sensitivity (Days)",
    options=[3, 7, 15],
    value=7,
    help="3 days: High sensitivity (Tactical). 7 days: Balanced (Operational). 15 days: Long-term (Strategic)."
)

# --- 4. KINEMATIC CALCULATIONS ---
unit_cat = df.groupby(['Date', 'Unit', 'Category']).agg(rpn=('Harm_Score', 'sum')).reset_index()
unit_total = unit_cat.groupby(['Date', 'Unit']).agg(total_rpn=('rpn', 'sum')).reset_index()
unit_total = unit_total.sort_values(['Unit', 'Date'])

# Apply selected window
unit_total['Velocity'] = unit_total.groupby('Unit')['total_rpn'].transform(lambda x: x.diff(window) / window)
unit_total['Acceleration'] = unit_total.groupby('Unit')['Velocity'].transform(lambda x: x.diff(window) / window)
unit_total = unit_total.dropna(subset=['Acceleration'])

# Get current stats for selected unit
unit_data = unit_total[unit_total['Unit'] == selected_unit]
latest_stats = unit_data.iloc[-1]
accel_val = latest_stats['Acceleration']

# Find top category driver
latest_date = df['Date'].max()
cat_breakdown = unit_cat[(unit_cat['Date'] == latest_date) & (unit_cat['Unit'] == selected_unit)]
top_category = cat_breakdown.sort_values('rpn', ascending=False).iloc[0]['Category']

# --- 5. DASHBOARD UI ---
st.title(f"Executive Risk Surveillance: {selected_unit}")

# High-level Metrics
m1, m2, m3 = st.columns(3)
m1.metric("Risk Magnitude (RPN)", f"{latest_stats['total_rpn']:.0f}")
m2.metric("Risk Velocity", f"{latest_stats['Velocity']:.2f}")
m3.metric("Momentum (Acceleration)", f"{accel_val:.2f}", delta=f"{accel_val:.2f}", delta_color="inverse")

# Visuals
fig = plt.figure(figsize=(14, 6), facecolor=APPLE_WHITE)
gs = gridspec.GridSpec(1, 2, wspace=0.3)

# Pulse Graph
ax1 = fig.add_subplot(gs[0])
ax1.plot(unit_data['Date'], unit_data['total_rpn'], color=APPLE_BLACK, lw=2.5)
ax1.fill_between(unit_data['Date'], unit_data['total_rpn'], color=APPLE_BLACK, alpha=0.05)
ax1.set_title("RISK MAGNITUDE (The Pulse)", loc='left', color=GRAY, fontsize=10)
ax1.set_facecolor(APPLE_WHITE)
ax1.spines[['top', 'right']].set_visible(False)

# Momentum Graph
ax2 = fig.add_subplot(gs[1])
ax2.plot(unit_data['Date'], unit_data['Acceleration'], color=IOS_RED, lw=2, linestyle='--')
ax2.set_title(f"RISK MOMENTUM ({window}-Day Sensitivity)", loc='left', color=GRAY, fontsize=10)
ax2.set_facecolor(APPLE_WHITE)
ax2.axhline(0, color=GRAY, lw=0.5, alpha=0.5)
ax2.spines[['top', 'right']].set_visible(False)

st.pyplot(fig)

# Diagnosis Box
st.subheader("Strategic Diagnosis")
status_color = "error" if accel_val > 0.4 else "warning" if accel_val > 0 else "success"
status_text = "CRITICAL ACCELERATION" if accel_val > 0.4 else "GAINING MOMENTUM" if accel_val > 0 else "STABLE"

st.info(f"""
**Status:** {status_text}  
**Primary Driver:** {top_category} incidents  
**Insight:** At a {window}-day sensitivity, {selected_unit} is showing a momentum score of {accel_val:.2f}. 
This indicates that the risk environment is {'compounding' if accel_val > 0 else 'stabilizing'}. 
Immediate review of {top_category} protocols is suggested.
""")