"""The written explanation exists and covers what the operator needs (FR-036)."""
import pathlib
import re

import pytest

from factory import config

ROOT = config.PACKAGE_DIR.parent
HEADINGS = ["How a run flows", "Using the factory", "Adding a step", "Adding a persona",
            "Where the rules live", "What this proof of concept does not protect you from"]


@pytest.mark.fr("FR-036")
def test_the_readme_has_its_named_sections():
    readme = (ROOT / "README.md").read_text()
    found = re.findall(r"^#+ (.+)$", readme, re.M)
    for heading in HEADINGS:
        assert heading in found, f"README.md has no section titled {heading!r}"


@pytest.mark.fr("FR-036")
def test_the_readme_names_every_command_and_every_step():
    from factory import workflow
    readme = (ROOT / "README.md").read_text()
    contract = (ROOT / "specs" / "001-near-loop-factory" / "contracts" / "cli.md").read_text()
    commands = set(re.findall(r"^\| `factory ([a-z-]+)", contract, re.M))
    assert len(commands) >= 12
    for command in commands:
        assert f"factory {command}" in readme, f"README.md does not show `factory {command}`"
    for step in workflow.STEPS:
        assert f"`{step.name}`" in readme, f"README.md does not mention the {step.name} step"
    for limit in ("contained", "bubblewrap", "kernel", "not contained by the factory"):     # the limits, stated
        assert limit in readme, f"README.md does not state: {limit}"
