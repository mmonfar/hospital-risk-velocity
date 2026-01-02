import pandas as pd

# ---------------------------------------------------------
# Harm Quantization
# ---------------------------------------------------------
HARM_MAPPING = {
    'A': 1, 'B': 2, 'C': 3, 'D': 4,
    'E': 5, 'F': 6, 'G': 7, 'H': 8, 'I': 9
}

HARM_LABELS = {
    1: "No Harm / Near Miss",
    2: "Minimal Harm",
    3: "Low Harm",
    4: "Moderate Harm",
    5: "Significant Harm",
    6: "Severe Harm",
    7: "Life-Threatening Harm",
    8: "Death / Sentinel Event",
    9: "Catastrophic Harm"
}

# ---------------------------------------------------------
# Data Loading & Quantization
# ---------------------------------------------------------
def load_and_quantize(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])
    df["harm_score"] = df["Harm_Level"].map(HARM_MAPPING)
    return df

# ---------------------------------------------------------
# Aggregation: Risk Position
# ---------------------------------------------------------
def aggregate_unit_daily(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["Date", "Unit"])
          .agg(total_rpn=("harm_score", "sum"))
          .reset_index()
          .sort_values(["Unit", "Date"])
    )

# ---------------------------------------------------------
# Signal Smoothing (Robust Median)
# ---------------------------------------------------------
def smooth_rpn(df: pd.DataFrame, window: int) -> pd.DataFrame:
    df = df.copy()
    df["rpn_smooth"] = (
        df.groupby("Unit")["total_rpn"]
          .transform(lambda x: x.rolling(window).median())
    )
    return df

# ---------------------------------------------------------
# Risk Kinematics
# ---------------------------------------------------------
def compute_kinematics(df: pd.DataFrame, window: int) -> pd.DataFrame:
    df = df.copy()

    df["velocity"] = (
        df.groupby("Unit")["rpn_smooth"]
          .transform(lambda x: x.diff(window) / window)
    )

    df["acceleration"] = (
        df.groupby("Unit")["velocity"]
          .transform(lambda x: x.diff(window) / window)
    )

    return df.dropna(subset=["acceleration"])

# ---------------------------------------------------------
# Hotspot Identification
# ---------------------------------------------------------
def identify_hotspot(df: pd.DataFrame) -> pd.Series:
    latest_date = df["Date"].max()
    snapshot = df[df["Date"] == latest_date]
    return snapshot.sort_values("acceleration", ascending=False).iloc[0]

# ---------------------------------------------------------
# Executive Interpretation
# ---------------------------------------------------------
def interpret_acceleration(a: float) -> str:
    if a > 0.4:
        return "CRITICAL ACCELERATION – Risk is compounding rapidly"
    elif a > 0:
        return "GAINING MOMENTUM – Risk is increasing"
    else:
        return "STABLE / DECELERATING – Risk under control"
