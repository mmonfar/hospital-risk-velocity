"""App-level tests with Streamlit's AppTest: the page renders and shows the engine's status."""

import datetime as dt
from pathlib import Path
from typing import cast

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from clinical_risk_dashboard.sample_data import generate_incidents
from risk_kinematics import Tolerance, calculate_risk_kinetics, classify

APP = Path(__file__).resolve().parents[2] / "src" / "clinical_risk_dashboard" / "app.py"
SIGMAS = {"Zero tolerance (1σ)": 1, "Standard (2σ)": 2, "Critical only (3σ)": 3}


def run(at: AppTest | None = None) -> AppTest:
    at = at or AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def page_html(at: AppTest) -> str:
    return "\n".join(str(m.value) for m in at.markdown)


def expected(unit: str | None, window: int, sigma: int) -> Tolerance:
    df = generate_incidents()
    if unit is not None:
        df = cast(pd.DataFrame, df[df["Unit"] == unit])
    k = calculate_risk_kinetics(df, window, sigma)
    return classify(k.daily, k.mean, k.std, sigma).tolerance


@pytest.fixture(scope="module")
def default_run() -> AppTest:
    return run()


def test_renders_all_four_charts(default_run: AppTest) -> None:
    assert len(default_run.get("plotly_chart")) == 4


def test_brand_is_applied(default_run: AppTest) -> None:
    html = page_html(default_run)
    assert "--mm-teal" in html  # canonical stylesheet injected by the bundled theme
    assert 'class="mm-dot"' in html  # wordmark square, never a typed period


def test_default_status_is_the_engine_status(default_run: AppTest) -> None:
    assert f"<b>{expected(None, 7, 2).value}</b>" in page_html(default_run)


@pytest.mark.parametrize(
    ("sigma_label", "window"), [("Zero tolerance (1σ)", 3), ("Critical only (3σ)", 15)]
)
def test_status_follows_controls(sigma_label: str, window: int) -> None:
    at = run()
    at.select_slider[0].set_value(window)
    at.select_slider[1].set_value(sigma_label)
    run(at)
    assert f"<b>{expected(None, window, SIGMAS[sigma_label]).value}</b>" in page_html(at)


def test_single_unit_scope() -> None:
    at = run()
    at.radio[0].set_value("Single unit")
    run(at)
    at.selectbox[0].set_value("CICU")
    run(at)
    html = page_html(at)
    assert "<h1>CICU</h1>" in html
    assert f"<b>{expected('CICU', 7, 2).value}</b>" in html


def test_short_period_shows_no_data() -> None:
    at = run()
    at.date_input[0].set_value((dt.date(2025, 3, 1), dt.date(2025, 3, 5)))
    run(at)
    assert f"<b>{Tolerance.NO_DATA.value}</b>" in page_html(at)
