# Spec: risk kinetics engine
Problem: show whether harm is rising or speeding up, not only how many incidents there are.
Acceptance criteria:
- `add_harm_scores` weights each incident by harm level.
- `calculate_risk_kinetics` gives a complete calendar series (empty days count as zero), velocity, acceleration and the limit for the chosen window and sigma.
- `classify` returns a `Tolerance` status; `has_rising_trend` checks a run of 6 rising days.
Tests: `tests/engine/` (`python -m pytest`).
