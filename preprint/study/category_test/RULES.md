# Count by harm category (rules written before any run, 4 Nov 2026)

Question: how does counting incidents by harm category compare with the total count and the weighted scores? This method was not in the protocol. Nothing here changes any earlier result.

## Methods (each uses the daily report counts per level A-I; no weights)
- **C1, nine daily charts, not adjusted.** One chart per level. Alarm if any level is above its limit. Each limit is the negative binomial (1 - 1/365) quantile for that level alone, the same rule as the total count chart M7. This is the plain way to watch each category. Its false alarms add up, and they are reported as they are.
- **C2, nine daily charts, adjusted.** As C1, each limit at the (1 - 1/(9 x 365)) quantile (Bonferroni). Limits are whole numbers, so the achieved false-alarm rate may miss the target.
- **C3, E-I count, daily.** One chart on the daily count of levels E-I, same limit rule as M7.
- **C4, E-I count, EWMA.** EWMA (lambda 0.2) on the daily count of levels E-I, calibrated to ARL0 365 as M4.
- **C5, total count, EWMA.** EWMA (lambda 0.2) on the daily number of reports, calibrated to ARL0 365 as M4. This is the smoothed count chart the earlier runs did not have.
- **C6, nine EWMA charts.** One EWMA per level, each standardised by its known mean and SD. Alarm if the largest is above one common limit, calibrated to ARL0 365.

M7 is rerun as a parity gate only.

## Run
- Same code for the generator and oracle calibration, pool 1,000 x 1,000 days, as the larger run. Seed 20261104, so each replicate has the same data as the larger run, and comparison with M2, M4, M5 and M7 there is paired.
- Scenarios: IC2, IC5, IC8, S15, S2, S2-small, S2-large, R60, SEV, REP. n = 20,000; IC5 40,000.
- **Gate:** M7 first alarms must equal those of the larger run in every replicate. If not, stop and report.
- Diagnostic: IC5, S2, SEV, REP at n = 1,000 (IC5 2,000) under 10 further seeds, as for the larger run, to see the spread between seeds.

## Measures and reading
ARL0 and FA365 in IC scenarios; POD30 among runs with no earlier alarm, as before; REP is a false signal, lower is better.
- Comparisons are read with the ARL0 of each chart beside them. A gap below 2 x the SD between seeds is not read as real.
- Expected before the run: C1 has many more false alarms than one chart. Rare levels cannot alarm on a single report at this limit. C3 and C4 do well on SEV and poorly on S2. If an expectation fails, it is reported as failed.

## Limits
Exploratory, synthetic, one generator. Reporting rates and severity mix are as simulated. Levels are drawn independently given the count of the day. Oracle calibration uses the true model, so no ward could achieve it.
