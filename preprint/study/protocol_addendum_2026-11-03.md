# Protocol addendum: velocity, acceleration and jerk as alarms (3 November 2026)

Written and committed BEFORE any run of these alarms. It is added after the primary run and after the 2 November post hoc work, so all results are exploratory. The primary protocol (`protocol.md`), its results (`results/full/`) and the engine are not changed.

## A. Aim
The released method displays velocity and acceleration but does not alarm on them. Measure whether an alarm on the first, second or third difference of the smoothed score detects anything that a calibrated score chart does not, at the same false-alarm rate.

## D. Data-generating mechanisms
Same model, parameters and streams as the primary study, core setting (mu0 = 2, theta = 2):
- IC5 (in control), S15 (all levels 1.5x), S2 (all levels 2x), R60 (linear ramp to 2x over 60 days), SEV (severity shift), REP (reporting of levels A-D 1.5x).
- One new scenario, P14: all levels 2x for 14 days from the change day, then back to baseline. Reason: all six above are sustained, which favours charts that build up evidence. A short-lived rise is the fairest case for a difference statistic. The first design listed the six; P14 was added on 3 November, before any run.

Replicates: n = 1,000 (IC5 2,000), as in the primary study. Same root seed and stream keys, so comparisons are paired, and P14 uses its own child key.

## M. Methods
Let x_t be the daily score, w = 7. Upper one-sided alarm only: a rise is the concern.
- Smoothed score, primary form (trailing): s_t = mean of x_(t-6) ... x_t. It uses no future data and is not revised later.
- V (velocity): v_t = (s_t - s_(t-w)) / w. A (acceleration): a_t = (v_t - v_(t-w)) / w. J (jerk): j_t = (a_t - a_(t-w)) / w.
- Sensitivity form (as displayed live): s_T at the latest day is the truncated centred mean of x_(T-3) ... x_T, and earlier s values are full centred means. Each day is computed only from data up to that day. Labels V-live, A-live, J-live.
- Comparators on the same streams: M4 (EWMA) and M5 (CUSUM) as in the primary study.
- Weights: squared (released, 1 to 81) and linear (1 to 9).
- Calibration: the primary oracle method, separately per statistic and weight scheme: smallest threshold with pooled ARL0 of at least 365 days, pool of 1,000 in-control continuations of 1,000 days. First alarm counted from day 121.

## E. Estimands and performance measures
ARL0, POD14, POD30, CED, as defined in the primary protocol, with Monte Carlo standard errors and with the unconditional detection values. One addition, because it asks directly whether the statistic "captures anything":
- Paired lead: over replicates with no pre-change alarm by either chart, the share where the difference alarm fires strictly before the EWMA alarm, and the median days of lead when it does. Same against CUSUM.

## Expectations stated before the run
These are expectations, not hypotheses to defend. Report the results whichever way they fall.
1. V, A and J need more evidence per day than a chart that accumulates, so on sustained rises (S15, S2, R60) POD30 of V is lower than EWMA and CUSUM, and A and J are lower again.
2. Differencing amplifies noise: each order adds noise relative to signal, so J is expected to detect least.
3. V may do relatively better on P14 than on S2.
4. In REP, any alarm is a false signal about harm under this model.

## Parity gate
Before the full run: M4 and M5 under squared weights on S2 must reproduce the published POD30 (0.84 and 0.87) and the published ARL0 in IC5 within Monte Carlo error. If the gate fails, stop.

## Limits to state with the results
Synthetic data; one window width (w = 7); one core setting; developer-run; exploratory. A negative result applies to this form of the statistic, not to every trend rule.
