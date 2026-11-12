"""Severity-mix check: mixes as in RULES.md, and the code reduces to the frozen code on the base mix."""

import numpy as np

from study.severity_mix import run as sm
from study.sim import charts, dgm

SQ = dgm.WEIGHT_SCHEMES["squared"]
LIN = dgm.WEIGHT_SCHEMES["linear"]


def _share_no_harm(p, w):
    return float(p[:4] @ w[:4] / (p @ w))


def test_mixes_as_in_rules():
    want = {"BASE": (0.15, 0.53, 0.70), "LOW": (0.05, 0.79, 0.89), "PUB": (0.028, 0.84, 0.92), "HIGH": (0.30, 0.32, 0.49), "NEAR": (0.15, 0.38, 0.63), "CD": (0.15, 0.65, 0.76)}
    for k, (ei, sq, lin) in want.items():
        p = sm.MIXES[k]
        assert abs(p.sum() - 1) < 1e-12
        assert abs(p[4:].sum() - ei) < 0.001
        assert abs(_share_no_harm(p, SQ) - sq) < 0.006
        assert abs(_share_no_harm(p, LIN) - lin) < 0.006


def test_week_averages_one():
    assert abs(sm.WEEK.mean() - 1) < 1e-12
    assert sm.WEEK[(dgm.TAU - 1) % 7] == 0.5  # day 181 is a Saturday


def test_base_stream_equals_frozen():
    for sid in sm.SCENARIOS:
        sc = dgm.BY_ID[sid]
        a = dgm.simulate_stream(sc, np.random.default_rng(5))
        b = sm.simulate(sc, np.random.default_rng(5), dgm.PI0, False)
        assert (a == b).all()
        assert (dgm.pi_after(sc) == sm.pi_after(sc, dgm.PI0)).all()


def test_base_fit_equals_frozen():
    sc = dgm.BY_ID["S2"]
    a, b = charts.true_fit(sc, SQ), sm.true_fit(sc, SQ, dgm.PI0)
    assert (a.mean_n, a.theta, a.xbar, a.sd) == (b.mean_n, b.theta, b.xbar, b.sd)


def test_mean_paths():
    sc = dgm.BY_ID["SEV"]
    for p in sm.MIXES.values():
        assert (sm.mean_path(sc, p, False) == dgm.mean_path(sc)).all()
    low = sm.MIXES["LOW"]
    assert abs(sm.mean_path(dgm.BY_ID["REP"], low, False)[-1] - 2 * (0.95 * 1.5 + 0.05)) < 1e-9
    wd = sm.mean_path(dgm.BY_ID["IC5"], low, True)
    assert abs(wd[:7].mean() - 2) < 1e-12 and wd[0] == 2.4 and wd[5] == 1.0


def test_pool_starts_on_day_121_weekday():
    m = sm.pool_means(dgm.BY_ID["IC5"], True, reps=2, horizon=7)
    assert m.shape == (2, 7)
    assert (m[0] == 2 * sm.WEEK[(dgm.PHASE1_DAYS + np.arange(7)) % 7]).all()


def test_sev_share_doubles():
    sc = dgm.BY_ID["SEV"]
    for p in sm.MIXES.values():
        assert abs(sm.pi_after(sc, p)[4:].sum() - 2 * p[4:].sum()) < 1e-12
