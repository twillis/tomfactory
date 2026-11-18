"""Adding a step or a persona is one entry and one file, and touches nothing else (Story 6).

These tests change nothing on disk in the factory: they register a check and swap in a
longer step table from the outside, which is exactly what editing workflow.py would do.
"""
import dataclasses
import pathlib
import re
import shutil

import pytest

from factory import checks, config, workflow, workspace
from factory.workflow import Step
from tests.test_cycle import BUILD, cycle, script  # noqa: F401  (cycle is a fixture)


def table_with(monkeypatch, after, new, **replace_previous):
    """Install a copy of the step table with `new` inserted after the step named `after`."""
    steps = list(workflow.STEPS)
    index = [s.name for s in steps].index(after)
    steps[index] = dataclasses.replace(steps[index], on_pass=new.name, **replace_previous)
    steps.insert(index + 1, new)
    monkeypatch.setattr(workflow, "STEPS", steps)
    return steps


@pytest.fixture
def prompts_copy(tmp_path, monkeypatch):
    folder = tmp_path / "prompts"
    shutil.copytree(config.PROMPTS_DIR, folder)
    monkeypatch.setattr(config, "PROMPTS_DIR", folder)
    return folder


@pytest.mark.fr("FR-037")
@pytest.mark.fr("FR-030")
def test_a_new_code_step_is_one_check_and_one_entry(cycle, monkeypatch):
    @checks.register("count_files")
    def count_files(ctx):
        files = [f for f in pathlib.Path(ctx.checkout.path).rglob("*.py")]
        return checks.CheckResult("count_files", True, f"{len(files)} python files")

    monkeypatch.setitem(checks.REGISTRY, "count_files", count_files)
    table_with(monkeypatch, "test", Step("count_files", "code", on_pass="architecture_review", checks=("count_files",)))
    source_before = workspace.fingerprint([config.PACKAGE_DIR])

    run, _, store, _ = cycle(script())

    assert run.outcome == "accepted"
    names = [s.name for s in store.steps.list(run.id)]
    assert names == ["plan", "baseline", "write_tests", "red", "build", "test", "count_files",
                     "architecture_review", "document", "review", "finish"]
    added = store.steps.list(run.id)[6]
    assert [c["name"] for c in added.checks] == ["factory_untouched", "changes_allowed", "count_files"]
    assert added.checks[-1]["note"] == "2 python files" and added.passed
    assert workspace.fingerprint([config.PACKAGE_DIR]) == source_before, "no source file was edited"


@pytest.mark.fr("FR-046")
def test_a_new_persona_is_one_file_named_on_an_entry(cycle, monkeypatch):
    def install():      # the cycle fixture has already pointed PERSONAS_DIR at a temporary copy
        (config.PERSONAS_DIR / "careful_coder.md").write_text(
            "# Careful coder\n\n## Expertise\n\nCAREFUL-CODER-MARKER\n\n## Priorities\n\nSafety.\n\n## Must not\n\nRush.\n")
        steps = list(workflow.STEPS)
        index = [s.name for s in steps].index("build")
        steps[index] = dataclasses.replace(steps[index], persona="careful_coder")
        monkeypatch.setattr(workflow, "STEPS", steps)

    install()
    run, fake, store, _ = cycle(script())
    assert run.outcome == "accepted"
    build = [s for s in store.steps.list(run.id) if s.name == "build"][0]
    assert build.persona == "careful_coder"
    assert "CAREFUL-CODER-MARKER" in fake.calls[2]["persona"]


@pytest.mark.fr("FR-037")
@pytest.mark.fr("FR-032")
def test_a_new_agent_step_that_says_nothing_may_read_and_change_nothing(cycle, monkeypatch, prompts_copy):
    (prompts_copy / "second_opinion.md").write_text("Give a second opinion on:\n\n{{request}}\n")
    table_with(monkeypatch, "review", Step("second_opinion", "agent", persona="reviewer", on_pass="finish",
                                             inputs=("request",)))
    meddling = {"envelope": {}, "files": {"hello.py": "tampered = True\n"}}
    run, fake, store, _ = cycle(script() + [meddling])
    assert fake.calls[-1]["capabilities"] == "read"                      # the closed default
    assert run.outcome == "needs-me" and "second_opinion" in run.reason and "hello.py" in run.reason
    added = store.steps.list(run.id)[-1]
    assert (added.name, added.failure) == ("second_opinion", "guard")
    assert [c["name"] for c in added.checks][:2] == ["factory_untouched", "changes_allowed"]


@pytest.mark.fr("FR-037")
def test_a_prompt_may_only_use_the_inputs_its_entry_lists(cycle, monkeypatch, prompts_copy):
    (prompts_copy / "second_opinion.md").write_text("Opinion on {{request}} given {{diff}}\n")
    table_with(monkeypatch, "review", Step("second_opinion", "agent", persona="reviewer", on_pass="finish",
                                             inputs=("request",)))
    with pytest.raises(LookupError, match="diff"):
        cycle(script() + [{"envelope": {}}])


@pytest.mark.fr("FR-037")
def test_the_data_layer_the_driver_and_the_command_line_name_no_step_and_no_persona():
    steps = [s.name for s in workflow.STEPS if s.name != "plan"]     # "plan" is also the thing the operator approves
    personas = [s.persona for s in workflow.STEPS if s.persona]
    for file in ("store.py", "driver.py", "cli.py", "operations.py", "checks.py"):
        text = (config.PACKAGE_DIR / file).read_text()
        literals = set(re.findall(r"""["']([a-z_]+)["']""", text))
        named = sorted(literals & set(steps + personas))
        if file == "checks.py":
            named = [n for n in named if n not in ("baseline",)]      # a check may share a step's name
        if file == "cli.py":
            named = [n for n in named if n not in ("test",)]
        assert named == [], f"{file} names steps or personas: {named}"
