# Squared or arithmetic weights: side by side

The tool keeps **squared weights** (A = 1 ... I = 81) as its default. This page does not change it, because neither scheme is best overall.

All numbers come from a simulation study on synthetic wards (2 reports a day, overdispersed counts; paper in preparation). "Arithmetic" means A = 1 ... I = 9. "Total count" means the daily number of reports with no weights: it is a different method, not arithmetic weights.

**These are research charts, not the tool's status.** Their limits were set from a fixed baseline for about one false alarm a year. For the tool's own status, see [False alarms of the tool](#false-alarms-of-the-tool).

## Results

Share of runs with an alarm within 30 days of the change, among runs with no earlier alarm (Monte Carlo error 0.01-0.02).

| | Single-day chart | | | Smoothed chart (EWMA) | |
|---|---|---|---|---|---|
| | Total count | Arithmetic | Squared | Arithmetic | Squared |
| All incidents double | 70% | 70% | 57% | 93% | 84% |
| Same volume, more severe (E-I share doubled) | 6% | 18% | 30% | 26% | 41% |
| More no-harm reports only, harm unchanged (false signal: lower is better) | 23% | 19% | 14% | 41% | 22% |
| Average days to a false alarm, stable ward | 582 | 432 | 366 | 360 | 334 |
| False alarm within one year, stable ward | 47% | 57% | 63% | 65% | 67% |

The false-alarm rates are not equal. The total count chart has the strictest limit, so with equal false alarms it would detect more than it shows here; this was not measured. No smoothed total count chart was tested.

## Pros and cons

| | Pros | Cons |
|---|---|---|
| **Arithmetic** | Best of the two at overall rises. On the single-day chart it matches the total count on a doubling and also sees severity better. | Weakest of the two on severity. On the smoothed chart it reacts most to extra no-harm reports. |
| **Squared** (default) | Better on severity. Reacts less to extra no-harm reports. | Misses more overall rises. |

The chart type matters too: smoothing gave more detection for both schemes, and also more false signal from extra no-harm reports, at limits not set to equal false alarms. The numeric weights are conventions on both sides; no source supports either set.

## Two monitors run together

Exploratory, and not part of the study's planned analysis. A pair alarms when the first of its two smoothed charts alarms. Each chart keeps the limit set for it alone, so false alarms add up. "Harm-only" gives levels A-D a weight of 0 and uses squared weights for E-I. Combined from the saved runs by [`evidence/two_monitors.py`](evidence/two_monitors.py), with no new simulation; output in [`evidence/two_monitors.csv`](evidence/two_monitors.csv).

| Smoothed chart (EWMA) | All incidents double | More severe | More no-harm reports only | Days to a false alarm | False alarm within one year |
|---|---|---|---|---|---|
| Squared alone | 84% | 41% | 22% | 334 | 67% |
| Harm-only alone | 56% | 58% | 9% | 367 | 63% |
| **Squared + harm-only** | 86% | 60% | 24% | 256 | 76% |
| Arithmetic alone | 93% | 26% | 41% | 360 | 65% |
| **Arithmetic + harm-only** | 94% | 60% | 42% | 217 | 81% |

A pair sees both overall rises and severity, at the cost of about 40-70% more false alarms than the better single chart (average days to a false alarm 256 and 217, against 367). The pairs were not recalibrated to equal false-alarm rates, so these detection figures are not a fair win over one chart.

## False alarms of the tool

Simulated stable ward, 2 reports a day, 7-day window, squared weights. Days on average to the first alarm:

| Tolerance | Outside tolerance | Any alert (Outside or Marginal) |
|---|---|---|
| 2 sigma (default) | 80 | 32 |
| 3 sigma | 351 | 67 |

1 sigma was not tested. Release 2.1.0, before the moving-average change in the Changelog, gave 19 and 9 days at 2 sigma, and 51 and 15 days at 3 sigma. With 2.1.0 at 2 sigma, changing the weight scheme did not repair this (Outside 18-25 days under all four schemes). The current engine was tested with squared weights only. The 68%, 95% and 99.7% labels are normal-curve labels, not false-alarm rates.

## Not tested

- **Count by harm category** (one chart per level, or a count of levels E-I). The usual way of reporting incidents by category was not in the study, so no advantage over it can be claimed. The nearest results differ: the total count ignores harm levels, and harm-only is still a weighted score.
- Real incident data. All of this is synthetic.
