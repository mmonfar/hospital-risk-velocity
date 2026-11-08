# Spec: dashboard presentation
Problem: an executive must read status, reason and next step on one page without help.
Acceptance criteria:
- DASH-1: `status_view`, `status_reason` and `momentum_lines` turn the engine result into plain words.
- DASH-2: the latest-day momentum never reads as all clear while the trend is rising.
- DASH-3: `view` builds the page parts.
- DASH-4: `app.py` only wires filters and calls.
- DASH-5: the page carries the synthetic-data and not-a-medical-device notices.
- DASH-6: the page carries the mmonfar wordmark.
Tests: `tests/app/` (`python -m pytest`).
