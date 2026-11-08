"""Check that every criterion id in the specs is traced to a test that exists.

Usage: python tests/spec_trace.py   (exit 0 = ok, exit 1 = problem)
TRACE.md rows: | ID | `path::test_name` | what the test asserts |  (or GAP in the test column).
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "docs" / "specs"
TRACE = SPECS / "TRACE.md"
ID_RE = re.compile(r"^- ([A-Z]+-\d+):", re.M)


def spec_ids() -> list[str]:
    ids: list[str] = []
    for spec in sorted(SPECS.glob("*.md")):
        if spec.name != TRACE.name:
            ids += ID_RE.findall(spec.read_text(encoding="utf-8"))
    return ids


def test_exists(ref: str) -> bool:
    path, _, name = ref.partition("::")
    file = ROOT / path
    return file.is_file() and bool(re.search(rf"^\s*(async )?def {re.escape(name)}\(", file.read_text(encoding="utf-8"), re.M))


def main() -> int:
    problems: list[str] = []
    rows: dict[str, list[str]] = {}
    if TRACE.is_file():
        for line in TRACE.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and re.fullmatch(r"[A-Z]+-\d+", cells[0]):
                rows[cells[0]] = re.findall(r"`([^`]+)`", cells[1]) or [cells[1]]
    else:
        problems.append("docs/specs/TRACE.md is missing")
    ids = spec_ids()
    for i in ids:
        if i not in rows:
            problems.append(f"{i}: not in TRACE.md")
            continue
        for ref in rows[i]:
            if ref.strip() == "GAP":
                problems.append(f"{i}: GAP, no test")
            elif not test_exists(ref):
                problems.append(f"{i}: test not found: {ref}")
    for i in rows:
        if i not in ids:
            problems.append(f"{i}: in TRACE.md but not in any spec")
    for p in problems:
        print("FAIL", p)
    print(f"{len(ids)} criteria, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
