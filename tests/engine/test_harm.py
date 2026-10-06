import math

import pandas as pd

from risk_kinematics import HARM_ORDINAL, HARM_WEIGHTS, add_harm_scores


def test_weights_are_squared_ordinals() -> None:
    assert HARM_WEIGHTS["A"] == 1
    assert HARM_WEIGHTS["E"] == 25
    assert HARM_WEIGHTS["I"] == 81
    assert all(HARM_WEIGHTS[k] == v**2 for k, v in HARM_ORDINAL.items())


def test_unknown_level_is_nan_and_input_is_not_mutated() -> None:
    df = pd.DataFrame({"Harm_Level": ["A", "Z"]})
    out = add_harm_scores(df)
    assert out["weighted_score"].iloc[0] == 1
    assert math.isnan(out["weighted_score"].iloc[1])
    assert list(df.columns) == ["Harm_Level"]
