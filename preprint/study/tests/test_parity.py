"""M.1 gate: the vectorised replica must give the real engine's daily status on every day."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from risk_kinematics import HARM_LEVELS, add_harm_scores, calculate_risk_kinetics, classify
from risk_kinematics.kinetics import Tolerance

from study.sim import dgm, shipped

CODE = {Tolerance.NO_DATA: 0, Tolerance.WITHIN: 1, Tolerance.MARGINAL: 2, Tolerance.OUTSIDE: 3}
N_DAYS = 210
THETAS = (1.0, 2.0, np.inf)


def engine_status(counts: np.ndarray, sigmas=(2.0, 3.0)) -> dict[float, np.ndarray]:
    t_n = counts.shape[0]
    dates = pd.date_range("2025-01-01", periods=t_n, freq="D")
    day, lev = np.nonzero(counts)
    reps = counts[day, lev]
    day, lev = np.repeat(day, reps), np.repeat(lev, reps)
    df = add_harm_scores(
        pd.DataFrame({"Date": dates[day], "Harm_Level": [HARM_LEVELS[i] for i in lev]})
    )
    upto = np.cumsum(counts.sum(axis=1))
    out = {s: np.zeros(t_n, dtype=np.int8) for s in sigmas}
    for t in range(t_n):
        if upto[t] == 0:
            continue
        sub = df.iloc[: upto[t]]
        k = calculate_risk_kinetics(sub, 7, sigmas[0])
        for s in sigmas:
            out[s][t] = CODE[classify(k.daily, k.mean, k.std, s).tolerance]
    return out


@pytest.mark.parametrize("mu0", [0.5, 2.0])
def test_replica_matches_engine_on_15_streams_all_days_both_k(mu0: float) -> None:
    w = dgm.WEIGHT_SCHEMES["squared"]
    for i in range(15):
        sc = dgm.Scenario("PAR", "step", mu0, THETAS[i % 3], 2.0)  # change inside the 210 days
        rng = np.random.default_rng(np.random.SeedSequence([4242, int(mu0 * 10), i]))
        counts = dgm.simulate_stream(sc, rng, n_days=N_DAYS)
        real = engine_status(counts)
        mine = shipped.status(counts @ w, counts.sum(axis=1), (2.0, 3.0))
        for s in (2.0, 3.0):
            bad = np.flatnonzero(real[s] != mine[s])
            assert bad.size == 0, f"mu0={mu0} stream={i} k={s} first mismatch day {bad[0] + 1}: engine {real[s][bad[0]]} replica {mine[s][bad[0]]}"
