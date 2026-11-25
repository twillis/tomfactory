"""A project's per-step overrides in .factory.toml: a closed list of fields on steps that exist (FR-112)."""
import pytest

from factory import cli, config, operations, tables
from factory.operations import Refused
from factory.workflow import Rework
from tests.conftest import ARCHITECT, BUILD, commit_files, DOCUMENT, drive_with, PLAN, REVIEW, WRITE_TESTS
from tests.fake_agent import FakeAgent


def settings(extra, climbs_to="standard"):
    toml = config.DEFAULT_FACTORY_TOML.replace('climbs_to = "standard"', f'climbs_to = "{climbs_to}"')
    return {".factory.toml": toml + extra}


def entry(table, name):
    return next(step for step in table if step.name == name)


@pytest.mark.fr("FR-112")
def test_each_overridable_field_is_applied_and_smells_are_added_never_removed():
    table = tables.overridden(tables.SPRINT_STEPS, {
        "document": {"model": "middle", "timeout": 600},
        "build": {"smells": ["tests_within_budget", "lines_within_length"]},
        "converge": {"rework_at_most": 1}})
    assert (entry(table, "document").model, entry(table, "document").timeout) == ("middle", 600)
    assert entry(table, "build").smells == ("lines_within_length", "readable", "tests_within_budget")
    assert entry(table, "converge").routes["rework"] == Rework("build", at_most=1, then="retro")
    assert entry(table, "dialogue_planner") == entry(tables.SPRINT_STEPS, "dialogue_planner")    # untouched: the same


@pytest.mark.fr("FR-112")
@pytest.mark.parametrize("overrides, says", [
    ({"nosuch": {"model": "light"}}, "[steps.nosuch]: there is no step nosuch in this run's table"),
    ({"build": {"checks": []}}, "[steps.build]: checks cannot be set; a project may set model, timeout, smells, rework_at_most"),
    ({"build": {"persona": "x"}}, "[steps.build]: persona cannot be set"),
    ({"build": {"may_change": "anything"}}, "[steps.build]: may_change cannot be set"),
    ({"build": {"model": "fable"}}, "[steps.build]: model must be one of light, middle, standard, strongest"),
    ({"test": {"model": "light"}}, "[steps.test]: model must be one of light, middle, standard, strongest, on an agent step"),
    ({"build": {"timeout": True}}, "[steps.build]: timeout must be a whole number of seconds"),
    ({"build": {"smells": "lines_within_length"}}, "[steps.build]: smells must be a list of check names"),
    ({"dialogue_planner": {"rework_at_most": 2}},
     "[steps.dialogue_planner]: rework_at_most needs a capped rework route; it has none"),
    ({"converge": {"rework_at_most": 0}}, "[steps.converge]: rework_at_most must be a whole number, at least 1"),
])
def test_an_override_that_is_not_allowed_is_refused_naming_it(overrides, says):
    with pytest.raises(ValueError) as refused:
        tables.overridden(tables.SPRINT_STEPS, overrides)
    assert says in str(refused.value)


@pytest.mark.fr("FR-112")
def test_a_request_with_an_unsound_override_is_refused_before_any_run_exists(home, target, fake_notify):
    commit_files(target, settings('\n[steps.build]\nsmells = ["nosuch_check"]\n'))
    with pytest.raises(Refused, match="build uses the check nosuch_check, which is not registered"):
        operations.request("Add a greeting", target)
    assert operations.status() == []


@pytest.mark.fr("FR-112")
def test_a_run_uses_the_projects_model_and_climb_ceiling(home, target, fake_notify):
    commit_files(target, settings('\n[steps.build]\nmodel = "light"\n', climbs_to="middle"))
    broken = dict(BUILD, files={"hello.py": "def greet(:\n"})                 # fails the tests twice, then mended
    fake = drive_with(FakeAgent([{"envelope": PLAN}, WRITE_TESTS, broken, broken, BUILD, ARCHITECT, DOCUMENT, REVIEW]))
    run = operations.approve(operations.request("Add a greeting", target).id)
    assert run.outcome == "accepted", run.reason
    assert [call["model"] for call in fake.calls][2:5] == ["light", "middle", "middle"]    # climbs, then stops


@pytest.mark.fr("FR-112")
def test_climbs_to_must_be_a_grade(home, target, fake_notify):
    commit_files(target, settings("", climbs_to="fable"))
    with pytest.raises(Refused, match="climbs_to must be light, middle, standard or strongest"):
        operations.request("Add a greeting", target)


@pytest.mark.fr("FR-112")
def test_the_table_command_shows_the_steps_with_the_projects_overrides(target, capsys):
    commit_files(target, settings('\n[steps.document]\nmodel = "middle"\ntimeout = 600\n'))
    assert cli.main(["table", "--target", str(target)]) == 0
    lines = capsys.readouterr().out.splitlines()
    document = next(line for line in lines if line.startswith("document"))
    assert "model middle" in document and "timeout 600s" in document


@pytest.mark.fr("FR-112")
def test_a_new_codebases_settings_file_has_no_step_overrides():
    assert "steps" not in config.DEFAULT_FACTORY_TOML.split("climbs_to")[1]
