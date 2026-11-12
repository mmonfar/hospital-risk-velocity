"""Rolling least-squares slope of the daily score as an alarm statistic (addendum 2, 2026-11-03).

slope_t = OLS slope of x on day number over the last L days up to and including day t (no future data).
Input and output shape (reps, days). Days with fewer than L days of history are NaN (never alarm).
"""

from __future__ import annotations

import numpy as np

LENGTHS = {"SL14": 14, "SL28": 28}


def rolling_slope(x: np.ndarray, length: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    n = x.shape[-1]
    k = np.arange(length) - (length - 1) / 2.0  # centred day index, oldest first
    out = np.full(x.shape, np.nan)
    if n >= length:
        acc = np.zeros(x.shape[:-1] + (n - length + 1,))
        for i in range(length):
            acc += k[i] * x[..., i : n - length + 1 + i]
        out[..., length - 1 :] = acc / (k**2).sum()
    return out


def all_slopes(x: np.ndarray) -> dict[str, np.ndarray]:
    return {name: rolling_slope(x, L) for name, L in LENGTHS.items()}
