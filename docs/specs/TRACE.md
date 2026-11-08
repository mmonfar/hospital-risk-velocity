# Spec trace

Each criterion id in `docs/specs/*.md` maps to the test that proves it. Checked by `python tests/spec_trace.py`.
GAP means no test yet. "Asserts" says in one line what the test checks.

| ID | Test | Asserts |
|---|---|---|
| KIN-1 | `tests/engine/test_harm.py::test_weights_are_squared_ordinals`, `tests/engine/test_spec_gaps.py::test_squared_weights_for_every_level` | Each level A-I gets weight n squared; scores column matches for all nine levels. |
| KIN-2 | `tests/engine/test_calendar_and_trend.py::test_zero_event_days_are_kept_as_zero`, `tests/engine/test_spec_gaps.py::test_empty_series_is_no_data_and_does_not_raise` | Days with no events appear as zero on a one-day grid; an empty log gives an empty series, no error. |
| KIN-3 | `tests/engine/test_spec_gaps.py::test_slope_velocity_is_the_daily_change_of_the_smooth_line`, `tests/engine/test_spec_gaps.py::test_jerk_acceleration_is_the_change_of_velocity`, `tests/engine/test_spec_gaps.py::test_velocity_is_divided_by_the_window` | Velocity is the change of the smooth line; acceleration is the change of velocity; both divided by the window. |
| KIN-4 | `tests/engine/test_kinetics.py::test_limit_formula_is_mean_plus_sigma_times_std_over_root_window` | The limit equals mean + sigma * std / sqrt(window). |
| KIN-5 | `tests/engine/test_kinetics.py::test_pinned_outputs`, `tests/engine/test_spec_gaps.py::test_one_data_point_is_no_data_with_no_spread` | Status is a Tolerance with pinned z and confidence; one data point gives NO_DATA. |
| KIN-6 | `tests/engine/test_spec_gaps.py::test_exactly_six_rising_days_is_flagged_and_five_is_not`, `tests/engine/test_spec_gaps.py::test_ties_do_not_count_as_rising` | Six rising steps flag; five do not; an equal step breaks the run. |
| DASH-1 | `tests/app/test_dashboard_view.py::test_every_status_has_a_reason_and_a_headline`, `tests/app/test_dashboard_view.py::test_momentum_lines_words` | Every status has a plain reason and headline; momentum words match the numbers. |
| DASH-2 | `tests/app/test_dashboard_view.py::test_momentum_lines_never_hide_a_rising_trend` | Latest day down plus rising trend shows "rising" in amber, not reassuring. |
| DASH-3 | `tests/app/test_dashboard_view.py::test_hero_and_kpi_parts_build_for_every_unit` | The hero and KPI parts build for every unit. |
| DASH-4 | `tests/app/test_app_wiring.py::test_root_app_is_only_a_launcher`, `tests/app/test_app_wiring.py::test_app_takes_words_and_page_parts_from_presentation_and_view` | Root app.py has no functions; the page file calls view/presentation and does not define their functions. Source check only. |
| DASH-5 | `tests/app/test_dashboard_app.py::test_footer_notices_are_present` | Page html has "Not a medical device" and "synthetic data". |
| DASH-6 | `tests/app/test_dashboard_app.py::test_page_carries_the_mmonfar_wordmark` | Page html has the wordmark text with its empty square element. |
