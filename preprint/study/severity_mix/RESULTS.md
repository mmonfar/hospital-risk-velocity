# Severity-mix and weekday check: results (4 Nov 2026)

Rules: `RULES.md` (commit 1ba1cf4); code committed before any run (182a511). Exploratory, added after the primary results, synthetic, one generator. Oracle limits. Summarised in Additional file 1, Section S8, and in the main paper.

Run: seed 20261104, n = 5,000 per scenario, 10,000 for IC5, 9 arms (11.6 min for the 8 other arms), 10 further seeds at n = 1,000, IC5 2,000 (20.9 min). Tables: `summary.csv`, `orderings.csv`, `findings.csv`, `c7_overall.csv`, `size_changes.csv`, `seed_spread.csv`.

## Gates
- **Parity passed.** BASE first alarms equal the earlier runs in 325,000 of 325,000 rows (`parity.json`).
- **Arm checks passed.** Moments: 1 of 648 beyond 3 MCSE (largest 3.25), about 2 expected by chance (`arm_checks.csv`). M7 and C5 first alarms equal across the flat mixes in IC5, S2 and SEV: 200,000 rows, 0 differ (`invariance.csv`).
- Extra check, not in the rules: BASE at the 10 seeds equals the earlier spread runs in 24 of 24 values (`seed_parity.csv`).
- All charts read in orderings were inside the ARL0 band of 310-420 days in every arm, except M7 and M1a, which are exempt. M7 was 594 days (flat), 535 (weekday). So no ordering is "Cannot say". M2 with linear weights was outside the band in BASE (427 days) and LOW (459), but it is in no ordering.

## Findings by the reading rule
| finding | verdict | cells: held / flipped / not separated |
|---|---|---|
| A. Weight trade-off (orderings 1-6) | held | 54 / 0 / 0 |
| B. Scores above the daily count chart M7 (7-11) | held | 45 / 0 / 0 |
| C. Each smoothed count against the scores (12-19) | held | 72 / 0 / 0 |
| D. Two counts against one score (20-22) | cannot say | 23 / 0 / 4 |
| E. Squared score: severity shift above no-harm rise (23) | **changed** | 5 / 3 / 1 |
| F. Released rule ARL0 below 100 days (24) | held | 9 / 0 / 0 |

"Held" means only in these arms. B is the less telling, because M7 overshoots its false-alarm target, so it is not a fair rival. C held means that each smoothed count kept its lead on its own kind of change, and not that the score did better.

**E changed.** M4 squared, POD30 in SEV against REP:

| arm | BASE | LOW | PUB | HIGH | NEAR | CD | WD-BASE | WD-PUB | WD-HIGH |
|---|---|---|---|---|---|---|---|---|---|
| SEV | 0.41 | 0.22 | 0.20 | 0.60 | 0.49 | 0.31 | 0.38 | 0.18 | 0.55 |
| REP | 0.22 | 0.34 | 0.31 | 0.16 | 0.15 | 0.32 | 0.21 | 0.30 | 0.15 |
| status | Held | Flipped | Flipped | Held | Held | Not separated | Held | Flipped | Held |

So when E-I reports are rare (5%, 2.8%), or when no-harm reports sit in C and D, the squared score reacted at least as often to 1.5 times the no-harm reports as to a doubled share of harm. These two effect sizes are choices. The signal table in the rules pointed to this before the run; the run gives its size.

**D.** C7 was not better overall in any arm (`c7_overall.csv`). Its lead on S2 was not separated in LOW, PUB and CD, and its extra false signal on REP was not separated in PUB.

## POD30 by mix, limits reset (BASE / LOW / PUB / HIGH / NEAR / CD)
| chart | S2 | SEV | REP (lower is better) |
|---|---|---|---|
| M4 squared | .87 .88 .83 .89 .79 .93 | .41 .22 .20 .60 .49 .31 | .22 .34 .31 .16 .15 .32 |
| M4 linear | .95 .95 .95 .95 .93 .96 | .24 .13 .12 .39 .34 .17 | .40 .52 .54 .27 .32 .45 |
| M4 harm-only | .60 .35 .27 .77 .60 .60 | .58 .34 .27 .78 .58 .58 | .08 .08 .08 .08 .08 .08 |
| C4 E-I count | .65 .42 .33 .82 .65 .66 | .65 .39 .32 .82 .64 .65 | .08 .07 .08 .09 .08 .08 |
| C5 total count | .97 in all | .08 in all | .55 .62 .63 .45 .55 .55 |
| C7 both counts | .93 .90 .86 .95 .93 .93 | .57 .35 .31 .76 .57 .56 | .39 .38 .34 .33 .39 .39 |

C5 in S2 and SEV is the same in all mixes by construction: daily counts do not depend on the mix. This is not evidence of robustness. For comparison, a chart with ARL0 365 alarms by chance within 30 days in about 0.08 of runs. In all, 85 POD30 values moved in size by more than 0.05 and more than 2s (`size_changes.csv`); 81 of them are from a different mix, and 4 from the weekday pattern. One of the 4 is M1a any flag (WD-PUB, REP), which is not read.

## Limits not reset (descriptive)
- **Mix.** With BASE limits, ARL0 of M4 squared was 56 days in HIGH and 81 in CD, and 1,737, 7,874 and 58,329 days in NEAR, LOW and PUB, where S2 POD30 was 0.52, 0.41 and 0.12. Values above 1,095 days extrapolate beyond follow-up. Total count charts C5 and M7 did not change. C4 moved most: ARL0 28 days in HIGH, and 102,767 and 5,474,504 days in LOW and PUB. The limits of a score or an E-I count must be set for the local mix. FA365 and POD30 for these runs are in `summary.csv`.
- **Weekday.** With limits from the stream without the pattern, in WD-BASE ARL0 fell in all charts: M7 594 to 306 days, C5 361 to 245, M2 squared 366 to 255, M4 squared 376 to 293, M5 squared 379 to 293, C4 353 to 307.
- **Weekday, limits reset.** ARL0 came back near target, and POD30 of M4 and M5 fell by at most 0.05.

## Expectations written before the run
| | expectation | result |
|---|---|---|
| 1 | Ordering 23 flips in LOW and PUB; may be not separated in CD; holds in HIGH, NEAR | **Met** |
| 2 | In LOW, PUB, M4 squared SEV near chance, 0.08-0.15; ordering 9, perhaps 10, 11, not separated | **Failed.** 0.22 and 0.20, about half of BASE but above that range; 9, 10, 11 Held. This went in favour of the score |
| 3 | In HIGH, 13 not separated; C4 above on SEV, below on REP | **Failed in part.** 13 Held (0.89 against 0.82, gap 0.07, 2s 0.02). C4 above on SEV (0.82, 0.60) and below on REP (0.09, 0.16): met |
| 4 | Limits not reset: M4 squared below 250 days in HIGH, CD; above 600 in LOW, PUB, NEAR | **Met** |
| 5 | 1, 2, 3, 5, 6 held in flat arms; 4 may be not separated in LOW, PUB | **Met.** 4 held too |
| 6 | C7 not better overall in any arm, because above M4 squared on REP | **Met, reason in part wrong.** In LOW, PUB and CD it failed on S2; in PUB the REP gap was not separated |
| 7 | 12, 15, 17 hold in flat arms | **Met** |
| 8 | M1a ARL0 below 30 days | **Met** (18-19 outside, 8-9 any flag) |
| 9 | Limits not reset for weekday: false alarms rise in all charts, most in M2 and M7; M7 ARL0 falls by more than half | **Failed in part.** All rose. M7 fell most but by 48%, not more than half. M2 squared (30%) was not above C5 (32%), though M2 linear (41%) was |
| 10 | Limits reset: POD30 falls by at most 0.05 for M4, M5, more for M2; no ordering flips | **Failed in part.** At most 0.05 for M4 and M5: met. M2 fell no more (at most 0.035 for squared). 23 is flipped in WD-PUB, as it is in PUB without the pattern; the pattern caused no new flip |

## Limits
As in `RULES.md`. M1a POD30 rests on few runs, because few are still free of an alarm at the change, so it is not read. A seed SD comes from 10 seeds at n = 1,000 and is itself uncertain. The check says nothing on real wards, on season, drift, exposure or delayed reports, or on other volumes. PUB comes from one hospital and medication errors only.
