"""Synthetic incident logs. No real patient or incident data is used anywhere."""

import numpy as np
import pandas as pd
import pytest

from risk_kinematics import HARM_LEVELS, add_harm_scores


def make_log(levels_by_day: list[list[str]], start: str = "2025-01-01") -> pd.DataFrame:
    days = pd.date_range(start, periods=len(levels_by_day), freq="D")
    rows = [
        {"Date": d, "Harm_Level": lvl}
        for d, lvls in zip(days, levels_by_day, strict=True)
        for lvl in lvls
    ]
    return add_harm_scores(pd.DataFrame(rows))


def cyclic_log() -> pd.DataFrame:
    """40 days, 1-2 events a day, levels cycling through A-I."""
    return make_log(
        [[HARM_LEVELS[(i * 7 + k * 3) % 9] for k in range(1 + i % 2)] for i in range(40)]
    )


def random_log(seed: int, days: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return make_log(
        [list(rng.choice(list(HARM_LEVELS[:5]), size=rng.integers(1, 4))) for _ in range(days)]
    )


def spike_log() -> pd.DataFrame:
    """30 quiet days (level B), then 10 days of level I."""
    return make_log([["B"]] * 30 + [["I"]] * 10)


def flat_log() -> pd.DataFrame:
    """Identical score every day: std is 0."""
    return make_log([["C"]] * 30)


@pytest.fixture
def cyclic() -> pd.DataFrame:
    return cyclic_log()
