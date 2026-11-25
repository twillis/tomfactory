"""The factory's own code, measured and reported, never a reason to fail (FR-039, SC-007).

What lets the operator read the factory in one sitting is code that is easy to follow, not a line count under a
limit. So the suite measures the factory as it would measure any codebase (FR-148): each function's cognitive
complexity, by complexipy, read with the factory's own reader; and it reports the size and the functions over the
limit a codebase starts with as a warning in pytest's summary. It fails only if the measure cannot be read.
"""
import pathlib
import subprocess
import sys
import warnings

import pytest

from factory import checks, config

COMPLEXIPY = pathlib.Path(sys.executable).parent / "complexipy"     # in the factory's dev group
LIMIT = config.TargetConfig().readability_limit
SHOWN = 10


def non_blank_lines() -> int:
    return sum(1 for file in config.PACKAGE_DIR.glob("*.py") for line in file.read_text().splitlines() if line.strip())


@pytest.mark.fr("FR-039")
def test_the_factorys_own_code_is_measured_and_reported_never_failed(tmp_path):
    if not COMPLEXIPY.exists():
        pytest.skip("complexipy is not installed; `uv sync` installs the factory's dev group")
    report = tmp_path / "readability.json"
    subprocess.run([str(COMPLEXIPY), config.PACKAGE_DIR.name, "--isolated", "-q", "--output-format", "json",
                    "--output", str(report), "--cache-dir", str(tmp_path / "cache")], cwd=config.PACKAGE_DIR.parent, capture_output=True, check=False)
    scores = checks.readability_scores(report)
    assert scores, "complexipy wrote no report the factory can read"
    high = sorted((s for s in scores if s["complexity"] > LIMIT), key=lambda s: s["complexity"], reverse=True)
    named = ", ".join(f"{s['path']}:{s['function_name']} ({s['complexity']})" for s in high[:SHOWN])
    warnings.warn(f"The factory's own code, reported, not judged: {non_blank_lines()} non-blank lines; "
                  f"{len(high)} of its {len(scores)} functions have a cognitive complexity over {LIMIT}"
                  + (f", the highest: {named}" if named else ""), stacklevel=1)
