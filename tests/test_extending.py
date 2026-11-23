"""Adding a step or a persona is one entry and one file, and touches nothing else (Story 6).

These tests change nothing on disk in the factory: they register a check and swap in a
longer step table from the outside, which is exactly what editing workflow.py would do.
"""
import ast
import dataclasses
import pathlib
import shutil

import pytest

from factory.operations import Refused

from factory import checks, config, own_files, tables, workflow, workspace
from factory.workflow import Step
from tests.conftest import script


def table_with(monkeypatch, after, new, **replace_previous):
    """Install a copy of the step table with `new` inserted after the step named `after`."""
    steps = list(tables.STEPS)
    index = [s.name for s in steps].index(after)
    steps[index] = dataclasses.replace(steps[index], on_pass=new.name, **replace_previous)
    steps.insert(index + 1, new)
    monkeypatch.setattr(tables, "table_for", lambda spec_kit, run_kind, cycle="auto": steps)
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
        return checks.CheckResult(True, f"{len(files)} python files")

    monkeypatch.setitem(checks.REGISTRY, "count_files", checks.REGISTRY["count_files"])    # removed afterwards
    table_with(monkeypatch, "test", Step("count_files", "code", on_pass="architecture_review", checks=("count_files",)))
    source_before = own_files.fingerprint([config.PACKAGE_DIR])

    run, _, store, _ = cycle(script())

    assert run.outcome == "accepted"
    names = [s.name for s in store.query("steps", {"run_id": run.id})]
    assert names == ["plan", "baseline", "write_tests", "red", "build", "test", "count_files",
                     "architecture_review", "document", "review", "finish"]
    added = store.query("steps", {"run_id": run.id})[6]
    assert [c["name"] for c in added.checks] == ["factory_untouched", "changes_allowed", "count_files"]
    assert added.checks[-1]["note"] == "2 python files" and added.passed
    assert own_files.fingerprint([config.PACKAGE_DIR]) == source_before, "no source file was edited"


@pytest.mark.fr("FR-046")
def test_a_new_persona_is_one_file_named_on_an_entry(cycle, monkeypatch):
    def install():      # the cycle fixture has already pointed PERSONAS_DIR at a temporary copy
        (config.PERSONAS_DIR / "careful_coder.md").write_text(
            "# Careful coder\n\n## Expertise\n\nCAREFUL-CODER-MARKER\n\n## Priorities\n\nSafety.\n\n## Must not\n\nRush.\n")
        steps = list(tables.STEPS)
        index = [s.name for s in steps].index("build")
        steps[index] = dataclasses.replace(steps[index], persona="careful_coder")
        monkeypatch.setattr(tables, "table_for", lambda spec_kit, run_kind, cycle="auto": steps)

    install()
    run, fake, store, _ = cycle(script())
    assert run.outcome == "accepted"
    build = [s for s in store.query("steps", {"run_id": run.id}) if s.name == "build"][0]
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
    added = store.query("steps", {"run_id": run.id})[-1]
    assert (added.name, added.failure) == ("second_opinion", "guard")
    assert [c["name"] for c in added.checks][:2] == ["factory_untouched", "changes_allowed"]


@pytest.mark.fr("FR-037")
def test_a_prompt_may_only_use_the_inputs_its_entry_lists(cycle, monkeypatch, prompts_copy):
    (prompts_copy / "second_opinion.md").write_text("Opinion on {{request}} given {{diff}}\n")
    table_with(monkeypatch, "review", Step("second_opinion", "agent", persona="reviewer", on_pass="finish",
                                             inputs=("request",)))
    with pytest.raises(Refused, match="second_opinion's prompt uses {{diff}}"):        # refused at the request (FR-112)
        cycle(script() + [{"envelope": {}}])


@pytest.mark.fr("FR-037")
@pytest.mark.parametrize("file", ["store.py", "records.py", "driver.py", "cli.py", "operations.py", "checks.py"])
def test_no_module_but_the_rules_decides_by_a_steps_or_personas_name(file):
    """No comparison with, or lookup by, a step's or persona's name outside workflow.py."""
    names = {s.name for t in tables.TABLES for s in t} | {s.persona for t in tables.TABLES for s in t if s.persona}
    tree = ast.parse((config.PACKAGE_DIR / file).read_text())
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            found += [c.value for c in ast.walk(node) if isinstance(c, ast.Constant) and c.value in names]
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "workflow.get" and node.args \
                and isinstance(node.args[0], ast.Constant) and node.args[0].value in names:
            found.append(node.args[0].value)
    assert found == [], f"{file} decides by the name of a step or persona: {found}"
