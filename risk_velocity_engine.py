import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# 1. Load and Quantize
# ---------------------------------------------------------
df = pd.read_csv('hospital_risk_data.csv', parse_dates=['Date'])
harm_mapping = {'A':1, 'B':2, 'C':3, 'D':4, 'E':5, 'F':6, 'G':7, 'H':8, 'I':9}
df['Harm_Score'] = df['Harm_Level'].map(harm_mapping)

# 2. Advanced Aggregation for Drill-down
# ---------------------------------------------------------
unit_cat = df.groupby(['Date', 'Unit', 'Category']).agg(rpn=('Harm_Score', 'sum')).reset_index()
unit_total = unit_cat.groupby(['Date', 'Unit']).agg(total_rpn=('rpn', 'sum')).reset_index()

# 3. Calculate Kinematics (Global Unit Level)
# ---------------------------------------------------------
unit_total = unit_total.sort_values(['Unit', 'Date'])
window = 7
unit_total['Velocity'] = unit_total.groupby('Unit')['total_rpn'].transform(lambda x: x.diff(window) / window)
unit_total['Acceleration'] = unit_total.groupby('Unit')['Velocity'].transform(lambda x: x.diff(window) / window)

# --- CRITICAL FIX: REMOVE NaNs BEFORE CALCULATING LIMITS ---
unit_total = unit_total.dropna(subset=['Acceleration'])

# 4. Identify the "Problematic Category" within the unit
# ---------------------------------------------------------
latest_date = unit_total['Date'].max()
latest_stats = unit_total[unit_total['Date'] == latest_date]
top_unit_row = latest_stats.sort_values('Acceleration', ascending=False).iloc[0]
target_unit = top_unit_row['Unit']
accel_val = top_unit_row['Acceleration']

category_breakdown = unit_cat[(unit_cat['Date'] == latest_date) & (unit_cat['Unit'] == target_unit)]
top_category = category_breakdown.sort_values('rpn', ascending=False).iloc[0]['Category']

# 5. THE "APPLE-MATTE" CEO DASHBOARD
# ---------------------------------------------------------
APPLE_WHITE, APPLE_BLACK, IOS_RED, GRAY = "#F5F5F7", "#1D1D1F", "#FF3B30", "#86868B"
plt.rcParams['font.family'] = 'sans-serif'

fig = plt.figure(figsize=(14, 10), facecolor=APPLE_WHITE)
gs = gridspec.GridSpec(3, 2, height_ratios=[1, 2.5, 1], hspace=0.5)

# 1. HEADER: Clear Status for Leadership
ax_head = fig.add_subplot(gs[0, :])
ax_head.axis('off')
ax_head.text(0, 0.8, f"EXECUTIVE RISK REPORT: {target_unit}", fontsize=26, fontweight='bold', color=APPLE_BLACK)
status = "CRITICAL ACCELERATION" if accel_val > 0.4 else "GAINING MOMENTUM"
ax_head.text(0, 0.45, f"STATUS: {status}", fontsize=16, fontweight='600', color=IOS_RED)

# 2. LEFT PANEL: The Pulse (Risk Magnitude)
ax_rpn = fig.add_subplot(gs[1, 0], facecolor=APPLE_WHITE)
unit_data = unit_total[unit_total['Unit'] == target_unit] 
ax_rpn.plot(unit_data['Date'], unit_data['total_rpn'], color=APPLE_BLACK, lw=2.5)
ax_rpn.fill_between(unit_data['Date'], unit_data['total_rpn'], color=APPLE_BLACK, alpha=0.05)
ax_rpn.set_title("RISK MAGNITUDE (The Pulse)", loc='left', color=GRAY, fontsize=10, pad=15)
ax_rpn.spines[['top', 'right']].set_visible(False)
ax_rpn.tick_params(colors=GRAY, labelsize=9)

# 3. RIGHT PANEL: The Momentum (Acceleration)
ax_accel = fig.add_subplot(gs[1, 1], facecolor=APPLE_WHITE)
ax_accel.plot(unit_data['Date'], unit_data['Acceleration'], color=IOS_RED, lw=2, linestyle='--')
ax_accel.set_title("RISK MOMENTUM (The Early Warning)", loc='left', color=GRAY, fontsize=10, pad=15)
ax_accel.spines[['top', 'right']].set_visible(False)
ax_accel.tick_params(colors=GRAY, labelsize=9)
ax_accel.axhline(0, color=GRAY, lw=0.5, alpha=0.5)

# 4. BOTTOM PANEL: Plain English Strategic Insight
ax_box = fig.add_subplot(gs[2, :], facecolor='#FFFFFF')
ax_box.axis('off')
explanation = (
    f"EXECUTIVE SUMMARY:\n"
    f"The {target_unit} is experiencing a 'Risk Surge.' Acceleration indicates that risk is not just rising, \n"
    f"but the rate of growth is compounding. This is a leading indicator of systemic overwhelm.\n\n"
    f"STRATEGIC IMPACT:\n"
    f"Current safety measures are being challenged by the momentum of {top_category} incidents.\n"
    f"Immediate intervention is recommended to prevent this trend from becoming a sentinel event."
)
ax_box.text(0.02, 0.5, explanation, fontsize=12, color=APPLE_BLACK, linespacing=1.6, verticalalignment='center',
            bbox=dict(facecolor='white', edgecolor='#D2D2D7', boxstyle='round,pad=1.5'))

plt.savefig('executive_risk_dashboard.png', dpi=300, bbox_inches='tight')
print(f"Executive Dashboard successfully created for {target_unit}.")