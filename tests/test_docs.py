"""The written explanation exists and covers what the operator needs (FR-036)."""
import pathlib
import re

import pytest

from factory import config, tables

ROOT = config.PACKAGE_DIR.parent
HEADINGS = ["How a run flows", "Using the factory", "Adding a step", "Adding a persona",
            "Where the rules live", "What this proof of concept does not protect you from"]


@pytest.mark.fr("FR-036")
def test_the_readme_has_its_named_sections():
    readme = (ROOT / "README.md").read_text()
    found = re.findall(r"^#+ (.+)$", readme, re.M)
    for heading in HEADINGS:
        assert heading in found, f"README.md has no section titled {heading!r}"


def _commands():
    """The commands the parser itself accepts, so a new one cannot go undocumented."""
    from factory import cli
    choices = next(a for a in cli.build_parser()._actions if a.dest == "command").choices
    return [name for name in choices if not name.startswith("_")]


@pytest.mark.fr("FR-036")
def test_the_readme_names_every_command_step_input_and_module():
    from factory import driver, workflow
    readme = (ROOT / "README.md").read_text()
    for command in _commands():
        assert f"factory {command}" in readme, f"README.md does not show `factory {command}`"
    for step in {s.name for table in tables.TABLES for s in table}:
        assert f"`{step}`" in readme, f"README.md does not mention the {step} step"
    for name in driver.INPUTS:
        assert f"`{name}`" in readme, f"README.md does not list the input {name}"
    for module in (ROOT / "factory").glob("*.py"):
        if module.name not in ("__init__.py", "__main__.py"):
            assert f"`{module.name}`" in readme, f"README.md's map has no row for {module.name}"
    for limit in ("contained", "bubblewrap", "kernel", "not contained by the factory"):     # the limits, stated
        assert limit in readme, f"README.md does not state: {limit}"
