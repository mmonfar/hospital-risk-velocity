# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]
- Docs: `docs/WEIGHTS.md` shows squared and arithmetic weights side by side, with pros and cons, simulated false-alarm numbers and two monitors run together. Default weights unchanged. README: two statements corrected.
- Engine: the trend line is a trailing moving average (no line before a full window). The limit is mean + sigma x daily sd / sqrt(window) and the status z uses the same scale, so the line is over the limit exactly when the status says Outside. A status needs 3 x window days. See docs/FINDINGS.md in the clinical-platform dashboard.

## [2.1.0] - 2026-10-31
- New page design: left unit list with risk (sigma), header selectors (unit, period, window, tolerance), four KPI cards, trend chart with limit and "Now" marker, action card with a "Why" line, drivers, and a "How the status is decided" card.
- Momentum card fixed: it now shows "Latest day" and "trend" as two lines, so it no longer says "decreasing" beside a chart that climbed.
- Status card gives the reason (for example "Raised by the trend: it rose 6 days in a row").
- Page rebuilt on `view.py` and `static/style.css` (no Plotly); `charts.py` and the bundled brand folder removed. The `src/` package layout of 2.0.0 is kept.
- Test suite is now 228 tests (dashboard and engine), merged with the 2.0.0 engine tests.
- Requirements: Streamlit 1.64 or newer, pandas, numpy. Plotly no longer needed.
- Font (Plus Jakarta Sans, SIL OFL) bundled; no network call at run time.
- README: new screenshots (desktop 1440 px and phone 390 px).

## [2.0.0] - 2026-10-06

The first version stays available under the tag `v1-final`; this release supersedes it.

### Why

| First version | Problem | 2.0.0 |
|---|---|---|
| Days with no incidents were dropped from the series | The x axis was not calendar-linear. Gaps were squeezed out, and the mean, control limit, velocity and acceleration were per day with a report, not per calendar day | The series is reindexed to a complete daily calendar and an empty day counts as zero |
| The status looked only at the latest day | A unit whose trend had risen for days could read "Within tolerance" because the latest day happened to be normal | A rising-trend rule (the smoothed trend rose on each of the last 6 days) raises "Within tolerance" to "Marginal variance". It never lowers a status or overrides "Outside tolerance". The 6-day run is a run-chart convention, not yet sourced |
| The "Risk momentum" card used the latest acceleration only | It could read "Decreasing" while the trend line was still rising | The card says it describes the latest day and shows the trend state beside it; a cooling latest day on a rising trend is shown in amber, not teal |
| The data were a bundled file | The data had to be vetted and could not be varied | Data are generated from a fixed seed by `generate_incidents`, so every run is reproducible |

### Added
- Rising-trend check and marker on the chart.
- Test suite: engine (harm scores, kinetics, calendar and trend rule) and app (Streamlit AppTest, status and momentum presentation, 162 status cases across units, windows and tolerance modes).
- Installable package (`pip install -e .`) with the engine `risk_kinematics` and the app `clinical_risk_dashboard`.
- Bundled light theme and two fonts (SIL Open Font License 1.1); no external font service.
- Licence pack (AGPL-3.0-or-later, commercial licence on request, CC BY-NC content), disclaimer, independence and data notice, AI-use line.

### Changed
- Status labels use text first; colour only reinforces them. No emoji in body text.
- Directive wording is neutral and states the evidence ("the trend has risen for 6 days in a row").
- README describes the current tool, its method, parameters and limitations.

### Removed
- Root modules `risk_engine.py`, `ui_styles.py` and the bundled CSV file (replaced by the packaged engine, app and generator).

## [1.0.0]
- First release: harm levels, risk velocity and acceleration, sigma tolerance, Streamlit portal.
