"""Velocity, acceleration and jerk of the smoothed score as alarm statistics (addendum 2026-11-03).

All functions take arrays of shape (reps, days) and return the same shape. Days with too little
history are NaN (they can never alarm). w = 7.

Trailing form (primary): s_t = mean(x[t-6..t]); V = (s_t - s_(t-w))/w; A = (V_t - V_(t-w))/w; J likewise.
Live form (sensitivity): value at day T uses only x[..T]. s_T = mean(x[T-3..T]) (truncated centred
mean); every earlier s_u in the difference is the full centred mean(x[u-3..u+3]).
"""

from __future__ import annotations

import numpy as np

W = 7
STATS = ("V", "A", "J", "V-live", "A-live", "J-live")


def _shift(a: np.ndarray, k: int) -> np.ndarray:
    """out[..., t] = a[..., t-k]; NaN for t < k."""
    out = np.full(a.shape, np.nan)
    if k < a.shape[-1]:
        out[..., k:] = a[..., : a.shape[-1] - k]
    return out


def _window_mean(x: np.ndarray, back: int, fwd: int) -> np.ndarray:
    """out[t] = mean(x[t-back .. t+fwd]); NaN where the window is not inside the array."""
    x = np.asarray(x, dtype=float)
    n = x.shape[-1]
    c = np.concatenate([np.zeros(x.shape[:-1] + (1,)), np.cumsum(x, axis=-1)], axis=-1)
    out = np.full(x.shape, np.nan)
    width = back + fwd + 1
    t = np.arange(back, n - fwd)
    if t.size:
        out[..., t] = (c[..., t + fwd + 1] - c[..., t - back]) / width
    return out


def trailing(x: np.ndarray) -> dict[str, np.ndarray]:
    s = _window_mean(x, W - 1, 0)
    v = (s - _shift(s, W)) / W
    a = (v - _shift(v, W)) / W
    j = (a - _shift(a, W)) / W
    return {"V": v, "A": a, "J": j}


def live(x: np.ndarray) -> dict[str, np.ndarray]:
    c = _window_mean(x, 3, 3)  # full centred mean (valid only when 3 later days exist)
    sl = _window_mean(x, 3, 0)  # truncated centred mean at the latest day
    vc = (c - _shift(c, W)) / W
    ac = (vc - _shift(vc, W)) / W
    v = (sl - _shift(c, W)) / W
    a = (v - _shift(vc, W)) / W
    j = (a - _shift(ac, W)) / W
    return {"V-live": v, "A-live": a, "J-live": j}


def all_stats(x: np.ndarray) -> dict[str, np.ndarray]:
    out = trailing(x)
    out.update(live(x))
    return out


def for_alarm(a: np.ndarray) -> np.ndarray:
    """NaN (not enough history) becomes -inf so that it can never exceed a threshold."""
    return np.where(np.isnan(a), -np.inf, a)
