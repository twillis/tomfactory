"""FR-164: a codebase built on another reads that codebase's developer docs, never its source."""
import pathlib

import pytest

from factory import config, operations
from tests.conftest import commit_files, drive_with, git, planner_says, speaks, sprint_settings
from tests.fake_agent import FakeAgent

GUIDE = "# Building an app\n\nCall make_app(settings).\n"


@pytest.fixture
def framework(tmp_path):
    """The codebase the target is built on, beside it: docs, a README and source."""
    other = tmp_path / "framework"
    other.mkdir()
    git(other, "init", "-q", "-b", "main")
    return commit_files(other, {"docs/guide.md": GUIDE, "README.md": "# framework\n", "framework/core.py": "x = 1\n"})


def with_docs(entries):
    """The sprint settings with `readable_docs` set to `entries`."""
    settings = sprint_settings()
    toml = settings[".factory.toml"]
    line = next(line for line in toml.splitlines() if line.startswith("readable_docs"))
    settings[".factory.toml"] = toml.replace(line, "readable_docs = " + str(list(entries)).replace("'", '"'))
    return settings


def built_on_prompt(target, entries):
    seen = {}

    def analyst(call):
        seen["prompt"], seen["cwd"] = call["prompt"], pathlib.Path(call["cwd"])
        return speaks()

    commit_files(target, with_docs(entries))
    drive_with(FakeAgent([analyst, planner_says(), speaks(blocking=()), speaks(blocking=())]))
    operations.request("Add a greeting", target)
    return seen["prompt"], seen["cwd"]


@pytest.mark.fr("FR-164")
@pytest.mark.parametrize("named", ["from the target", "whole"])
def test_the_agents_get_the_docs_of_what_it_is_built_on_and_not_its_source(home, target, framework, fake_notify,
                                                                           named):
    codebase = "../framework" if named == "from the target" else str(framework)
    prompt, cwd = built_on_prompt(target, [f"{codebase}:docs", f"{codebase}:README.md"])
    copy = cwd / ".factory-built-on" / "framework"
    assert (copy / "docs" / "guide.md").read_text() == GUIDE
    assert (copy / "README.md").exists() and not (copy / "framework").exists()
    assert "`.factory-built-on/framework/docs/guide.md`" in prompt and "never from its source" in prompt
    assert "core.py" not in prompt
    status = git(cwd, "status", "--porcelain")
    assert ".factory-built-on" not in status                                  # never part of a step's change


@pytest.mark.fr("FR-164")
def test_a_codebase_built_on_nothing_is_told_so(home, target, fake_notify):
    prompt, cwd = built_on_prompt(target, [])
    assert "names no other codebase it is built on" in prompt
    assert not (cwd / ".factory-built-on").exists()


@pytest.mark.fr("FR-164")
def test_an_entry_without_its_codebase_is_refused(target):
    commit_files(target, with_docs(["docs"]))
    with pytest.raises(config.ConfigError, match="readable_docs"):
        config.read_target_config(target, git(target, "rev-parse", "HEAD").strip())
