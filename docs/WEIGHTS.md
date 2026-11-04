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

The false-alarm rates are not equal. The total count chart has the strictest limit, so with equal false alarms it would detect more than it shows here; this was not measured. A smoothed total count chart was tested later: see [Counts by harm category](#counts-by-harm-category).

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

## Larger run

Added after the results above, and not planned in advance: the same code and generator, a new seed and 20 times the runs (20,000 per scenario, 40,000 for the stable ward).

| | Single-day chart | | | Smoothed chart (EWMA) | |
|---|---|---|---|---|---|
| | Total count | Arithmetic | Squared | Arithmetic | Squared |
| All incidents double | 69% | 69% | 58% | 95% | 87% |
| Same volume, more severe | 5% | 17% | 29% | 25% | 41% |
| More no-harm reports only (lower is better) | 26% | 23% | 15% | 40% | 22% |
| Average days to a false alarm, stable ward | 587 | 430 | 368 | 360 | 375 |
| False alarm within one year, stable ward | 46% | 57% | 63% | 64% | 62% |

Two monitors, smoothed chart, limits not recalibrated: squared + harm-only 88%, 59%, 23%, 274 days; arithmetic + harm-only 95%, 59%, 42%, 224 days ([`evidence/two_monitors_larger.csv`](evidence/two_monitors_larger.csv)).

- **What held.** Every ordering set before the run: arithmetic above squared above harm-only on overall rises, the reverse on severity, and the score charts above the total count on severity.
- **What moved.** The average days to a false alarm for the smoothed squared chart rose from 334 to 375. Across 10 further seeds at the original run size it ranged from 347 to 414 days, about 2.3 times its stated error, so its false-alarm figure is less exact than the first table suggests. Arithmetic and squared swapped places on this row (360 against 334, then 360 against 375): do not read a small gap there as real.
- **What it cannot show.** More runs narrow the error for this generator. They do not test its assumptions, and they say nothing new about real wards. The tool's own false-alarm numbers below were not rerun.

## Counts by harm category

Added after the results above, and not planned in advance: the usual way of watching incidents by category, on the same data as the larger run. No weights. All smoothed charts below are set to about one false alarm a year.

| Chart | All incidents double | More severe | More no-harm reports only (lower is better) | Days to a false alarm |
|---|---|---|---|---|
| Nine daily charts, one per level | 84% | 42% | 49% | 125 |
| Nine daily charts, stricter limits | 34% | 12% | 10% | 949 |
| Nine smoothed charts, one shared limit | 27% | 19% | 5% | 378 |
| Smoothed total count | 97% | 8% | 56% | 360 |
| Smoothed count of levels E-I | 64% | 64% | 8% | 354 |
| **Two smoothed counts (total + E-I), one shared limit** | 93% | 57% | 39% | 364 |
| Smoothed score, arithmetic | 95% | 25% | 40% | 360 |
| Smoothed score, squared | 87% | 41% | 22% | 375 |
| Smoothed score, harm-only | 59% | 58% | 8% | 380 |

- **A chart per level does poorly.** Either many false alarms or low detection.
- **Smoothed counts match or beat the score on one kind of change.** The total count does better than any weighting on overall rises, and is nearly blind to severity. The E-I count does better than squared weights on severity.
- **Two counts against one score.** Two counts beat squared weights on overall rises and on severity, but give more false signal from extra no-harm reports (39% against 22%). By the rule set before the run, neither is better overall. Against arithmetic weights, two counts are about equal on rises and false signal, and far better on severity.
- **What the score keeps.** One number to watch, and with squared weights less false signal from extra no-harm reports. Two counts also show which count moved; whether that helps a reviewer was not tested.
- **Limits of this result.** Exploratory: the two-count chart was chosen after seeing the other results. One generator, synthetic data, levels assumed to be graded correctly.

## False alarms of the tool

Simulated stable ward, 2 reports a day, 7-day window, squared weights. Days on average to the first alarm:

| Tolerance | Outside tolerance | Any alert (Outside or Marginal) |
|---|---|---|
| 2 sigma (default) | 80 | 32 |
| 3 sigma | 351 | 67 |

1 sigma was not tested. Release 2.1.0, before the moving-average change in the Changelog, gave 19 and 9 days at 2 sigma, and 51 and 15 days at 3 sigma. With 2.1.0 at 2 sigma, changing the weight scheme did not repair this (Outside 18-25 days under all four schemes). The current engine was tested with squared weights only. The 68%, 95% and 99.7% labels are normal-curve labels, not false-alarm rates.

## Not tested

- Real incident data. All of this is synthetic.
