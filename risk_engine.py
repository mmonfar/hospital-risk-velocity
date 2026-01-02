import pandas as pd
import numpy as np

def calculate_risk_kinetics(df_f, window, sigma_val):
    """
    Translates categorical harm data into kinetic time-series derivatives.
    """
    # 1. Aggregation & Weighting logic
    daily = df_f.groupby('Date').agg({'weighted_score': 'sum', 'raw_level': 'mean'}).reset_index()
    
    # 2. Kinetic Derivatives (Velocity & Acceleration)
    daily['smooth'] = daily['weighted_score'].rolling(window, center=True, min_periods=1).mean()
    daily['velocity'] = daily['smooth'].diff(window) / window
    daily['acceleration'] = daily['velocity'].diff(window) / window

    # 3. Statistical Control Limits
    mean_val = daily['weighted_score'].mean()
    std_val = daily['weighted_score'].std()
    ucl_value = mean_val + (sigma_val * std_val)
    
    return daily, mean_val, std_val, ucl_value

def get_strategic_status(daily, mean_val, std_val, sigma_val):
    """
    Determines the executive directive based on risk appetite thresholds.
    """
    confidence_levels = {1: "68%", 2: "95%", 3: "99.7%"}
    conf_pct = confidence_levels.get(sigma_val, "95%")

    if not daily.dropna().empty:
        latest = daily.dropna().iloc[-1]
        z_score = (latest['weighted_score'] - mean_val) / std_val
        
        if z_score > sigma_val:
            status, color = "OUTSIDE TOLERANCE", "#FF3B30"
            prompt = f"🔴 ALERT: Risk exceeds {conf_pct} stability threshold. Immediate intervention required."
        elif z_score > (sigma_val * 0.7):
            status, color = "MARGINAL VARIANCE", "#FF9500"
            prompt = "🟡 WATCH: Risk trending toward upper limit. Brief unit leads on preventative measures."
        else:
            status, color = "WITHIN TOLERANCE", "#28A745"
            prompt = "🟢 STABLE: Risk levels are within normal historical variations."
            
        return z_score, status, color, prompt, conf_pct
    
    return 0, "NO DATA", "#86868B", "Check date filters.", "N/A"