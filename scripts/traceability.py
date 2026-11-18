"""Gate (constitution S8): every FR in the spec must be named by at least one test.

Run from the repository root:  uv run python scripts/traceability.py
Prints the requirements no test names and exits 1 if there are any.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "specs" / "001-near-loop-factory" / "spec.md"


def main() -> int:
    wanted = set(re.findall(r"^- \*\*(FR-\d{3})\*\*:", SPEC.read_text(), re.M))
    named: set[str] = set()
    for path in (ROOT / "tests").rglob("*.py"):
        named |= set(re.findall(r"""fr\(\s*["'](FR-\d{3})["']\s*\)""", path.read_text()))
    missing = sorted(wanted - named)
    unknown = sorted(named - wanted)
    print(f"{len(wanted)} requirements, {len(wanted) - len(missing)} named by a test")
    if unknown:
        print("markers naming no requirement in the spec:", ", ".join(unknown))
    if missing:
        print("named by no test:", ", ".join(missing))
    return 1 if missing or unknown else 0


if __name__ == "__main__":
    sys.exit(main())
