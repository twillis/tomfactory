"""The factory's own code stays small enough to read in one sitting (FR-039, SC-007)."""
import pathlib

import pytest

from factory import config

LIMIT = 4100    # non-blank lines in factory/*.py; tests, personas and prompts are not counted.
                # The operator, 2026-11-18: "at this point size is not a thing that matters necessarily".
                # Kept as a tripwire against runaway growth, not as a target. Raised from 3,500 to 4,100
                # on 2026-11-24 for the planning dialogue (FR-119 to FR-129), which took it to about 4,030.


@pytest.mark.fr("FR-039")
def test_the_factorys_own_code_is_under_the_line_limit():
    counts = {f.name: sum(1 for line in f.read_text().splitlines() if line.strip())
              for f in sorted(pathlib.Path(config.PACKAGE_DIR).glob("*.py"))}
    total = sum(counts.values())
    listing = "\n".join(f"  {name:16} {count}" for name, count in counts.items())
    assert total <= LIMIT, f"the factory's own code is {total} non-blank lines; the limit is {LIMIT}\n{listing}"
