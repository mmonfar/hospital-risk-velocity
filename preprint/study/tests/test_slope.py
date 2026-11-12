"""Tests for the rolling slope alarm statistics (addendum 2)."""

from __future__ import annotations

import numpy as np

from study.extra import derivatives as dv
from study.extra import run_derivatives as rd
from study.extra import slope as sl
from study.sim import charts, dgm


def test_slope_matches_polyfit():
    x = np.random.default_rng(1).poisson(6, size=(2, 60)).astype(float)
    for L in (14, 28):
        got = sl.rolling_slope(x, L)
        for r in range(2):
            for t in range(L - 1, 60):
                ref = np.polyfit(np.arange(L), x[r, t - L + 1 : t + 1], 1)[0]
                assert abs(got[r, t] - ref) < 1e-10


def test_slope_ignores_later_days():
    rng = np.random.default_rng(2)
    x = rng.poisson(5, size=(1, 90)).astype(float)
    y = x.copy()
    y[:, 60:] = rng.poisson(50, size=(1, 30))
    for L in (14, 28):
        np.testing.assert_array_equal(sl.rolling_slope(x, L)[:, :60], sl.rolling_slope(y, L)[:, :60])


def test_too_little_history_cannot_alarm():
    x = np.random.default_rng(3).poisson(5, size=(1, 40)).astype(float) * 100
    for L in (14, 28):
        s = sl.rolling_slope(x, L)
        assert np.isnan(s[:, : L - 1]).all()
        assert not (dv.for_alarm(s)[:, : L - 1] > -1e300).any()


def test_calibration_reaches_arl0_365_on_small_pool():
    rng = np.random.default_rng(5)
    n = dgm.draw_n(rng, np.full((200, 400 + rd.PAD), 2.0), 2.0)
    x, _ = dgm.compound_days(rng, n, dgm.PI0, dgm.WEIGHT_SCHEMES["squared"])
    for L in (14, 28):
        stat = dv.for_alarm(sl.rolling_slope(x, L))[:, rd.PAD :]
        c = charts.calibrate_threshold(stat)
        assert charts._arl(np.maximum.accumulate(stat, axis=1), c) >= 365.0
