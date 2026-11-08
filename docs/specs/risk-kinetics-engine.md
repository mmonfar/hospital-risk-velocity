# Spec: risk kinetics engine
Problem: show whether harm is rising or speeding up, not only how many incidents there are.
Acceptance criteria:
- KIN-1: `add_harm_scores` weights each incident by harm level (squared ordinal).
- KIN-2: `calculate_risk_kinetics` gives a complete calendar series (empty days count as zero).
- KIN-3: it gives velocity and acceleration (differences over the window, divided by the window).
- KIN-4: it gives the limit for the chosen window and sigma.
- KIN-5: `classify` returns a `Tolerance` status.
- KIN-6: `has_rising_trend` checks a run of 6 rising days.
Tests: `tests/engine/` (`python -m pytest`).
