"""App-level tests with Streamlit's AppTest: the page renders and shows the engine's status."""

from pathlib import Path
from typing import cast

import pandas as pd
import pytest
from clinical_risk_dashboard import presentation
from clinical_risk_dashboard.sample_data import UNITS, generate_incidents
from risk_kinematics import StrategicStatus, calculate_risk_kinetics, classify
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"
SIGMAS = {"1σ  Zero tolerance": 1, "2σ  Standard": 2, "3σ  Critical only": 3}


def run(at: AppTest | None = None) -> AppTest:
    at = at or AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def page_html(at: AppTest) -> str:
    return "\n".join(str(m.value) for m in at.markdown)


def engine(unit: str | None, window: int, sigma: int) -> StrategicStatus:
    df = generate_incidents()
    if unit is not None:
        df = cast(pd.DataFrame, df[df["Unit"] == unit])
    k = calculate_risk_kinetics(df, window, sigma)
    return classify(k.daily, k.mean, k.std, sigma)


@pytest.fixture(scope="module")
def default_run() -> AppTest:
    return run()


def test_opens_on_the_unit_that_needs_attention(default_run: AppTest) -> None:
    z = {u: engine(u, 7, 2).z_score for u in UNITS}
    assert default_run.radio(key="scope_nav").value == max(z, key=lambda u: z[u])


def test_page_has_the_four_questions_and_the_trend_chart(default_run: AppTest) -> None:
    html = page_html(default_run)
    for text in ("Is it good or bad?", "What do we do?", "Why?", "How the status is decided"):
        assert text in html
    assert 'class="trend"' in html
    assert 'class="limit"' in html
    assert 'class="zone"' in html
    assert "Now:" in html


def test_status_card_shows_the_engine_status_and_a_reason(default_run: AppTest) -> None:
    status = engine("CICU", 7, 2)
    html = page_html(default_run)
    assert status.tolerance.value.capitalize() in html
    assert presentation.status_reason(status, 2) in html
    assert presentation.status_view(status).directive in html


def test_momentum_names_both_the_latest_day_and_the_window_trend(default_run: AppTest) -> None:
    html = page_html(default_run)
    assert "Latest day:" in html
    assert "7-day trend:" in html


def test_footer_notices_are_present(default_run: AppTest) -> None:
    html = page_html(default_run)
    assert "Not a medical device" in html
    assert "AGPL-3.0" in html
    assert "CC BY-NC 4.0" in html
    assert "synthetic data" in html.lower()


@pytest.mark.parametrize(
    ("sigma_label", "window"), [("1σ  Zero tolerance", 3), ("3σ  Critical only", 15)]
)
def test_status_follows_controls(sigma_label: str, window: int) -> None:
    at = run()
    at.selectbox(key="window").set_value(f"{window} days")
    at.selectbox(key="tolerance").set_value(sigma_label)
    run(at)
    unit = at.radio(key="scope_nav").value
    expected = engine(unit, window, SIGMAS[sigma_label]).tolerance
    assert expected.value.capitalize() in page_html(at)


def test_header_unit_and_nav_stay_in_step() -> None:
    at = run()
    at.selectbox(key="scope_hdr").set_value("Emergency")
    run(at)
    assert at.radio(key="scope_nav").value == "Emergency"
    assert 'rw-h1">Emergency</h1>' in page_html(at)
    assert presentation.status_reason(engine("Emergency", 7, 2), 2) in page_html(at)


def test_whole_hospital_is_one_click_away() -> None:
    at = run()
    at.radio(key="scope_nav").set_value("Whole hospital")
    run(at)
    assert 'rw-h1">Whole hospital</h1>' in page_html(at)
    assert engine(None, 7, 2).tolerance.value.capitalize() in page_html(at)


def test_short_period_still_renders() -> None:
    at = run()
    at.selectbox(key="period").set_value("30 days")
    run(at)
    assert "Count in the last 30 days" in page_html(at)
