# Addendum 3 (post hoc), 9 November 2026: one more tuning each for EWMA (M4) and CUSUM (M5)

Status: POST HOC. Added after the plan, in response to review (the review said the two
comparators were tried with one tuning only). It is not part of the pre-specified protocol.
These values were fixed and written BEFORE the run.

Values (standard textbook ranges):
- EWMA lambda = 0.10 (primary: 0.20). Textbook range for EWMA is 0.05 to 0.25 (Montgomery,
  Introduction to Statistical Quality Control: 0.05-0.25, with 0.05, 0.10 and 0.20 the usual picks).
  0.10 is the usual choice for small shifts. A value of 0.4 was NOT chosen: it is outside that range.
- CUSUM reference value k = 0.25 SD above the baseline mean (primary: 0.5 SD). Textbook rule:
  k is half the shift to detect, in SD units; 0.25 targets a shift of 0.5 SD. The score is skewed
  and its rises in the scenarios are small in SD units, so 0.25 is the fair second choice.
  Both new tunings point the same way (more sensitive to small, sustained rises). This is the
  tuning most likely to help the comparators, so the test is hard on the author's method.

Design: scenarios S2, S15, SEV, REP, IC5. Oracle calibration only (ARL0 = 365, 1,000 x 1,000-day
pool, same seed and same pool as the primary run). No bootstrap. Same streams as the primary run
(common random numbers). n = 1,000 per scenario (IC5: 2,000), as in the primary run.
Gate: with the primary tuning, M4 and M5 must equal the primary replicates exactly, else nothing is written.
Report all results, whether they favour the comparators or the author's method.
Not tested: charts built for this score type (compound-Poisson or demerit charts).
Code: study/extra/run_addendum3.py. Output: study/results/extra/g1_*.
