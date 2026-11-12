"""Generator moments, chart hand-computed cases, reproducibility (synthetic data only)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from study.sim import charts, dgm, run, shipped

PI0, W = dgm.PI0, dgm.WEIGHT_SCHEMES["squared"]


def _z(samples: np.ndarray, expected: float) -> float:
    return abs(samples.mean() - expected) / (samples.std(ddof=1) / np.sqrt(len(samples)))


def _streams(sid: str, reps: int = 300) -> list[np.ndarray]:
    sc = dgm.BY_ID[sid]
    return [dgm.simulate_stream(sc, dgm.scenario_rngs(99, 0, r)[0]) for r in range(reps)]


def test_in_control_moments_within_3_mcse() -> None:
    sc = dgm.BY_ID["IC5"]  # mu0 = 2, theta = 2
    ss = _streams("IC5")
    n = np.array([s.sum(axis=1) for s in ss])
    assert _z(n.mean(axis=1), 2.0) < 3
    assert _z(n.var(axis=1, ddof=1), sc.mu0 + sc.mu0**2 / sc.theta) < 3
    x = np.array([s @ W for s in ss])
    assert _z(x.mean(axis=1), 2.0 * (PI0 @ W)) < 3
    for lev in range(9):  # severity mix
        prop = np.array([s[:, lev].sum() / s.sum() for s in ss])
        assert _z(prop, PI0[lev]) < 3, lev


def test_poisson_scenario_has_variance_equal_to_mean() -> None:
    n = np.array([s.sum(axis=1) for s in _streams("IC6")])  # mu0 = 2, Poisson
    assert _z(n.var(axis=1, ddof=1), 2.0) < 3


def test_change_scenarios_post_tau_moments() -> None:
    t0 = dgm.TAU - 1
    s2 = np.array([s[t0:].sum(axis=1).mean() for s in _streams("S2")])
    assert _z(s2, 4.0) < 3
    sev = _streams("SEV")
    assert _z(np.array([s[t0:].sum(axis=1).mean() for s in sev]), 2.0) < 3  # constant volume
    assert _z(np.array([s[t0:, 4:].sum() / s[t0:].sum() for s in sev]), 0.30) < 3
    assert _z(np.array([s[:t0, 4:].sum() / s[:t0].sum() for s in sev]), 0.15) < 3
    rep = _streams("REP")
    assert _z(np.array([s[t0:, :4].sum(axis=1).mean() for s in rep]), 2.0 * 0.85 * 1.5) < 3
    assert _z(np.array([s[t0:, 4:].sum(axis=1).mean() for s in rep]), 2.0 * 0.15) < 3  # E-I unchanged
    r60 = dgm.mean_path(dgm.BY_ID["R60"])
    assert r60[t0] == 2.0 and abs(r60[t0 + 59] - 4.0) < 1e-12 and r60[-1] == 4.0


def test_scenario_table_has_18_and_ic5_is_core() -> None:
    assert len(dgm.SCENARIOS) == 18
    ic5 = dgm.BY_ID["IC5"]
    assert (ic5.mu0, ic5.theta) == (2.0, 2.0)


def test_replica_status_is_not_trivial() -> None:
    sc = dgm.Scenario("T", "step", 2.0, 2.0, 2.0)
    c = dgm.simulate_stream(sc, np.random.default_rng(5), n_days=300)
    s = shipped.status(c @ W, c.sum(axis=1))[2.0]
    assert {shipped.NO_DATA, shipped.WITHIN, shipped.MARGINAL, shipped.OUTSIDE} <= set(s.tolist())


# ---- charts against hand-computed cases ---------------------------------------------------------


def test_shewhart_xmr_limit() -> None:
    x1 = np.array([1.0, 3.0, 2.0, 4.0])  # mean 2.5, MR = 2,1,2 -> MRbar 5/3
    assert abs(charts.shewhart_limit(x1, 3.0) - (2.5 + 3 * (5 / 3) / 1.128)) < 1e-12


def test_ewma_path() -> None:
    z = charts.ewma_paths(np.array([10.0, 0.0, 10.0]), 0.2, 5.0)
    assert np.allclose(z, [6.0, 4.8, 0.2 * 10 + 0.8 * 4.8])


def test_cusum_path_matches_recursion() -> None:
    x = np.array([3.0, 1.0, 0.0, 5.0, 0.0, 0.0, 4.0])
    c = charts.cusum_paths(x, 2.0)  # by hand: 1, 0, 0, 3, 1, 0, 2
    assert np.allclose(c, [1, 0, 0, 3, 1, 0, 2])


def test_gap_stat() -> None:
    g = charts.gap_stat(np.array([0, 1, 0, 0, 1, 2, 0, 1]))
    assert np.array_equal(g, [-np.inf, -np.inf, -np.inf, -np.inf, -3, 0, -np.inf, -2])


def test_nb_quantile_hand_cases() -> None:
    # Poisson-like limit is not needed: NB(mean 1, size 1) is geometric, P(N<=k) = 1 - 0.5^(k+1)
    assert charts.nb_upper_quantile(1.0, 1.0, 0.75) == 1.0  # 1 - 0.25 = 0.75
    assert charts.nb_upper_quantile(1.0, 1.0, 0.76) == 2.0
    assert charts.nb_upper_quantile(0.0, 1.0, 0.99) == 0.0


def test_calibrate_threshold_toy() -> None:
    stat = np.tile(np.arange(1.0, 11.0), (3, 1))  # every row first exceeds c at day floor(c)+1
    c = charts.calibrate_threshold(stat, target=5.0)
    assert 4.0 <= c < 4.001
    assert charts.calibrate_threshold(stat, target=1.0) < 1.0  # alarm on day 1


def test_calibrated_charts_hit_target_arl_in_a_big_pool() -> None:
    rng = np.random.default_rng(3)
    fit = charts.true_fit(dgm.BY_ID["IC5"], W)
    th = charts.thresholds(fit, W, rng, reps=400, horizon=2000)
    n = dgm.draw_n(rng, np.full((400, 2000), 2.0), 2.0)
    x, ne = dgm.compound_days(rng, n, dgm.PI0, W)
    for name, stat in {
        "M3": x,
        "M4": charts.ewma_paths(x, 0.2, fit.xbar),
        "M5": charts.cusum_paths(x, fit.xbar + 0.5 * fit.sd),
    }.items():
        arl = charts._arl(np.maximum.accumulate(stat, axis=1) , th[name])
        assert 300 < arl < 450, (name, arl)  # fresh pool, ~+-10% Monte Carlo error


# ---- reproducibility ----------------------------------------------------------------------------


def test_same_seed_gives_identical_csv(tmp_path) -> None:
    args = ["--n", "4", "--n-ic5", "4", "--scenarios", "IC5,S2,SEV", "--seed", "11", "--weights-study"]
    run.main([*args, "--out", str(tmp_path / "a")])
    run.main([*args, "--out", str(tmp_path / "b")])
    for name in ("replicates.csv", "summary.csv", "weights_replicates.csv", "weights_summary.csv"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes(), name
    rep = pd.read_csv(tmp_path / "a" / "replicates.csv")
    assert set(rep["method"]) == set(run.ALL_METHODS)
    run.main(["--n", "4", "--n-ic5", "4", "--scenarios", "IC5", "--seed", "12", "--out", str(tmp_path / "c")])
    other = pd.read_csv(tmp_path / "c" / "replicates.csv")
    assert not other.equals(rep[rep.scenario == "IC5"].reset_index(drop=True))
