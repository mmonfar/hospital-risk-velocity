# study/extra: post hoc work (2 November 2026)

Everything here was added AFTER the primary run, in response to the publication review. It is not part of the
pre-specified protocol. The primary results in `study/results/full/` are unchanged.

- `derived.py`: numbers computed from the existing result files (no new simulation). Output: `study/results/extra/c1_* ... c7_*`.
- `run_extra.py`: new simulations, own child key `20261102`, primary streams are never changed.
  - D1 scenario S127 (step rise of all levels by 1.267; same mean-score rise as REP: 5.85 x 0.5 / 10.96 = 0.267).
  - D2 released rule (engine 48c467f) with k tuned by bisection to ARL0 = 365 in IC5 (tuning set), checked on a fresh test set.
  - D3 trailing version (engine c3cee22), vectorised replica, gated by `study/tests/test_trailing_parity.py`.
  Output: `study/results/extra/d1_*, d2_*, d3_*`, `run_extra.log`.
- `replicas.py`: the extra replicas. `figures.py`: redrawn figures (300 dpi, 2,100 px wide).
- `make_archive.py`: builds the upload folder and zip (in `study/archive_build/`, not tracked).

Run: `python -m study.extra.derived`, `python -m study.extra.run_extra --workers 10`, `python -m study.extra.figures`.
Frozen engines: `study/engine_frozen/`. Exact package versions: `study/requirements-frozen.txt`.

## Derivative alarms (addendum 2026-11-03, exploratory)

- `derivatives.py`: V, A, J of the 7-day smoothed score (trailing form) and V-live, A-live, J-live (live form), on arrays (reps, days).
- `run_derivatives.py`: runner, own child key `20261103` (also for scenario P14). `--gate` checks M4 and M5 against the published primary run first.
  Output: `study/results/extra/e1_arl0.csv, e2_detection.csv, e3_paired_lead.csv, e_meta.json, e_notes.md, run_derivatives.log`.
- Tests: `study/tests/test_derivatives.py`. Run: `python -m study.extra.run_derivatives --workers 10 --out study/results/extra`.

## Rolling slope alarms (addendum 2, 2026-11-03, exploratory)

- `slope.py`: OLS slope of the daily score over the last 14 or 28 days (SL14, SL28). `run_slope.py`: runner, reuses the addendum 1 streams and thresholds; the gate requires V, M4, M5 to equal `e1`/`e2` exactly, else nothing is written.
- Output: `study/results/extra/f1_arl0.csv, f2_detection.csv, f3_paired_lead.csv, f_meta.json, f_notes.md, run_slope.log`. Tests: `study/tests/test_slope.py`.
- Run: `python -m study.extra.run_slope --workers 10 --out study/results/extra`.
