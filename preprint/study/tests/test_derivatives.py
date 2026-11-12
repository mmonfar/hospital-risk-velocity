"""Tests for the derivative-alarm statistics (addendum 2026-11-03)."""

from __future__ import annotations

import numpy as np

from study.extra import derivatives as dv
from study.extra import run_derivatives as rd
from study.sim import charts, dgm

W = 7


def _slow_trailing(x: np.ndarray) -> dict[str, np.ndarray]:
    n = len(x)

    def s(t):
        return x[t - 6 : t + 1].mean()

    def v(t):
        return (s(t) - s(t - W)) / W

    def a(t):
        return (v(t) - v(t - W)) / W

    def j(t):
        return (a(t) - a(t - W)) / W

    out = {k: np.full(n, np.nan) for k in "VAJ"}
    for t in range(n):
        if t - 6 - W >= 0:
            out["V"][t] = v(t)
        if t - 6 - 2 * W >= 0:
            out["A"][t] = a(t)
        if t - 6 - 3 * W >= 0:
            out["J"][t] = j(t)
    return out


def _slow_live(x: np.ndarray, T: int) -> tuple[float, float, float]:
    """Live V, A, J at day T using only x[:T+1]."""
    x = x[: T + 1]

    def c(u):  # full centred mean, needs x[u+3] to exist
        return x[u - 3 : u + 4].mean()

    def sl(u):
        return x[u - 3 : u + 1].mean() if u == T else c(u)

    def v(u):
        return (sl(u) - c(u - W)) / W

    def a(u):
        return (v(u) - v(u - W)) / W if u != T else (v(u) - v(u - W)) / W

    def j(u):
        return (a(u) - a(u - W)) / W

    return v(T), a(T), j(T)


def test_trailing_matches_slow_loop():
    x = np.random.default_rng(1).poisson(5, size=(3, 60)).astype(float)
    fast = dv.trailing(x)
    for r in range(3):
        slow = _slow_trailing(x[r])
        for k in "VAJ":
            np.testing.assert_allclose(fast[k][r], slow[k], equal_nan=True, atol=1e-12)


def test_live_matches_slow_loop():
    x = np.random.default_rng(2).poisson(5, size=(2, 70)).astype(float)
    fast = dv.live(x)
    for r in range(2):
        for T in range(30, 70):
            v, a, j = _slow_live(x[r], T)
            assert abs(fast["V-live"][r, T] - v) < 1e-12
            assert abs(fast["A-live"][r, T] - a) < 1e-12
            assert abs(fast["J-live"][r, T] - j) < 1e-12


def test_trailing_value_ignores_later_days():
    rng = np.random.default_rng(3)
    x = rng.poisson(5, size=(1, 80)).astype(float)
    y = x.copy()
    y[:, 50:] = rng.poisson(40, size=(1, 30))
    a, b = dv.trailing(x), dv.trailing(y)
    for k in "VAJ":
        np.testing.assert_array_equal(a[k][:, :50], b[k][:, :50])


def test_live_value_ignores_later_days():
    rng = np.random.default_rng(4)
    x = rng.poisson(5, size=(1, 80)).astype(float)
    y = x.copy()
    y[:, 51:] = rng.poisson(40, size=(1, 29))
    a, b = dv.live(x), dv.live(y)
    for k in dv.STATS[3:]:
        np.testing.assert_array_equal(a[k][:, :51], b[k][:, :51])


def test_calibration_reaches_arl0_365_on_small_pool():
    rng = np.random.default_rng(5)
    n = dgm.draw_n(rng, np.full((200, 400 + rd.PAD), 2.0), 2.0)
    x, _ = dgm.compound_days(rng, n, dgm.PI0, dgm.WEIGHT_SCHEMES["squared"])
    stat = dv.for_alarm(dv.trailing(x)["V"])[:, rd.PAD :]
    c = charts.calibrate_threshold(stat)
    cm = np.maximum.accumulate(stat, axis=1)
    assert charts._arl(cm, c) >= 365.0


def test_p14_returns_to_baseline_after_14_days():
    rng = np.random.default_rng(6)
    reps = np.stack([rd.p14_stream(rng) for _ in range(300)])
    n = reps.sum(axis=2).mean(axis=0)  # mean reports per day
    during = n[dgm.TAU - 1 : dgm.TAU - 1 + rd.P14_DAYS].mean()
    before = n[: dgm.TAU - 1].mean()
    after = n[dgm.TAU - 1 + rd.P14_DAYS :].mean()
    assert abs(before - 2.0) < 0.15 and abs(after - 2.0) < 0.15 and abs(during - 4.0) < 0.5


def test_primary_scenario_table_unchanged():
    assert [s.sid for s in dgm.SCENARIOS] == [f"IC{i}" for i in range(1, 10)] + ["S15", "S2", "S2-small", "S2-large", "S2-theta1", "S2-Pois", "R60", "SEV", "REP"]
    assert "P14" not in dgm.BY_ID and len(dgm.SCENARIOS) == 18
    assert dgm.ROOT_SEED == 20261013
