"""Wider M.1 parity (post hoc, added 2 Nov 2026): replica vs frozen engine 48c467f.

Adds mu0 = 8; theta = 1 and Poisson; one stream of 1,215 days; and the linear, exponential and
harm-only weight schemes (zero-score days, constant stretches).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from risk_kinematics import HARM_LEVELS, add_harm_scores, calculate_risk_kinetics, classify
from risk_kinematics.kinetics import Tolerance

from study.sim import dgm, shipped

CODE = {Tolerance.NO_DATA: 0, Tolerance.WITHIN: 1, Tolerance.MARGINAL: 2, Tolerance.OUTSIDE: 3}


def engine_status(counts: np.ndarray, weights: np.ndarray, sigmas=(2.0, 3.0)) -> dict[float, np.ndarray]:
    t_n = counts.shape[0]
    dates = pd.date_range("2025-01-01", periods=t_n, freq="D")
    day, lev = np.nonzero(counts)
    reps = counts[day, lev]
    day, lev = np.repeat(day, reps), np.repeat(lev, reps)
    df = add_harm_scores(pd.DataFrame({"Date": dates[day], "Harm_Level": [HARM_LEVELS[i] for i in lev]}))
    df["weighted_score"] = weights[lev].astype(float)  # scheme under test (squared = engine default)
    upto = np.cumsum(counts.sum(axis=1))
    out = {s: np.zeros(t_n, dtype=np.int8) for s in sigmas}
    for t in range(t_n):
        if upto[t] == 0:
            continue
        k = calculate_risk_kinetics(df.iloc[: upto[t]], 7, sigmas[0])
        for s in sigmas:
            out[s][t] = CODE[classify(k.daily, k.mean, k.std, s).tolerance]
    return out


def _compare(counts: np.ndarray, weights: np.ndarray, label: str) -> None:
    real = engine_status(counts, weights)
    mine = shipped.status(counts @ weights, counts.sum(axis=1), (2.0, 3.0))
    for s in (2.0, 3.0):
        bad = np.flatnonzero(real[s] != mine[s])
        assert bad.size == 0, f"{label} k={s}: {bad.size} days differ, first day {bad[0] + 1}: engine {real[s][bad[0]]} replica {mine[s][bad[0]]}"


def _stream(mu0: float, theta: float, key: int, n_days: int, kind: str = "step") -> np.ndarray:
    sc = dgm.Scenario("PAR", kind, mu0, theta, 2.0)
    rng = np.random.default_rng(np.random.SeedSequence([5151, int(mu0 * 10), key]))
    return dgm.simulate_stream(sc, rng, n_days=n_days)


@pytest.mark.parametrize("theta", [1.0, np.inf])
def test_mu0_8_theta1_and_poisson(theta: float) -> None:
    w = dgm.WEIGHT_SCHEMES["squared"]
    for i in range(2):
        _compare(_stream(8.0, theta, i, 210), w, f"mu0=8 theta={theta} stream={i}")


def test_one_stream_of_1215_days() -> None:
    sc = dgm.BY_ID["IC5"]
    rng = np.random.default_rng(np.random.SeedSequence([5151, 1215]))
    counts = dgm.simulate_stream(sc, rng)
    assert counts.shape[0] == 1215
    _compare(counts, dgm.WEIGHT_SCHEMES["squared"], "IC5 1215 days")


@pytest.mark.parametrize("scheme", ["linear", "exponential", "harm_only"])
@pytest.mark.parametrize("mu0", [0.5, 2.0])
def test_weight_schemes(scheme: str, mu0: float) -> None:
    w = dgm.WEIGHT_SCHEMES[scheme]
    for i in range(2):
        _compare(_stream(mu0, 2.0, i, 210), w, f"{scheme} mu0={mu0} stream={i}")
