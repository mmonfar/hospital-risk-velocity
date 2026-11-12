# Full run: results notes (step 5 session 2, 21 Oct 2026)

Synthetic seeded data only (seed 20261013). Local only, not pushed. Status: **complete** (not partial).

## What was run
- Primary run (oracle calibration for M2-M5, M7): `python -m study.sim.run --n 1000 --n-ic5 2000 --weights-study --workers 12 --calibration oracle --out study/results/full`. 18 scenarios, n = 1,000 each, IC5 n = 2,000, 9 methods (M1a/M1b x OUTSIDE/any alert; M2, M3, M4, M5, M7; M6 dropped, protocol §9 c). Weights study: IC5, S2, SEV, REP x 4 schemes x (M1a out/any, M2, M4, M5), n = 1,000 (IC5 2,000). Wall time about 40 s on 12 workers (185 s CPU). 171,000 + 100,000 replicate rows.
- Sensitivity run (bootstrap calibration, 200 continuations per replicate): same settings, `study/results/full/bootstrap_sensitivity/`. Wall time 13 min on 12 workers, 7,405 s CPU (2.06 h; the pilot projection of 44 min CPU was low because the full run also covers the weights study at n = 1,000 with the same pool size and IC5 at n = 2,000).
- Tables and figures: `python -m study.sim.report --results study/results/full --sensitivity study/results/full/bootstrap_sensitivity`.

## Deviations from the protocol (details in protocol §9)
1. Oracle calibration is primary, bootstrap is the sensitivity analysis (protocol M.2 had them the other way round).
2. M6 g-chart is not part of the compared set (cannot reach ARL0 365 with E-I at 15% of reports). Pre-registered expectation 4 is only testable with the harm-only weights.
3. M2 and M3 are the same rule; both kept, treat as one.
4. Figures drawn with Pillow (no matplotlib in the venv). Figures follow the colour-blind-safe Okabe-Ito palette; not yet through the brand-chart pass.
5. Poisson (theta = inf) bug in the M7 NB quantile fixed before the final run.

## Key numbers
IC5 (core in control, mu0 = 2, theta = 2), 2,000 replicates:
- M1a as shipped, k = 2: ARL0 **19 days** (OUTSIDE), **9 days** (any alert); 17.8 alarm episodes per ward-year (OUTSIDE), 32.9 (any alert); 25.6 alarm-days per year (OUTSIDE). FA365 = 1.00.
- M1b as shipped, k = 3: ARL0 51 days (OUTSIDE), 15 (any alert); 6.6 episodes per year (OUTSIDE).
- Oracle-calibrated M2 / M4 / M5: ARL0 366 / 334 / 337 days (MCSE 8); about 1.0 / 1.2 / 1.4 false-alarm episodes per year.
- Every as-shipped variant alarms within the first year in essentially all replicates (FA365 0.95-1.00).
- Out of control, S2 (rate x 2): POD30 0.57 (M2), 0.84 (M4), 0.87 (M5), 0.70 (M7); CED 34 / 16 / 15 / 25 days. M1a looks fast (CED 5 days) only because it alarms before the change in 96% of replicates.
- REP (reporting rises, harm constant): POD30 0.14 (M2), 0.22 (M4), 0.21 (M5), 0.23 (M7); 0.93 for M1a OUTSIDE. Score-based charts signal on reporting alone, as expected.
- SEV (severity shift at constant volume): POD30 0.30 (M2), 0.41 (M4), 0.43 (M5), 0.06 (M7). The count chart is blind to it, as expected. Harm-only weights raise detection (M2 0.39, M4 0.58, M5 0.60).
- Weights (S2 POD30, M4): squared 0.84, linear 0.93, exponential 0.35, harm-only 0.56. The exponential scheme loses most of the power because a few high-weight reports dominate the variance. Results depend strongly on the scheme.

## Pre-registered expectations (§7), what the run shows
1. Confirmed: M1a ARL0 far below 365, any alert lower still (9 vs 19 days).
2. Confirmed for S15 and R60: M4/M5 POD30 0.50/0.49 (S15) and 0.28/0.30 (R60) against 0.28 and 0.17 for M2.
3. Partly: score charts signal in REP at 14-23% (POD30) against 30-87% in S2-type shifts; the as-shipped method signals in 93% of REP replicates, but it also alarms before the change in 97% of them.
4. M7 does not detect SEV (confirmed). M6 was not run (see deviation 2).
5. Not examined in detail here: S2-small has long CEDs for all charts (M2 83 days, M4 42, M5 39, M7 55); M6 comparison is not possible.

## Calibration sensitivity (Table S1)
Oracle ARL0 sits at 334-396 for M2-M5 in all nine IC scenarios (target 365), except M2/M3 at mu0 = 0.5, theta = 2 (451, discrete scores) and M7 (396-880: the count quantile is discrete, the smallest threshold overshoots). Per-replicate bootstrap calibration lands well above 365: IC5 643 / 649 / 731 / 734 (M2 / M3 / M4 / M5), 1,344-2,299 at mu0 = 0.5, 445-526 (M2/M3) and 480-624 (M4/M5) at mu0 = 8. Estimation error in the Phase I fit therefore makes the deployable charts less sensitive than the oracle ones: S2 POD30 falls from 0.57 / 0.84 / 0.87 to 0.45 / 0.72 / 0.77 (M2 / M4 / M5). Use oracle for comparing charts at equal ARL0, bootstrap for what a ward would get with 120 baseline days.

## Files
- `tables/table1_in_control.csv`, `table2_out_of_control.csv`, `table3_weights.csv`, `tableS1_calibration_sensitivity.csv` (long format, with MCSE); `tables/tables.md` (all tables as markdown, estimate (MCSE)).
- `figures/figure1_arl0.png` (ARL0 by method and IC scenario, log scale, 365 line, 95% bars), `figure2_pod30.png` (POD30 by method and scenario with 95% bars; for REP high is bad), `figure3_stream.png` (one S2 stream with each method's alarm days).
- `replicates.csv`, `summary.csv`, `weights_replicates.csv`, `weights_summary.csv`, `timing.csv`, `meta.json`, `run.log`; the same set under `bootstrap_sensitivity/`.

## Caveats
- M1 results assume the engine is re-run daily on all data since the start (protocol §8).
- M1a any-alert has no usable CED/POD in several scenarios (alarms before the change in 99-100% of replicates).
- Table 2 CED/POD for M1 are conditional on no pre-change alarm, a small selected group (n_eligible in the CSV).
- Discrete scores make exact ARL0 = 365 impossible for M2, M3, M7 at small mu0.
