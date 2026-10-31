"""Harm-level encoding: NCC MERP categories A (no error) to I (death).

Weights are squared ordinals so
that severe events dominate a daily sum: A=1, B=4, ... I=81.
"""

from typing import cast

import pandas as pd

HARM_LEVELS: tuple[str, ...] = tuple("ABCDEFGHI")
HARM_ORDINAL: dict[str, int] = {level: i + 1 for i, level in enumerate(HARM_LEVELS)}
HARM_WEIGHTS: dict[str, int] = {level: (i + 1) ** 2 for i, level in enumerate(HARM_LEVELS)}


def add_harm_scores(df: pd.DataFrame, column: str = "Harm_Level") -> pd.DataFrame:
    """Return a copy with ``weighted_score`` and ``raw_level`` columns.

    Unknown levels map to NaN.
    """
    out = df.copy()
    levels = cast(pd.Series, out[column])
    out["weighted_score"] = levels.map(HARM_WEIGHTS)
    out["raw_level"] = levels.map(HARM_ORDINAL)
    return out
