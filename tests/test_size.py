"""The factory's own code stays small enough to read in one sitting (FR-039, SC-007)."""
import pathlib

import pytest

from factory import config

LIMIT = 2000    # non-blank lines in factory/*.py; tests, personas and prompts are not counted


@pytest.mark.fr("FR-039")
def test_the_factorys_own_code_is_under_the_line_limit():
    counts = {f.name: sum(1 for line in f.read_text().splitlines() if line.strip())
              for f in sorted(pathlib.Path(config.PACKAGE_DIR).glob("*.py"))}
    total = sum(counts.values())
    listing = "\n".join(f"  {name:16} {count}" for name, count in counts.items())
    assert total <= LIMIT, f"the factory's own code is {total} non-blank lines; the limit is {LIMIT}\n{listing}"
