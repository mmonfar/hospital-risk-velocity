# Changelog

## 2.1.0 - 2026-10-31
- New page design: left unit list with risk (sigma), header selectors (unit, period, window, tolerance), four KPI cards, trend chart with limit and "Now" marker, action card with a "Why" line, drivers, and a "How the status is decided" card.
- Momentum card fixed: it now shows "Latest day" and "trend" as two lines, so it no longer says "decreasing" beside a chart that climbed.
- Status card gives the reason (for example "Raised by the trend: it rose 6 days in a row").
- Engine moved to the `risk_kinematics/` folder; `risk_engine.py` and `ui_styles.py` removed.
- Added 224 tests (dashboard and engine). Added `CHANGELOG.md`.
- Requirements: Streamlit 1.64 or newer, pandas, numpy. Plotly no longer needed.
- Font (Plus Jakarta Sans, SIL OFL) bundled; no network call at run time.
- README: new screenshots (desktop 1440 px and phone 390 px).

## 1.0.0
- First release: harm levels, risk velocity and acceleration, sigma tolerance, Streamlit portal.
