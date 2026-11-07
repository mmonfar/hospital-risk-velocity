# Spec: dashboard presentation
Problem: an executive must read status, reason and next step on one page without help.
Acceptance criteria:
- `status_view`, `status_reason` and `momentum_lines` turn the engine result into plain words; the latest-day momentum never reads as all clear while the trend is rising.
- `view` builds the page parts; `app.py` only wires filters and calls.
- The page carries the synthetic-data and not-a-medical-device notices and the mmonfar wordmark.
Tests: `tests/app/` (`python -m pytest`).
