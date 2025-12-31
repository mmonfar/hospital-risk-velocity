import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Hospital Risk Velocity", layout="wide")
APPLE_WHITE, APPLE_BLACK, IOS_RED, GRAY = "#F5F5F7", "#1D1D1F", "#FF3B30", "#86868B"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {APPLE_WHITE}; }}
    [data-testid="stMetricValue"] {{ color: {APPLE_BLACK}; font-weight: bold; }}
    .stMetric {{ background-color: white; padding: 15px; border-radius: 12px; border: 1px solid #E5E5E7; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def load_and_process():
    df = pd.read_csv('hospital_risk_data.csv', parse_dates=['Date'])
    harm_mapping = {'A':1, 'B':2, 'C':3, 'D':4, 'E':5, 'F':6, 'G':7, 'H':8, 'I':9}
    df['Harm_Score'] = df['Harm_Level'].map(harm_mapping)
    return df

df = load_and_process()

# --- 3. SIDEBAR CONTROLS ---
st.sidebar.title("Surveillance Controls")
window = st.sidebar.select_slider("Select Surveillance Sensitivity", options=[3, 7, 15], value=7)

# --- 4. GLOBAL & UNIT MATH ---
global_total = df.groupby('Date').agg(total_rpn=('Harm_Score', 'sum')).reset_index().sort_values('Date')
global_total['Velocity'] = global_total['total_rpn'].diff(window) / window
global_total['Acceleration'] = global_total['Velocity'].diff(window) / window

unit_cat = df.groupby(['Date', 'Unit', 'Category']).agg(rpn=('Harm_Score', 'sum')).reset_index()
unit_total = unit_cat.groupby(['Date', 'Unit']).agg(total_rpn=('rpn', 'sum')).reset_index().sort_values(['Unit', 'Date'])
unit_total['Acceleration'] = unit_total.groupby('Unit')['total_rpn'].transform(lambda x: (x.diff(window)/window).diff(window)/window)

# Identify Hotspot
latest_date = unit_total['Date'].max()
latest_units = unit_total[unit_total['Date'] == latest_date].dropna(subset=['Acceleration'])
hotspot_row = latest_units.sort_values('Acceleration', ascending=False).iloc[0]
hotspot_unit = hotspot_row['Unit']
hotspot_accel = hotspot_row['Acceleration']

# --- 5. UI LAYOUT ---
st.title("Hospital Risk Kinetic Dashboard")
st.caption(f"Surveillance window: {window} days | Data refreshed through {latest_date.strftime('%Y-%m-%d')}")

# SECTION A: GLOBAL VIEW
st.subheader("I. System-Wide Health")
g1, g2 = st.columns(2)
with g1:
    fig_g = plt.figure(figsize=(10, 3), facecolor=APPLE_WHITE)
    plt.plot(global_total['Date'], global_total['total_rpn'], color=APPLE_BLACK, lw=2)
    plt.fill_between(global_total['Date'], global_total['total_rpn'], alpha=0.05)
    plt.title("GLOBAL RISK MAGNITUDE", loc='left', color=GRAY, fontsize=9)
    plt.gca().set_facecolor(APPLE_WHITE)
    plt.gca().spines[['top', 'right']].set_visible(False)
    st.pyplot(fig_g)
with g2:
    st.metric("Global Acceleration", f"{global_total['Acceleration'].iloc[-1]:.2f}", delta="System Trend", delta_color="inverse")
    st.info("System-wide acceleration indicates whether the hospital's total risk profile is compounding or stabilizing.")

st.divider()

# SECTION B: THE UNIT OF CONCERN
st.subheader(f"II. Priority Unit Drill-down: {hotspot_unit}")
m1, m2, m3 = st.columns(3)
hotspot_df = unit_total[unit_total['Unit'] == hotspot_unit]
latest_h_stats = hotspot_df.iloc[-1]

m1.metric("Unit Risk Score", f"{latest_h_stats['total_rpn']:.0f}")
m2.metric("Hotspot Acceleration", f"{hotspot_accel:.2f}", delta="Critical Early Warning", delta_color="inverse")

cat_data = unit_cat[(unit_cat['Date'] == latest_date) & (unit_cat['Unit'] == hotspot_unit)]
top_cat = cat_data.sort_values('rpn', ascending=False).iloc[0]['Category'] if not cat_data.empty else "N/A"
m3.metric("Primary Driver", top_cat)

# SECTION C: UNIT CHARTS
fig_u = plt.figure(figsize=(14, 5), facecolor=APPLE_WHITE)
gs = gridspec.GridSpec(1, 2, wspace=0.3)
ax1 = fig_u.add_subplot(gs[0]); ax2 = fig_u.add_subplot(gs[1])
ax1.plot(hotspot_df['Date'], hotspot_df['total_rpn'], color=APPLE_BLACK, lw=2.5)
ax1.set_title(f"{hotspot_unit}: RISK PULSE", loc='left', color=GRAY, fontsize=10)
ax2.plot(hotspot_df['Date'], hotspot_df['Acceleration'], color=IOS_RED, lw=2, linestyle='--')
ax2.axhline(0, color=GRAY, lw=0.5)
ax2.set_title(f"{hotspot_unit}: MOMENTUM (Acceleration)", loc='left', color=GRAY, fontsize=10)
for ax in [ax1, ax2]:
    ax.set_facecolor(APPLE_WHITE)
    ax.spines[['top', 'right']].set_visible(False)
st.pyplot(fig_u)

# SECTION D: STRATEGIC ACTION PLAN
st.subheader("III. Strategic Action Plan")
st.success(f"""
**Immediate Recommendation:**
Based on the **{window}-day kinetic analysis**, the **{hotspot_unit}** requires priority surveillance. 
Acceleration in this unit is currently **{hotspot_accel:.2f}**, primarily driven by **{top_cat}** incidents.

1. **Deploy Investigative Audit:** Review the last 72 hours of {top_cat} reports in {hotspot_unit}.
2. **Resource Re-allocation:** Assess if nursing ratios in {hotspot_unit} are contributing to the risk momentum.
3. **Leading Indicator Alert:** While current RPN is {latest_h_stats['total_rpn']:.0f}, the positive acceleration suggests this score will rise without intervention.
""")

# --- 6. SIDEBAR EXPORT ---
st.sidebar.divider()
if os.path.exists("executive_risk_dashboard.png"):
    with open("executive_risk_dashboard.png", "rb") as file:
        st.sidebar.download_button(
            label="Export Executive Brief (PNG)",
            data=file,
            file_name=f"Risk_Report_{hotspot_unit}.png",
            mime="image/png"
        )
else:
    st.sidebar.warning("Run 'risk_velocity_engine.py' once to generate the exportable brief.")