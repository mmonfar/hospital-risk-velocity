"""Tests for step 5 session 2 code: Poisson quantile, oracle calibration, workers, report.py."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from study.sim import charts, dgm, report, run


def test_nb_upper_quantile_poisson_limit_matches_scipy() -> None:
    for mean in (0.5, 2.0, 8.0):
        k = charts.nb_upper_quantile(mean, float("inf"), 1 - 1 / 365)
        cdf = lambda j: sum(math.exp(-mean) * mean**i / math.factorial(i) for i in range(j + 1))  # noqa: E731
        assert cdf(int(k)) >= 1 - 1 / 365 > cdf(int(k) - 1)
    # a large finite theta is close to the Poisson answer
    assert abs(charts.nb_upper_quantile(2.0, 1e6, 1 - 1 / 365) - charts.nb_upper_quantile(2.0, float("inf"), 1 - 1 / 365)) <= 1


def test_oracle_thresholds_give_arl0_near_target() -> None:
    sc = dgm.BY_ID["IC5"]
    w = dgm.WEIGHT_SCHEMES["squared"]
    fit = charts.true_fit(sc, w)
    rng = np.random.default_rng(5)
    th = charts.thresholds(fit, w, rng, ("M3", "M4", "M5"), reps=600)
    rng2 = np.random.default_rng(6)
    n = dgm.draw_n(rng2, np.full((600, 1000), fit.mean_n), fit.theta)
    x, _ = dgm.compound_days(rng2, n, fit.pi, w)
    for name, stat in {
        "M3": x,
        "M4": charts.ewma_paths(x, charts.LAMBDA, fit.xbar),
        "M5": charts.cusum_paths(x, fit.xbar + 0.5 * fit.sd),
    }.items():
        arl = charts._arl(np.maximum.accumulate(stat, axis=1), th[name])
        assert 290 < arl < 450, (name, arl)


def test_m6_is_not_in_the_compared_set_but_can_be_included(tmp_path) -> None:
    assert "M6" not in run.ALL_METHODS
    run.main(["--n", "3", "--n-ic5", "3", "--scenarios", "IC5", "--seed", "3", "--include-m6", "--out", str(tmp_path)])
    assert "M6" in set(pd.read_csv(tmp_path / "replicates.csv")["method"])


def test_workers_give_identical_csv(tmp_path) -> None:
    args = ["--n", "3", "--n-ic5", "3", "--scenarios", "IC5,S2", "--seed", "9", "--weights-study"]
    run.main([*args, "--workers", "1", "--out", str(tmp_path / "a")])
    run.main([*args, "--workers", "2", "--out", str(tmp_path / "b")])
    for name in ("replicates.csv", "summary.csv", "weights_replicates.csv", "weights_summary.csv"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes(), name


def test_report_builds_tables_and_figures(tmp_path) -> None:
    ids = ",".join([f"IC{i}" for i in range(1, 10)] + report.OOC_IDS)
    run.main(["--n", "4", "--n-ic5", "4", "--scenarios", ids, "--weights-study", "--seed", "4", "--out", str(tmp_path)])
    made = report.build(tmp_path, None)
    names = {p.name for p in made}
    assert {"table1_in_control.csv", "table2_out_of_control.csv", "table3_weights.csv", "tables.md",
            "figure1_arl0.png", "figure2_pod30.png", "figure3_stream.png"} <= names
    for p in made:
        assert p.exists() and p.stat().st_size > 0
    md = (tmp_path / "tables" / "tables.md").read_text(encoding="utf-8")
    assert "Table 1" in md and "Table 2" in md and "Table 3" in md
    t1 = pd.read_csv(tmp_path / "tables" / "table1_in_control.csv")
    assert set(t1["scenario"]) == {f"IC{i}" for i in range(1, 10)}


def test_md_table_and_formatting() -> None:
    assert report._fmt(float("nan")) == "n/a"
    assert report._with_mcse(366.4, 8.2, 0) == "366 (8)"
    out = report.md_table(pd.DataFrame({"a": [1], "b": ["x"]}))
    assert out.splitlines()[0] == "| a | b |" and out.splitlines()[2] == "| 1 | x |"
