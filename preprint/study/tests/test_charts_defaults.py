"""Addendum 3 (9 Nov 2026): lambda and the CUSUM reference became parameters.

With the default values, thresholds and alarms must be byte-identical to the code before the change.
GOLDEN was computed with study/sim/charts.py at commit 44a85b1 (before the change).
"""

from __future__ import annotations

import hashlib

import numpy as np

from study.sim import charts, dgm

GOLDEN = "54bab25964147546198b8562ec430a9b24b3330aa728c315814e2d13a6751582"


def _digest(**kw) -> str:
    w = dgm.WEIGHT_SCHEMES["squared"]
    fit = charts.true_fit(dgm.BY_ID["S2"], w)
    th = charts.thresholds(fit, w, np.random.default_rng(7), reps=40, horizon=300, **kw)
    rng = np.random.default_rng(8)
    n = dgm.draw_n(rng, np.full((5, 200), fit.mean_n), fit.theta)
    x, ne = dgm.compound_days(rng, n, fit.pi, w)
    al = charts.alarms(dict(th), fit, x, n, ne, **kw)
    h = hashlib.sha256(repr(sorted(th.items())).encode())
    for k in sorted(al):
        h.update(k.encode())
        h.update(np.ascontiguousarray(al[k]).tobytes())
    return h.hexdigest()


def test_default_outputs_unchanged():
    assert _digest() == GOLDEN


def test_explicit_primary_values_equal_default():
    assert _digest(lam=0.2, cusum_ref_sd=0.5) == GOLDEN


def test_other_values_change_outputs():
    assert _digest(lam=0.1, cusum_ref_sd=0.25) != GOLDEN
