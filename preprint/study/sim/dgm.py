"""Seeded synthetic incident-stream generator for the ADEMP protocol (study/protocol.md, section D).

Synthetic data only. One replicate = one ward = a (days x 9) matrix of report counts per
severity level A-I. Daily count N_t ~ NB(mean m_t, size theta) (Poisson if theta is inf); each
report draws a level from the severity mix pi_t. Score x_t = sum of level weights.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PHASE1_DAYS = 120
TAU = 181  # first day of the change (1-based); days 1..120 are Phase I
MONITOR_OOC = 365
MONITOR_IC = 1095
ROOT_SEED = 20261013
RAMP_DAYS = 60

PI0 = np.array([0.20, 0.25, 0.25, 0.15, 0.08, 0.04, 0.02, 0.007, 0.003])
_I = np.arange(1, 10)
WEIGHT_SCHEMES: dict[str, np.ndarray] = {
    "squared": (_I**2).astype(float),
    "linear": _I.astype(float),
    "exponential": (2.0 ** (_I - 1)),
    "harm_only": np.array([0, 0, 0, 0, 25, 36, 49, 64, 81], dtype=float),
}


@dataclass(frozen=True)
class Scenario:
    sid: str
    kind: str  # ic | step | ramp | sev | rep
    mu0: float
    theta: float
    factor: float = 1.0

    @property
    def is_ic(self) -> bool:
        return self.kind == "ic"

    @property
    def monitor_days(self) -> int:
        return MONITOR_IC if self.is_ic else MONITOR_OOC

    @property
    def n_days(self) -> int:
        return PHASE1_DAYS + self.monitor_days


def _build_scenarios() -> list[Scenario]:
    out = []
    i = 0
    for mu in (0.5, 2.0, 8.0):
        for th in (1.0, 2.0, np.inf):
            i += 1
            out.append(Scenario(f"IC{i}", "ic", mu, th))
    out += [
        Scenario("S15", "step", 2.0, 2.0, 1.5),
        Scenario("S2", "step", 2.0, 2.0, 2.0),
        Scenario("S2-small", "step", 0.5, 2.0, 2.0),
        Scenario("S2-large", "step", 8.0, 2.0, 2.0),
        Scenario("S2-theta1", "step", 2.0, 1.0, 2.0),
        Scenario("S2-Pois", "step", 2.0, np.inf, 2.0),
        Scenario("R60", "ramp", 2.0, 2.0, 2.0),
        Scenario("SEV", "sev", 2.0, 2.0, 2.0),
        Scenario("REP", "rep", 2.0, 2.0, 1.5),
    ]
    return out


SCENARIOS: list[Scenario] = _build_scenarios()
SCENARIO_INDEX = {s.sid: i for i, s in enumerate(SCENARIOS)}
BY_ID = {s.sid: s for s in SCENARIOS}


def level_multiplier(sc: Scenario) -> np.ndarray:
    """Post-change multiplier on the per-level report intensities."""
    m = np.ones(9)
    if sc.kind == "sev":  # E-I share 15% -> 30% at constant volume
        m[4:] = sc.factor
        m[:4] = (1 - sc.factor * PI0[4:].sum()) / PI0[:4].sum()
    elif sc.kind == "rep":  # near-miss/no-harm reporting up, E-I unchanged
        m[:4] = sc.factor
    return m


def pi_after(sc: Scenario) -> np.ndarray:
    p = PI0 * level_multiplier(sc)
    return p / p.sum()


def mean_path(sc: Scenario, n_days: int | None = None) -> np.ndarray:
    """Expected number of reports per day (day 1..n_days)."""
    t = np.arange(1, (n_days or sc.n_days) + 1)
    mu = np.full(t.size, sc.mu0, dtype=float)
    if sc.kind == "step":
        mu[t >= TAU] = sc.mu0 * sc.factor
    elif sc.kind == "ramp":
        frac = np.clip((t - TAU) / (RAMP_DAYS - 1), 0.0, 1.0)
        mu = sc.mu0 * (1 + frac * (sc.factor - 1))
    elif sc.kind in ("sev", "rep"):
        mu[t >= TAU] = sc.mu0 * float((PI0 * level_multiplier(sc)).sum())
    return mu


def draw_n(rng: np.random.Generator, mean: np.ndarray, theta: float) -> np.ndarray:
    """Negative-binomial counts with the given mean and size theta (Poisson if inf)."""
    mean = np.asarray(mean, dtype=float)
    if np.isinf(theta):
        return rng.poisson(mean)
    return rng.negative_binomial(theta, theta / (theta + mean))


def _levels(rng: np.random.Generator, total: int, pi: np.ndarray) -> np.ndarray:
    lev = np.searchsorted(np.cumsum(pi), rng.random(total), side="right")
    return np.minimum(lev, 8)


def simulate_stream(sc: Scenario, rng: np.random.Generator, n_days: int | None = None) -> np.ndarray:
    """Return an int array (n_days, 9) of report counts per level per day."""
    mu = mean_path(sc, n_days)
    t_n = mu.size
    n = draw_n(rng, mu, sc.theta)
    day = np.repeat(np.arange(t_n), n)
    u = rng.random(day.size)
    cdf0, cdf1 = np.cumsum(PI0), np.cumsum(pi_after(sc))
    post = day >= TAU - 1
    lev = np.where(post, np.searchsorted(cdf1, u, side="right"), np.searchsorted(cdf0, u, side="right"))
    lev = np.minimum(lev, 8)
    return np.bincount(day * 9 + lev, minlength=t_n * 9).reshape(t_n, 9)


def compound_days(
    rng: np.random.Generator, n: np.ndarray, pi: np.ndarray, weights: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Daily score and E-I report count for an array of daily report counts n (any shape)."""
    flat = n.ravel()
    day = np.repeat(np.arange(flat.size), flat)
    lev = _levels(rng, day.size, pi)
    x = np.bincount(day, weights=weights[lev], minlength=flat.size)
    ne = np.bincount(day[lev >= 4], minlength=flat.size)
    return x.reshape(n.shape), ne.reshape(n.shape)


def scenario_rngs(seed: int, idx: int, rep: int) -> tuple[np.random.Generator, np.random.Generator]:
    """(data rng, calibration rng) for scenario index idx and replicate rep.

    Equivalent to SeedSequence(seed).spawn(18)[idx].spawn(n)[rep].spawn(2), built directly so
    replicate r has the same stream whatever n is.
    """

    def mk(k: int) -> np.random.Generator:
        return np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(idx, rep, k)))

    return mk(0), mk(1)
