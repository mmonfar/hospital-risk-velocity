# Larger-run check (rules written before the run, 4 Nov 2026)

Question: does a larger random dataset change the results? This is a robustness check. It is apart from the paper: the frozen results in `study/results/full/` and `extra/` are not changed, and nothing here enters the paper without a separate decision.

- **Run.** Same code, generator and oracle calibration as `study/results/full/`. New seed 20261104. 20 times the replicates: n = 20,000 per scenario, 40,000 for IC5 (the frozen run has 1,000 and 2,000). All 18 scenarios and the weights study (IC5, S2, SEV, REP under 4 schemes). Output `study/larger_run/output/` (git-ignored); the summary files and the comparison are committed.
- **Compared.** ARL0 in IC scenarios; POD30 in the others. All compared methods in `summary.csv` and `weights_summary.csv`.
- **What counts as a difference.** |new - frozen| above 3 combined Monte Carlo standard errors. About 0.3% of comparisons would pass this by chance, so a few are expected.
- **What counts as a practical difference.** POD30 moves by more than 0.05, or ARL0 by more than 15%.
- **Order check.** Do these still hold, each by more than 2 standard errors of the difference, ignoring pairing: S2 arithmetic above squared above harm-only (M4); SEV harm-only above squared above arithmetic (M4); REP harm-only below squared below arithmetic (M4); S2 M4 and M5 above M7; SEV M2, M4 and M5 above M7.
- **Limit of this check.** More replicates reduce simulation noise only. They do not test other assumptions about the data, and they cannot show how the method behaves on real wards.
