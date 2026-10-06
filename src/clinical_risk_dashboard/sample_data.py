"""Seeded synthetic incident log for the demo dashboard.

Every row is generated here from a fixed seed. No real patient or incident data is used,
and none is shipped.

Columns: Date, Unit, Category, Harm_Level
(NCC MERP A-I). A surge of medication events in one unit over the last two weeks gives
the demo a visible signal to find.
"""

import numpy as np
import pandas as pd

from risk_kinematics import HARM_LEVELS, add_harm_scores

UNITS: tuple[str, ...] = ("CICU", "Emergency", "General Ward", "NICU", "Surgical Ward")
CATEGORIES: tuple[str, ...] = ("Equipment", "Fall", "Infection", "Medication", "Surgical")

# Most reports are no-harm, very few are severe.
_LEVEL_PROBS = np.array([0.40, 0.20, 0.14, 0.08, 0.06, 0.05, 0.04, 0.02, 0.01])

SURGE_UNIT = "CICU"
SURGE_CATEGORY = "Medication"


def generate_incidents(
    seed: int = 7,
    start: str = "2025-01-01",
    days: int = 90,
    surge_days: int = 14,
) -> pd.DataFrame:
    """A synthetic incident log with harm scores already added (``add_harm_scores``)."""
    rng = np.random.default_rng(seed)
    probs = _LEVEL_PROBS / _LEVEL_PROBS.sum()
    rows: list[dict[str, object]] = []
    for i, day in enumerate(pd.date_range(start, periods=days, freq="D")):
        for _ in range(int(rng.poisson(5.5))):
            rows.append(
                {
                    "Date": day,
                    "Unit": str(rng.choice(UNITS)),
                    "Category": str(rng.choice(CATEGORIES)),
                    "Harm_Level": str(rng.choice(HARM_LEVELS, p=probs)),
                }
            )
        if i >= days - surge_days:
            for _ in range(int(rng.integers(1, 4))):
                rows.append(
                    {
                        "Date": day,
                        "Unit": SURGE_UNIT,
                        "Category": SURGE_CATEGORY,
                        "Harm_Level": str(rng.choice(HARM_LEVELS[3:7])),
                    }
                )
    return add_harm_scores(pd.DataFrame(rows))
