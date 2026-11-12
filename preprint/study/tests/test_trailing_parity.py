"""D3 gate (post hoc, 2 Nov 2026): the trailing replica must give engine c3cee22's daily status on every day.

15 seeded streams per mu0 (0.5 and 2), theta cycling 1, 2, Poisson, 210 days, both k. Also checks that the
shipped_z helper reproduces the 48c467f OUTSIDE status.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from study.extra import replicas
from study.sim import dgm, shipped

THETAS = (1.0, 2.0, np.inf)
N_DAYS = 210


def engine_status_c3(counts: np.ndarray, sigmas=(2.0, 3.0)) -> dict[float, np.ndarray]:
    with replicas.engine("c3cee22") as rk:
        code = {rk.Tolerance.NO_DATA: 0, rk.Tolerance.WITHIN: 1, rk.Tolerance.MARGINAL: 2, rk.Tolerance.OUTSIDE: 3}
        t_n = counts.shape[0]
        dates = pd.date_range("2025-01-01", periods=t_n, freq="D")
        day, lev = np.nonzero(counts)
        reps = counts[day, lev]
        day, lev = np.repeat(day, reps), np.repeat(lev, reps)
        df = rk.add_harm_scores(pd.DataFrame({"Date": dates[day], "Harm_Level": [rk.HARM_LEVELS[i] for i in lev]}))
        upto = np.cumsum(counts.sum(axis=1))
        out = {s: np.zeros(t_n, dtype=np.int8) for s in sigmas}
        for t in range(t_n):
            if upto[t] == 0:
                continue
            k = rk.calculate_risk_kinetics(df.iloc[: upto[t]], 7, sigmas[0])
            for s in sigmas:
                out[s][t] = code[rk.classify(k.daily, k.mean, k.std, s, 7).tolerance]
        return out


@pytest.mark.parametrize("mu0", [0.5, 2.0])
def test_trailing_replica_matches_c3cee22_on_15_streams_both_k(mu0: float) -> None:
    w = dgm.WEIGHT_SCHEMES["squared"]
    for i in range(15):
        sc = dgm.Scenario("PAR", "step", mu0, THETAS[i % 3], 2.0)
        rng = np.random.default_rng(np.random.SeedSequence([8484, int(mu0 * 10), i]))
        counts = dgm.simulate_stream(sc, rng, n_days=N_DAYS)
        real = engine_status_c3(counts)
        mine = replicas.trailing_status(counts @ w, counts.sum(axis=1))
        for s in (2.0, 3.0):
            bad = np.flatnonzero(real[s] != mine[s])
            assert bad.size == 0, f"mu0={mu0} stream={i} k={s} first mismatch day {bad[0] + 1}: engine {real[s][bad[0]]} replica {mine[s][bad[0]]}"


def test_shipped_z_equals_shipped_outside() -> None:
    w = dgm.WEIGHT_SCHEMES["squared"]
    for i in range(10):
        sc = dgm.Scenario("PAR", "step", (0.5, 2.0)[i % 2], THETAS[i % 3], 2.0)
        counts = dgm.simulate_stream(sc, np.random.default_rng(np.random.SeedSequence([9, i])))
        x, n = counts @ w, counts.sum(axis=1)
        z = replicas.shipped_z(x, n)
        st = shipped.status(x, n, (2.0, 3.0, 4.5))
        for k in (2.0, 3.0, 4.5):
            assert np.array_equal(z > k, st[k] == shipped.OUTSIDE)
