"""app.py only wires filters and calls (spec DASH-4). Checked by reading the source tree."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_root_app_is_only_a_launcher() -> None:
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    assert not [n for n in tree.body if isinstance(n, ast.FunctionDef | ast.ClassDef)]


def test_app_takes_words_and_page_parts_from_presentation_and_view() -> None:
    src = (ROOT / "src" / "clinical_risk_dashboard" / "app.py").read_text(encoding="utf-8")
    assert "view." in src and "presentation." in src
    assert "def status_view" not in src and "def momentum_lines" not in src
    assert "def trend_svg" not in src and "def kpis_html" not in src
