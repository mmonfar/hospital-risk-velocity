"""Make the tests import the frozen engine (commit 48c467f), not whatever is installed.

The study ran against engine commit 48c467f. The installed package may be newer.
Set RKIN_ENGINE=c3cee22 to point at the later copy (its tests are in test_trailing_parity.py).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ENGINE = os.environ.get("RKIN_ENGINE", "48c467f")
SRC = Path(__file__).resolve().parents[1] / "engine_frozen" / ENGINE / "src"


def use_engine(src: Path) -> None:
    for name in [m for m in sys.modules if m == "risk_kinematics" or m.startswith("risk_kinematics.")]:
        del sys.modules[name]
    sys.path[:] = [p for p in sys.path if Path(p).resolve() != src.resolve()]
    sys.path.insert(0, str(src))
    sys.meta_path[:] = [f for f in sys.meta_path if "risk_kinematics" not in type(f).__module__ + repr(getattr(f, "__dict__", ""))[:400]]


use_engine(SRC)
