# Preprint package: protocol, seeds and replication code

Companion to the preprint on a monitoring rule for harm-weighted incident reports (simulation study).
All data are synthetic. Every number comes from fixed random seeds. No patient or staff data are in this folder.

## Tested engine
The engine tested in the preprint is **tag v2.1.0, commit 48c467f**. Later commits on `main` are not the tested version.
A frozen copy is in `study/engine_frozen/48c467f/`. The later trailing-average copy `c3cee22` is used only for the post hoc checks.

## What each file is
- `study/protocol_2026-10-13.md`: the protocol as fixed on 13 October 2026, before any result.
- `study/protocol_current_with_deviations.md`: the same protocol with the log of deviations (section 9).
- `study/protocol_addendum_2026-11-03.md`, `study/protocol_addendum_2_2026-11-03.md`, `study/protocol_addendum_3_2026-11-09.md`: the three addenda (the third is post hoc, a second tuning of EWMA and CUSUM).
- Seeds and settings: set in the code and the protocol (`study/sim/run.py` default seed; larger run seed 20261104, see below). Seed spreads: `study/larger_run/seed_spread.csv`, `study/category_test/seed_spread.csv`. Pinned packages: `study/requirements-frozen.txt`.
- `study/sim/`: data generator, replica of the released rule, comparison charts, measures, tables, figures.
- `study/extra/`: post hoc additions (derived numbers, extra simulations, addendum 3, figures).
- `study/tests/`: 62 tests (parity of the replica against the real engine, generator, charts, post hoc code).
- `study/larger_run/`, `study/category_test/`, `study/severity_mix/`, `study/run_length_check/`: later checks. Each has a `RULES.md` written before the run.
- `study/results/full/` and `study/results/extra/`: summaries, tables and figures. `study/results/full/tables/` holds the tables of the paper.
- `lit/`: logs of the short literature searches of 3 November 2026.
- `README_replication_package.md`: the original replication README (full detail, versions, timings).

## Not included
The large per-replicate files (`*replicates.csv`, about 20 MB) are left out to keep the repository small. They are rebuilt by the commands below with the same seed (same seed = identical files). Steps that read them (`study.extra.derived`, `study.extra.figures`, the `compare.py` scripts) need the rerun first.
The licence files are the ones in the repository root (AGPL-3.0-or-later; content CC BY-NC; see `LICENSING.md` there).

## How to rerun (from this folder, `preprint/`)
Python 3.11 with the packages in `study/requirements-frozen.txt`.
1. Tests (about 5 minutes): `python -m pytest study/tests -q`
2. Primary run (about 3 minutes of compute): `python -m study.sim.run --n 1000 --workers 12 --weights-study --out study/results/full`
   then `python -m study.sim.report --results study/results/full --sensitivity study/results/full/bootstrap_sensitivity`
3. Post hoc: `python -m study.extra.derived`, `python -m study.extra.run_extra --workers 10`, `python -m study.extra.figures`
4. Addendum 2: `python -m study.extra.run_derivatives --workers 10 --out study/results/extra`
5. Addendum 3: `python -m study.extra.run_addendum3 --workers 5 --out study/results/extra`
6. Larger run (hours): `python -m study.sim.run --n 20000 --n-ic5 40000 --seed 20261104 --workers 10 --weights-study --out study/larger_run/output`
7. Other checks: see `README_replication_package.md`, steps 8-10.
Check without running: `python -m study.sim.run --help`.
