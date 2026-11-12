# Severity-mix and weekday check (rules written before any run, 4 Nov 2026)

Question: do the orderings of the charts still hold if the severity mix differs from the one assumed, or if reports follow a weekday pattern?

This check was added after the primary results. It is exploratory and not in the protocol. Nothing here changes any earlier result, and nothing enters the paper without a separate decision.

Before these rules were committed, only the following had been done: (a) a timing pilot on the base mix only (`pilot_timing.py`, `pilot_timing.log`; n = 500), whose results were already public, and (b) a calculation on paper of mean shift / SD for each mix (table below). No other mix and no weekday stream has been simulated.

## Arms

All mixes are assumptions used in synthetic data. Levels A-I, in order. The table shows 4 decimals for display; the code builds each mix exactly (rescaled, or add-one over 633) so that it sums to 1.

| arm | A | B | C | D | E | F | G | H | I | E-I share | A-D share of mean score, squared / linear | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | .2000 | .2500 | .2500 | .1500 | .0800 | .0400 | .0200 | .0070 | .0030 | 15% | 53% / 70% | the mix of the paper; parity gate |
| LOW | .2235 | .2794 | .2794 | .1676 | .0267 | .0133 | .0067 | .0023 | .0010 | 5% | 79% / 89% | less harm: BASE with E-I rescaled to 5% and A-D rescaled to 95% |
| PUB | .3207 | .3649 | .1216 | .1643 | .0111 | .0111 | .0032 | .0016 | .0016 | 2.8% | 84% / 92% | a published mix (below) |
| HIGH | .1647 | .2059 | .2059 | .1235 | .1600 | .0800 | .0400 | .0140 | .0060 | 30% | 32% / 49% | more harm: BASE with E-I rescaled to 30% and A-D rescaled to 70% |
| NEAR | .4500 | .2500 | .1000 | .0500 | .0800 | .0400 | .0200 | .0070 | .0030 | 15% | 38% / 63% | same harm as BASE; no-harm reports mostly A and B, so they weigh little |
| CD | .0500 | .1000 | .3000 | .4000 | .0800 | .0400 | .0200 | .0070 | .0030 | 15% | 65% / 76% | same harm as BASE; no-harm reports mostly C and D, so they weigh more |
| WD-BASE, WD-PUB, WD-HIGH | as BASE, PUB, HIGH | | | | | | | | | | | weekday pattern on the base mix and on the two ends of the harm range |

**PUB.** The brain holds no published mix. One web search found one that gives every level: Aseeri M, et al. Evaluation of Medication Error Incident Reports at a Tertiary Care Hospital. Pharmacy (Basel) 2020;8(2):69, doi 10.3390/pharmacy8020069, Table 1: counts A-I 202, 230, 76, 103, 6, 6, 1, 0, 0 of 624. PUB is (count + 1) / 633: add-one, as in the Phase I fit of the protocol, so that no level has zero chance. It is one hospital, one year, voluntary reports, medication errors only. It shows that such a mix is reported, not that it is typical. Only these published totals are used.

**Left out, with reason.** A mix with more reports in G-I at the same E-I share (E-I .05, .04, .03, .02, .01; A-D as BASE): on paper its squared signals are S2 .76, SEV .33, REP .18, against .79, .30, .21 in BASE, so it adds little. Hence 5 mixes, not more.

**Weekday pattern.** Expected reports per day are multiplied by 1.2 on Monday-Friday and 0.5 on Saturday-Sunday (average 1). Day 1 is a Monday. The numbers are an assumption, not an estimate; the brain holds no source. The mix does not depend on the day. Size theta is unchanged. The change on day 181 applies on top of the pattern. Day 181 is a Saturday, a low-volume day, which may slow the first days of detection for the daily charts; this is fixed and not varied.

**Other stream features: out, and why.** Season: the result would depend on where in the season the change falls, which needs its own design. Drifting volume or exposure: a drift is itself a change, so a true alarm would need a new definition. Delayed reports: the chart would see a different stream on each day, which needs a new engine. So the check says nothing on these.

## Scenarios
IC5, S2, SEV, REP (mu0 = 2, theta = 2). Same definitions, applied to each mix:
- **S2:** volume doubles, mix unchanged.
- **SEV:** E-I share doubles at constant volume, A-D rescaled (LOW 5 to 10%, PUB 2.8 to 5.7%, HIGH 30 to 60%). The same relative shift means a different absolute shift in each mix; this is part of what is tested. HIGH SEV, at 60%, is a stress case and not a realistic ward. The mean path of SEV in every mix is that of BASE, so volume is the same to the last digit.
- **REP:** A-D reports times 1.5, E-I unchanged.

## Charts
- Scores, on the same weights as before: M2, M4, M5 with squared and with linear weights; M4 with harm-only weights, needed for the orderings.
- Counts, no weights: C4 (E-I, EWMA), C5 (total, EWMA), C7 (total + E-I, EWMA, one limit), M7 (total, daily).
- Released rule M1a (k = 2; outside, and any flag) with squared weights. It has no limit to calibrate, and it is reported as it is.

Count (frequency) charts and linear weights are different methods. They stay apart in all tables and wording.

**Limits.** Oracle, with the same pool method as the larger run and category test: 1,000 x 1,000 days, drawn from the true model of that arm, separately per scenario and weight scheme. Each arm also uses its own mix for the start value, the CUSUM reference, the score SD and the C4/C5/C7 scaling. C4, C5 and C7 use their own pool, as in the category test. M7 uses the negative binomial quantile. For weekday arms the pool has the same weekday pattern, starting on the same weekday as day 121. In weekday arms the chart itself does not change: start value, CUSUM reference and C4/C5/C7 scaling are those of the same mix without the pattern. Only the limit is recalibrated. M7 in weekday arms takes the (1 - 1/365) quantile of the pool counts, as a whole number.

**Limits not recalibrated (descriptive).** On the same data, each non-BASE mix also runs with the limits and chart settings of BASE, and each weekday arm with the limits of the same mix without the pattern. This is reported as ARL0, FA365 and POD30. Orderings are not read from it. POD30 here can rest on few runs when false alarms are many.

## Run
- New code in `study/severity_mix/`, committed before any run. `study/sim/` stays as it is.
- Seed 20261104, as the larger run. Daily counts and level draws of replicate r are the same across the flat mixes in IC5, S2 and SEV, so these are paired. REP and the weekday arms are not paired, because their daily means differ and the number of random draws changes. Nothing in the reading rule depends on pairing.
- **n = 5,000 per scenario, 10,000 for IC5.** This is the size used for C7. No larger run is done if a result is close.
- Spread between seeds: every arm, all charts, recalibrated limits, n = 1,000 (IC5 2,000), seeds 20261201-20261210, as the earlier spread runs. Each seed redraws data and pools.

## Gates, before anything is read
1. **Parity.** BASE first alarms must equal, in every replicate compared: the larger run for M1a, M2, M4, M5 and M7, on the weights above; the category test for C4 and C5; its pair run for C7. If not, stop and report. The pilot prototype matched in 26,000 of 26,000; this does not replace the gate.
2. **Arm checks.** Means and level shares of each arm within 3 MCSE of the exact mix. M7 and C5 first alarms in IC5, S2 and SEV equal across the flat mixes, because daily counts are the same; so differences there would be errors, not findings. Their sameness is not read as robustness.

## Measures and reading
ARL0 and FA365 in IC5; POD30 among runs with no earlier alarm, as before. REP is a false signal, lower is better.

Let s = the larger SD between seeds of the two values compared, in that arm and scenario, not below 0.01. For each ordering "A above B" in each arm:
- **Held:** A - B > 2s.
- **Flipped:** B - A > 2s.
- **Not separated:** neither.

ARL0 of each chart is read beside it. If a chart other than M7 or M1a has IC5 ARL0 outside 310-420 days in that arm, each of its orderings in that arm is **Cannot say**, whichever way it came out. This includes M2, whose limit can be lumpy in LOW and PUB. M7 is exempt: it overshoots (587 days in BASE) because its limit is a whole number, as already stated in the paper, and this favours the other chart in orderings 7-11, so a flip there is the more telling.

An ordering not Held in BASE at this run size is reported but not read in the other arms.

**Findings are the groups A-F below.** A finding has changed if one of its orderings Flipped in any arm. It held only if all its orderings are Held in every arm. Anything else is "cannot say". This bar is high on purpose: the expectations below already predict some results that are not separated, so "held" for a whole group may not be reached. A POD30 that moves from BASE by more than 0.05 and more than 2s, with no flip, is a change in size: reported, but it does not change the finding. Weekday arms are read the same way, and their sizes are compared with the same mix without the pattern.

All arms and orderings are reported, and none is dropped after the run. No correction for multiple comparisons; this is exploratory. Any added arm needs a new written addendum first, and is labelled as chosen after these results.

### Orderings (POD30 in BASE, larger run and category test)
**A. Weights (Table S4), M4**
1. S2: linear above squared (0.95, 0.87)
2. S2: squared above harm-only (0.87, 0.59)
3. SEV: harm-only above squared (0.58, 0.41)
4. SEV: squared above linear (0.41, 0.25)
5. REP: squared above harm-only (0.22, 0.08)
6. REP: linear above squared (0.40, 0.22)

**B. Scores against the daily count chart (Table S4), squared**
7. S2: M4 above M7 (0.87, 0.69)
8. S2: M5 above M7 (0.88, 0.69)
9. SEV: M2 above M7 (0.29, 0.05)
10. SEV: M4 above M7 (0.41, 0.05)
11. SEV: M5 above M7 (0.43, 0.05)

**C. Smoothed counts against scores (Table S5)**
12. S2: C5 above M4 squared (0.97, 0.87)
13. S2: M4 squared above C4 (0.87, 0.64)
14. SEV: C4 above M4 squared (0.64, 0.41)
15. SEV: M4 squared above C5 (0.41, 0.08)
16. REP: M4 squared above C4 (0.22, 0.08)
17. REP: C5 above M4 squared (0.56, 0.22)
18. SEV: M4 linear above C5 (0.25, 0.08)
19. REP: C5 above M4 linear (0.56, 0.40)

**D. One score against two counts**
20. S2: C7 above M4 squared (0.93, 0.87)
21. SEV: C7 above M4 squared (0.57, 0.41)
22. REP: C7 above M4 squared (0.39, 0.22)
- C7 is better overall in an arm only if 20 and 21 hold and C7 is not above M4 squared on REP by more than 2s, as in the earlier addendum. In BASE this was not met.

**E. What the squared score reacts to**
23. M4 squared: SEV above REP (0.41, 0.22). At these effect sizes, a doubled share of harm moves the score more than 1.5 times the no-harm reports. This one is new and was not tested before. The effect sizes are choices, and the paper signal table already points to its result in LOW and PUB, so the simulation adds only how large the gap is.

**F. Released rule**
24. M1a outside: IC5 ARL0 below 100 days (18 in BASE). Read directly, with no s.

## Signal on paper, before the run
Mean shift / daily SD at mu0 = 2, theta = 2. A guide for the expectations only: it ignores the shape of the distribution.

| arm | S2: squared, linear, harm-only, E-I, total | SEV: same order | REP: same order |
|---|---|---|---|
| BASE | .79 .93 .48 .51 1.00 | .30 .16 .48 .51 0 | .21 .33 0 0 .42 |
| LOW | .82 .95 .29 .31 1.00 | .13 .06 .29 .31 0 | .32 .42 0 0 .48 |
| PUB | .77 .93 .22 .24 1.00 | .10 .05 .22 .24 0 | .32 .43 0 0 .49 |
| HIGH | .82 .93 .65 .68 1.00 | .44 .27 .65 .68 0 | .13 .23 0 0 .35 |
| NEAR | .68 .89 .48 .51 1.00 | .38 .23 .48 .51 0 | .13 .28 0 0 .42 |
| CD | .89 .97 .48 .51 1.00 | .21 .10 .48 .51 0 | .29 .37 0 0 .43 |

## Expected before the run
If an expectation fails, it is reported as failed.

Against the score:
1. **Ordering 23 flips in LOW and PUB.** When harm reports are rare, the squared score reacts more to extra no-harm reports than to a doubled share of harm. It may also be not separated in CD. It holds in HIGH and NEAR.
2. In LOW and PUB, POD30 of M4 squared in SEV falls to near the chance level of about 0.08-0.15, so ordering 9 and perhaps 10 and 11 are not separated. The paper's "a total count can miss a severity shift, a score can see it" then depends on the mix.
3. In HIGH, ordering 13 is not separated (gap within 2s), while C4 stays above M4 squared on SEV and below it on REP. If so, the E-I count is as good as or better than the score on all three in that arm.
4. Without recalibration, BASE limits on M4 squared give ARL0 below 250 days in HIGH and CD, and above 600 days in LOW, PUB and NEAR. So the limits of a score must be set for the local mix.

For the score, or neutral:
5. Orderings 1, 2, 3, 5 and 6 are Held in all flat arms; 4 may be not separated in LOW and PUB, where both values are small.
6. C7 is not better overall in any arm, because it stays above M4 squared on REP.
7. Orderings 12, 15 and 17 hold in all flat arms. Total count is blind to SEV in any mix.
8. M1a ARL0 stays below 30 days in all arms.

Weekday:
9. With limits from the flat stream, false alarms rise in all charts, most in the daily charts M2 and M7. ARL0 of M7 falls by more than half.
10. With recalibrated limits, POD30 falls by no more than 0.05 for M4 and M5, more for M2, and no ordering flips.

## Limits of this check
- Exploratory, added after the results, by the authors who chose the base mix. The arms were picked with the earlier results and the paper signal sizes known.
- Synthetic, one generator, one volume (mu0 = 2, theta = 2). Levels are drawn independently given the count of the day.
- Oracle limits use the true model, so no ward could achieve them.
- It cannot show how any chart behaves on real wards or what mix a ward has. PUB comes from one hospital and medication errors only.
- It does not test season, drift, exposure, delayed reports, small wards or weights chosen by formula. If orderings hold, that means only in these arms.
