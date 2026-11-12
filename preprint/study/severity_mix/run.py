"""Severity-mix and weekday check: same charts on other mixes and a weekday pattern. See RULES.md.

Run from the repo root: py -3.11 -m study.severity_mix.run --out study/severity_mix/output --arms BASE
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from study.sim import charts, dgm, measures, shipped

SCENARIOS = ("IC5", "S2", "SEV", "REP")
LAM = charts.LAMBDA
P1 = dgm.PHASE1_DAYS
W = dgm.WEIGHT_SCHEMES
WEEK = np.array([1.2, 1.2, 1.2, 1.2, 1.2, 0.5, 0.5])  # day 1 is a Monday
ALL = np.arange(9)
EI = np.arange(4, 9)
PUB_COUNTS = np.array([202, 230, 76, 103, 6, 6, 1, 0, 0], dtype=float)


def _rescale(ei: float) -> np.ndarray:
    p = dgm.PI0.copy()
    p[:4] *= (1 - ei) / dgm.PI0[:4].sum()
    p[4:] *= ei / dgm.PI0[4:].sum()
    return p


def _same_harm(no_harm: tuple[float, float, float, float]) -> np.ndarray:
    return np.concatenate((no_harm, dgm.PI0[4:]))


MIXES = {
    "BASE": dgm.PI0,
    "LOW": _rescale(0.05),
    "PUB": (PUB_COUNTS + 1) / (PUB_COUNTS.sum() + 9),
    "HIGH": _rescale(0.30),
    "NEAR": _same_harm((0.45, 0.25, 0.10, 0.05)),
    "CD": _same_harm((0.05, 0.10, 0.30, 0.40)),
}


@dataclass(frozen=True)
class Arm:
    name: str
    mix: str
    weekday: bool


ARMS = {
    **{m: Arm(m, m, False) for m in MIXES},
    **{f"WD-{m}": Arm(f"WD-{m}", m, True) for m in ("BASE", "PUB", "HIGH")},
}


def level_multiplier(sc: dgm.Scenario, pi: np.ndarray) -> np.ndarray:
    m = np.ones(9)
    if sc.kind == "sev":
        m[4:] = sc.factor
        m[:4] = (1 - sc.factor * pi[4:].sum()) / pi[:4].sum()
    elif sc.kind == "rep":
        m[:4] = sc.factor
    return m


def pi_after(sc: dgm.Scenario, pi: np.ndarray) -> np.ndarray:
    p = pi * level_multiplier(sc, pi)
    return p / p.sum()


def mean_path(sc: dgm.Scenario, pi: np.ndarray, weekday: bool) -> np.ndarray:
    """Expected reports per day. SEV keeps the mean path of BASE in every mix (RULES.md)."""
    mu = dgm.mean_path(sc)
    if sc.kind == "rep":
        mu[dgm.TAU - 1 :] = sc.mu0 * float((pi * level_multiplier(sc, pi)).sum())
    return mu * WEEK[np.arange(mu.size) % 7] if weekday else mu


def simulate(sc: dgm.Scenario, rng: np.random.Generator, pi: np.ndarray, weekday: bool) -> np.ndarray:
    """dgm.simulate_stream with the mix and weekday pattern as inputs; same order of random draws."""
    mu = mean_path(sc, pi, weekday)
    t_n = mu.size
    n = dgm.draw_n(rng, mu, sc.theta)
    day = np.repeat(np.arange(t_n), n)
    u = rng.random(day.size)
    cdf0, cdf1 = np.cumsum(pi), np.cumsum(pi_after(sc, pi))
    post = day >= dgm.TAU - 1
    lev = np.where(post, np.searchsorted(cdf1, u, side="right"), np.searchsorted(cdf0, u, side="right"))
    lev = np.minimum(lev, 8)
    return np.bincount(day * 9 + lev, minlength=t_n * 9).reshape(t_n, 9)


def true_fit(sc: dgm.Scenario, weights: np.ndarray, pi: np.ndarray) -> charts.Fit:
    """charts.true_fit with the mix as input."""
    ew = float(pi @ weights)
    vw = float(pi @ weights**2) - ew**2
    vn = sc.mu0 + (0.0 if np.isinf(sc.theta) else sc.mu0**2 / sc.theta)
    return charts.Fit(sc.mu0, sc.theta, pi, sc.mu0 * ew, float(np.sqrt(vn * ew**2 + sc.mu0 * vw)))


def pool_means(sc: dgm.Scenario, weekday: bool, reps: int = 1000, horizon: int = 1000) -> np.ndarray:
    """Pool means; with the pattern each continuation starts on the weekday of day 121."""
    if not weekday:
        return np.full((reps, horizon), sc.mu0)
    return sc.mu0 * np.broadcast_to(WEEK[(P1 + np.arange(horizon)) % 7], (reps, horizon))


def _weekday_thresholds(fit: charts.Fit, sc: dgm.Scenario, weights: np.ndarray, rng: np.random.Generator, which: tuple[str, ...]) -> dict[str, float]:
    """charts.thresholds on a pool with the weekday pattern. The chart settings stay those of the fit."""
    n = dgm.draw_n(rng, pool_means(sc, True), fit.theta)
    x, _ = dgm.compound_days(rng, n, fit.pi, weights)
    th: dict[str, float] = {}
    if "M2" in which:
        th["M2"] = float(np.quantile(x, 1 - 1 / charts.TARGET_ARL, method="inverted_cdf"))
    if "M4" in which:
        th["M4"] = charts.calibrate_threshold(charts.ewma_paths(x, LAM, fit.xbar))
    if "M5" in which:
        th["M5"] = charts.calibrate_threshold(charts.cusum_paths(x, fit.xbar + 0.5 * fit.sd))
    if "M7" in which:
        th["M7"] = float(np.quantile(n, 1 - 1 / charts.TARGET_ARL, method="inverted_cdf"))
    return th


def _count_params(sc: dgm.Scenario, pi: np.ndarray, idx: np.ndarray) -> tuple[float, float]:
    mean = float(sc.mu0 * pi[idx].sum())
    var = mean + (0.0 if np.isinf(sc.theta) else mean**2 / sc.theta)
    return mean, float(np.sqrt(var * LAM / (2 - LAM)))


def _c7(c: np.ndarray, par: dict[str, tuple[float, float]]) -> np.ndarray:
    z_all = (charts.ewma_paths(c.sum(axis=-1).astype(float), LAM, par["all"][0]) - par["all"][0]) / par["all"][1]
    z_ei = (charts.ewma_paths(c[..., 4:].sum(axis=-1).astype(float), LAM, par["ei"][0]) - par["ei"][0]) / par["ei"][1]
    return np.maximum(z_all, z_ei)


WEIGHT_CHARTS = (("squared", ("M2", "M4", "M5", "M7")), ("linear", ("M2", "M4", "M5")), ("harm_only", ("M4",)))


def limits(sc: dgm.Scenario, idx: int, arm: Arm, seed: int) -> dict:
    """Limits of all charts for this arm: same pool method and seeds as the earlier runs."""
    pi = MIXES[arm.mix]
    t: dict = {}
    for wn, which in WEIGHT_CHARTS:
        fit = true_fit(sc, W[wn], pi)
        rng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(idx, 10**9)))
        th = _weekday_thresholds(fit, sc, W[wn], rng, which) if arm.weekday else charts.thresholds(fit, W[wn], rng, which, reps=1000)
        t[wn] = (fit, th)
    par = {"all": _count_params(sc, pi, ALL), "ei": _count_params(sc, pi, EI)}
    rng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(idx, 10**9 + 7)))
    pool = rng.multinomial(dgm.draw_n(rng, pool_means(sc, arm.weekday), sc.theta), pi)
    t["par"] = par
    t["C4"] = charts.calibrate_threshold(charts.ewma_paths(pool[..., 4:].sum(axis=-1).astype(float), LAM, par["ei"][0]))
    t["C5"] = charts.calibrate_threshold(charts.ewma_paths(pool.sum(axis=-1).astype(float), LAM, par["all"][0]))
    t["C7"] = charts.calibrate_threshold(_c7(pool, par))
    return t


def _episodes(a: np.ndarray) -> int:
    return int((a & ~np.concatenate(([False], a[:-1]))).sum())


def _row(a: np.ndarray) -> tuple[int, int, int]:
    return (P1 + 1 + int(a.argmax()) if a.any() else 0, int(a.sum()), _episodes(a))


def evaluate(counts: np.ndarray, t: dict) -> dict[tuple[str, str], tuple[int, int, int]]:
    c = counts[P1:]
    n, ne = c.sum(axis=1), c[:, 4:].sum(axis=1)
    out = {}
    for wn, _ in WEIGHT_CHARTS:
        fit, th = t[wn]
        for m, a in charts.alarms(th, fit, c @ W[wn], n, ne).items():
            out[(m, "none" if m == "M7" else wn)] = _row(a)
    par = t["par"]
    out[("C4", "none")] = _row(charts.ewma_paths(ne.astype(float), LAM, par["ei"][0]) > t["C4"])
    out[("C5", "none")] = _row(charts.ewma_paths(n.astype(float), LAM, par["all"][0]) > t["C5"])
    out[("C7", "none")] = _row(_c7(c, par) > t["C7"])
    return out


def released(counts: np.ndarray) -> dict[tuple[str, str], tuple[int, int, int]]:
    st = shipped.status(counts @ W["squared"], counts.sum(axis=1), (2.0,))[2.0][P1:]
    return {("M1a_out", "squared"): _row(st == shipped.OUTSIDE), ("M1a_any", "squared"): _row(st >= shipped.MARGINAL)}


def _not_recalibrated_arm(arm: Arm) -> Arm | None:
    if arm.weekday:
        return ARMS[arm.mix]
    return None if arm.name == "BASE" else ARMS["BASE"]


def run_task(task: tuple[str, str, int, int, bool]) -> pd.DataFrame:
    arm_name, sid, n, seed, with_other_limits = task
    arm, sc, idx = ARMS[arm_name], dgm.BY_ID[sid], dgm.SCENARIO_INDEX[sid]
    pi = MIXES[arm.mix]
    t = limits(sc, idx, arm, seed)
    other = _not_recalibrated_arm(arm) if with_other_limits else None
    t2 = limits(sc, idx, other, seed) if other else None
    rows = []
    for r in range(n):
        drng, _ = dgm.scenario_rngs(seed, idx, r)
        counts = simulate(sc, drng, pi, arm.weekday)
        for (m, wn), v in {**evaluate(counts, t), **released(counts)}.items():
            rows.append((arm_name, "recalibrated", sid, wn, r, m, *v, float("nan")))
        if t2:
            for (m, wn), v in evaluate(counts, t2).items():
                rows.append((arm_name, "not_recalibrated", sid, wn, r, m, *v, float("nan")))
    return pd.DataFrame(rows, columns=["arm", "limits", "scenario", "weights", "rep", "method", "first_alarm", "alarm_days", "episodes", "revision"])


def _summary(rep: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for (arm, lim), g in rep.groupby(["arm", "limits"], sort=False):
        s = measures.summarise(g.drop(columns=["arm", "limits"]))
        s.insert(0, "limits", lim)
        s.insert(0, "arm", arm)
        parts.append(s)
    return pd.concat(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--n-ic5", type=int, default=10000)
    ap.add_argument("--seeds", default="20261104", help="comma list; several seeds write one folder each, summaries only")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--recalibrated-only", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(",")]
    arms = a.arms.split(",")
    tasks = [(arm, s, a.n_ic5 if s == "IC5" else a.n, seed, not a.recalibrated_only) for seed in seeds for arm in arms for s in SCENARIOS]
    out = Path(a.out)
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        results = list(zip(tasks, ex.map(run_task, tasks), strict=True))
    for seed in seeds:
        for arm in arms:
            rep = pd.concat(r for t, r in results if t[0] == arm and t[3] == seed)
            d = out / f"s{seed}" / arm if len(seeds) > 1 else out / arm
            d.mkdir(parents=True, exist_ok=True)
            _summary(rep).to_csv(d / "summary.csv", index=False)
            if len(seeds) == 1:
                rep.to_csv(d / "replicates.csv", index=False)
    (out / f"meta_{arms[0]}.json").write_text(json.dumps({"seeds": seeds, "arms": arms, "n": a.n, "n_ic5": a.n_ic5, "numpy": np.__version__, "pandas": pd.__version__}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
