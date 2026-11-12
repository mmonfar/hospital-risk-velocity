"""Cheap tests for the post hoc code in study/extra (2 Nov 2026)."""

from __future__ import annotations

import numpy as np

from study.extra import derived, run_extra


def test_s127_matches_rep_mean_score_rise() -> None:
    assert abs(run_extra.mean_score_rise_rep() - run_extra.S127.factor) < 5e-4


def test_primary_scenarios_are_untouched() -> None:
    from study.sim import dgm

    assert len(dgm.SCENARIOS) == 18 and "S127" not in dgm.SCENARIO_INDEX


def test_arl0_and_bisection_on_toy_data() -> None:
    rng = np.random.default_rng(1)
    z = rng.normal(size=(400, 300))
    cm = np.maximum.accumulate(z, axis=1)
    a2, _ = run_extra.arl0_at(cm, 2.0)
    a3, _ = run_extra.arl0_at(cm, 3.0)
    assert a3 > a2
    k = run_extra.tune_k(cm, lo=0.0, hi=8.0)
    assert run_extra.arl0_at(cm, k)[0] >= run_extra.TARGET > run_extra.arl0_at(cm, k - 0.05)[0]


def test_wilson_and_km() -> None:
    lo, hi = derived.wilson(1000, 1000)
    assert 0.99 < lo < 1.0 and hi == 1.0
    t = np.array([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert derived.km(t, np.ones(10))["km_median"] == 5.0
    assert derived.km(t, np.zeros(10, dtype=bool))["share_no_alarm"] == 1.0
