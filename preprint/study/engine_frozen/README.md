# Frozen copies of the engine (package risk-kinematics, AGPL-3.0-or-later)

- `48c467f/`: the version the study evaluated. The tests import this copy (see `study/tests/conftest.py`).
- `c3cee22/`: the later version (trailing 7-day average; limit and z on the scale of the average;
  `classify` takes a `window` argument). Used only by `study/tests/test_trailing_parity.py` and the extra runs.

Each folder holds the 5 package files as committed (`pyproject.toml`, `src/risk_kinematics/{__init__,harm,kinetics}.py`, `py.typed`), unchanged.
The licence is declared in `pyproject.toml` (`AGPL-3.0-or-later`). The files carry no other header.
