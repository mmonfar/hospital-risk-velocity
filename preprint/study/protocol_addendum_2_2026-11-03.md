# Protocol addendum 2: rolling linear slope as an alarm (3 November 2026)

Written and committed BEFORE any run of this alarm, and after the results of addendum 1 (`protocol_addendum_2026-11-03.md`) were known. All results are exploratory. The primary protocol, its results, addendum 1 and the engine are not changed. This is the last method added to this study: after it, results are frozen.

## A. Aim
Velocity in addendum 1 compares two adjacent 7-day means. A least-squares slope is the standard estimate of a local trend, because it uses every day in the window. Measure whether it detects more than velocity, and whether it reaches the calibrated score charts, at the same false-alarm rate.

## D. Data-generating mechanisms
As addendum 1: IC5, S15, S2, R60, SEV, REP and P14, same streams, n = 1,000 (IC5 2,000).

## M. Methods
- SL14, SL28: ordinary least-squares slope of the daily score x_t on day number, over the last 14 or 28 days up to and including day t. It uses no future data. Upper one-sided alarm only. No inference from the regression is used: the threshold is calibrated by simulation, because daily scores are skewed and zero-heavy.
- Comparators on the same streams: M4 (EWMA), M5 (CUSUM) and V from addendum 1.
- Weights: squared and linear.
- Calibration: as V in addendum 1: oracle, per statistic and weight scheme, on the core pool, smallest threshold with pooled ARL0 of at least 365 days, 1,000 continuations of 1,000 days. First alarm counted from day 121.

## E. Performance measures
ARL0, POD14, POD30, CED, unconditional detection, paired lead against EWMA and CUSUM, as addendum 1.

## Expectations stated before the run
Expectations, not hypotheses to defend. Report the results whichever way they fall.
1. SL14 or SL28 detects more than V on S2 and R60.
2. Both remain below EWMA and CUSUM on the sustained step rises S15 and S2.
3. The gap to EWMA and CUSUM is smaller on the ramp R60 than on S2.

## Gate
V, M4 and M5 must reproduce the addendum 1 values exactly on the same streams and thresholds. If not, stop.

## Limits to state with the results
Synthetic data; two window widths; one core setting; developer-run; exploratory; chosen after seeing addendum 1.
