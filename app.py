"""Entry point for hosts that expect ``app.py`` at the repository root."""

import sys
from pathlib import Path
from runpy import run_path

SRC = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC))
run_path(str(SRC / "clinical_risk_dashboard" / "app.py"), run_name="__main__")
