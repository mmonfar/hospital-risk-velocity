# Addendum to RULES.md (written after seeing C1-C6, before any run of these two charts, 4 Nov 2026)

Reason: C4 (E-I count, EWMA) and C5 (total count, EWMA) each did better than the weighted scores on one kind of change. One score watches both kinds at once, so the fair question is one score against two count charts held to the same total false alarms.

- **C7, total count + E-I count.** Two EWMAs, each standardised by its known mean and SD. Alarm if the larger is above one common limit, calibrated to ARL0 365 for the pair.
- **C8, A-D count + E-I count.** As C7, on levels A-D and levels E-I, so the two channels do not share reports.
- Same seed and data as RULES.md. n = 5,000 per scenario, 10,000 for IC5, the same 10 scenarios. Plus IC5, S2, SEV, REP at n = 1,000 (IC5 2,000) under the same 10 further seeds.
- Compared with M4 and M5 under squared and linear weights in the same data. A chart counts as better only if it is higher on S2 and on SEV, and not worse on REP, each by more than 2 x the larger SD between seeds; read with ARL0 beside it.
- Expected before the run: C7 is at least as high as M4 squared on S2 and SEV, but higher on REP, because the total count reacts to extra reports. C8 reacts to REP through A-D. If this fails, it is reported as failed.
- This looks at results that were already seen, so it is exploratory and it needs replication on other generators.
