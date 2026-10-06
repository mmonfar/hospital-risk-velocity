"""The demo data is generated, deterministic and carries no free text."""

from typing import cast

import pandas as pd

from clinical_risk_dashboard.sample_data import (
    CATEGORIES,
    SURGE_CATEGORY,
    SURGE_UNIT,
    UNITS,
    generate_incidents,
)
from risk_kinematics import HARM_LEVELS, HARM_WEIGHTS


def test_same_seed_same_log() -> None:
    assert generate_incidents(seed=3).equals(generate_incidents(seed=3))
    assert not generate_incidents(seed=3).equals(generate_incidents(seed=4))


def test_columns_and_domains() -> None:
    df = generate_incidents()
    assert list(df.columns) == [
        "Date",
        "Unit",
        "Category",
        "Harm_Level",
        "weighted_score",
        "raw_level",
    ]
    assert set(df["Unit"]) <= set(UNITS)
    assert set(df["Category"]) <= set(CATEGORIES)
    assert set(df["Harm_Level"]) <= set(HARM_LEVELS)
    assert df["Date"].nunique() == 90
    levels = cast(pd.Series, df["Harm_Level"])
    assert (df["weighted_score"] == levels.map(HARM_WEIGHTS)).all()


def test_surge_is_visible_in_the_last_two_weeks() -> None:
    df = generate_incidents()
    surge = (df["Unit"] == SURGE_UNIT) & (df["Category"] == SURGE_CATEGORY)
    late = df["Date"] >= df["Date"].max() - pd.Timedelta(days=13)
    per_day_late = surge[late].sum() / 14
    per_day_early = surge[~late].sum() / 76
    assert per_day_late > 2 * per_day_early
