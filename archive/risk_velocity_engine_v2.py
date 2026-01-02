import matplotlib.pyplot as plt
from analytics import (
    load_and_quantize,
    aggregate_unit_daily,
    smooth_rpn,
    compute_kinematics,
    identify_hotspot,
    interpret_acceleration
)

# ---------------------------------------------------------
# Parameters
# ---------------------------------------------------------
DATA_PATH = "hospital_risk_data.csv"
WINDOW = 7
OUTPUT_PNG = "executive_risk_dashboard.png"

# ---------------------------------------------------------
# Pipeline
# ---------------------------------------------------------
df = load_and_quantize(DATA_PATH)
unit_daily = aggregate_unit_daily(df)
unit_daily = smooth_rpn(unit_daily, WINDOW)
unit_daily = compute_kinematics(unit_daily, WINDOW)

hotspot = identify_hotspot(unit_daily)
unit = hotspot["Unit"]
accel = hotspot["acceleration"]
status = interpret_acceleration(accel)

unit_df = unit_daily[unit_daily["Unit"] == unit]

# ---------------------------------------------------------
# Executive Plot
# ---------------------------------------------------------
plt.figure(figsize=(12, 6))
plt.plot(unit_df["Date"], unit_df["total_rpn"], label="Risk Magnitude", lw=2)
plt.plot(unit_df["Date"], unit_df["acceleration"], label="Risk Acceleration", lw=2, linestyle="--")

plt.axhline(0, color="gray", lw=0.5)
plt.title(f"Executive Risk Brief – {unit}\n{status}")
plt.xlabel("Date")
plt.legend()
plt.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_PNG, dpi=300)
print(f"Executive dashboard saved as {OUTPUT_PNG}")
