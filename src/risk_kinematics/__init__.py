"""Risk velocity and acceleration models over clinical risk scores."""

from risk_kinematics.harm import HARM_LEVELS, HARM_ORDINAL, HARM_WEIGHTS, add_harm_scores
from risk_kinematics.kinetics import (
    TREND_RUN_DAYS,
    KineticSeries,
    StrategicStatus,
    Tolerance,
    calculate_risk_kinetics,
    classify,
    has_rising_trend,
)

__version__ = "2.0.0"

__all__ = [
    "TREND_RUN_DAYS",
    "HARM_LEVELS",
    "HARM_ORDINAL",
    "HARM_WEIGHTS",
    "KineticSeries",
    "StrategicStatus",
    "Tolerance",
    "add_harm_scores",
    "calculate_risk_kinetics",
    "classify",
    "has_rising_trend",
]
