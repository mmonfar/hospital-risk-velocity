# Replication package: monitoring rule for harm-weighted incident reports (simulation study)

All data are synthetic. Everything is generated from fixed seeds. No patient or staff data are included.

## What is in this folder
- `study/sim/`: the simulation code of the primary study (data generator, replica of the released rule, comparison charts, measures, tables, figures).
- `study/extra/`: post hoc additions made after internal review (derived numbers, extra simulations D1-D3, redrawn figures, this archive script). They are labelled post hoc.
- `study/engine_frozen/48c467f/` and `c3cee22/`: frozen copies of the monitoring engine. The primary study used 48c467f; c3cee22 is the later trailing-average version.
- `study/tests/`: 62 tests: the primary code, wider parity tests, tests of the post hoc code, the trailing-average parity, the severity-mix code and addendum 3.
- Note: three comment lines in the frozen engine copies and one line on the interpreter path in the protocols were reworded to remove internal names; no code or method text changed.
- `study/protocol_2026-10-13.md`: the protocol as fixed on 13 October 2026, before results. `study/protocol_current_with_deviations.md`: current protocol with the deviations log.
- `study/results/full/`: primary results (replicates, summaries, tables, figures). `study/results/extra/`: post hoc results and redrawn figures, and the exploratory results of the 3 November addendum (files `e1_arl0.csv`, `e2_detection.csv`, `e3_paired_lead.csv`, `e_meta.json`, `e_notes.md`).
- `study/protocol_addendum_2_2026-11-03.md`, `study/protocol_addendum_3_2026-11-09.md`: the second addendum (3 November) and the third (9 November, post hoc, a second tuning of EWMA and CUSUM; rules written before the run). Results of the third: `study/results/extra/g1_*`.
- `study/larger_run/`, `study/category_test/`, `study/severity_mix/`, `study/run_length_check/`: later checks (rules in each `RULES.md`; summaries and comparison tables are committed, the large replicate files are not).
- `study/protocol_addendum_2026-11-03.md`: the addendum on velocity, acceleration and jerk as alarms, written before those alarms were run. Its results are exploratory.
- `Additional_file_1.zip`: CSV tables (censored shares, derived tables, post hoc simulation summaries, `summary.csv`).
- `study/requirements-frozen.txt`: exact package versions.
- `lit/`: logs of the brief literature searches of 3 November 2026 for the future-direction section (title-limited, not systematic).

## How to reproduce (run from this folder)
1. Python 3.11 with the packages in `study/requirements-frozen.txt` (versions below). No other package is needed.
2. Tests: `python -m pytest study/tests -q` (about 5 to 6 minutes; the parity tests re-run the real engine every day).
3. Primary run: `python -m study.sim.run --n 1000 --workers 12 --weights-study --out study/results/full` then `python -m study.sim.report --results study/results/full --sensitivity study/results/full/bootstrap_sensitivity`.
   Compute time summed over all cells: about 3 minutes (a few minutes wall clock on 12 processes).
4. Post hoc: `python -m study.extra.derived`, `python -m study.extra.run_extra --workers 10` (about 10 seconds), `python -m study.extra.figures`.
5. Addendum of 3 November (exploratory): `python -m study.extra.run_derivatives --workers 10 --out study/results/extra` (about 5 seconds).
6. Addendum 3 (9 November, post hoc, second tuning of EWMA and CUSUM): `python -m study.extra.run_addendum3 --workers 5 --out study/results/extra`.
7. Larger run (4 November, seed 20261104, n = 20,000 per scenario, 40,000 for IC5; several hours): `python -m study.sim.run --n 20000 --n-ic5 40000 --seed 20261104 --workers 10 --weights-study --out study/larger_run/output`, then `python study/larger_run/compare.py` and `python study/larger_run/seed_spread.py <temp_dir>` (see `study/larger_run/RULES.md`).
8. Category test (counts by harm category): `python -m study.category_test.run --out study/category_test/output`, then `python study/category_test/compare.py` (needs the larger-run replicates; see `study/category_test/RULES.md`).
9. Severity mix and weekday pattern: `python -m study.severity_mix.run --out study/severity_mix/output` (about 12 minutes), then `python -m study.severity_mix.compare study/severity_mix/output study/severity_mix/output_seeds` (see `study/severity_mix/RULES.md` and `RESULTS.md`).
10. Check of the ARL0 estimator (saved runs only, after steps 7 and 8): `python study/run_length_check/check.py`. The one-sided normal run lengths (44 and 741 days) are plain arithmetic from the normal tail and need no run.
Same seed gives identical CSV files. The engine release tested is tag v2.1.0 (frozen copy `study/engine_frozen/48c467f/`); later commits on the public main branch are not the tested version.

## Versions used
Python 3.11.9, numpy 2.4.6, pandas 3.0.6 (as in `study/requirements-frozen.txt` and the paper), Pillow 12.3.0, pytest 9.1.1. Operating system: Windows 11 (64-bit). The larger run (4 November) was made with pandas 3.0.5; the results do not depend on this version.

## Licences
Code: AGPL-3.0-or-later (see `LICENSE`). Results and text: see `LICENSING.md`.
