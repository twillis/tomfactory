"""A run's stages, published for a reader (FR-145).

`factory show --json` and `factory status --json` give each run its stages: the main path of its own table, left to
right, with the operator's waits where the run has them, each stage done, current, to come, failed or skipped, and in a
coarse group (planning, waiting, building, reviewing). A reader such as the viewer draws them and keeps no copy of the
tables.
"""
import json

import pytest

from factory import cli, operations, tables, workflow
from tests.conftest import (BUILD, PLAN, WRITE_TESTS, aligned_round, commit_files, drive_with, script, speaks,
                            sprint_settings)
from tests.fake_agent import FakeAgent
from tests.test_cycle import DEFECT, MENDED, WRONG_TEST
from tests.test_dialogue import BUILD_TO_THE_END, WHO, filled, planner_says
from tests.test_questions import LEAD_UNSURE, QUESTION
from tests.test_spikes import PLAN as SPIKE_PLAN, findings, probe, retro, spike

BUILT = ["baseline", "write_tests", "red", "build", "test", "architecture_review", "document"]
DIALOGUE = ["dialogue_analyst", "dialogue_planner", "dialogue_architect", "dialogue_check"]
PLAIN = ["plan", "approval", *BUILT, "review", "finish"]
SPRINT = [*DIALOGUE, "answers", "agreement", "approval", *BUILT, "converge", "retro", "finish"]
REJECT = {"envelope": {"verdict": "reject", "reasons": ["it says goodbye"], "ideals_broken": []}}


def stages(run_id):
    """The run's stages as `factory show --json` publishes them: name -> state."""
    return {stage.name: stage.state for stage in operations.show(run_id).stages}


def states(run_id, names):
    shown = stages(run_id)
    return [shown[name] for name in names]


# ---- the main path, from each table ----

@pytest.mark.fr("FR-145")
@pytest.mark.parametrize("table, path", [
    (tables.STEPS, ["plan", *BUILT, "review", "finish"]),
    (tables.SPEC_KIT_STEPS, ["specify", "clarify", "plan", "tasks", "analyze", *BUILT, "converge", "retro",
                             "finish"]),
    (tables.SPRINT_STEPS, [*DIALOGUE, *BUILT, "converge", "retro", "finish"]),
    (tables.TIDY_CODE, ["plan", "baseline", "tidy_code", "test", "review", "finish"]),
    (tables.SPRINT_TIDY_TESTS, [*DIALOGUE, "baseline", "tidy_tests", "test", "review", "finish"]),
    (tables.SPIKE_STEPS, ["spike_plan", "probe", "run_probe", "write_findings", "spike_retro", "finish"]),
], ids=["plain", "spec-kit", "sprint", "tidy-code", "sprint-tidy-tests", "spike"])
def test_the_main_path_follows_each_steps_pass_and_past_a_wait_to_where_approval_leads(table, path):
    assert [step.name for step in workflow.main_path(table)] == path        # mend_tests and recheck_plan are off it


@pytest.mark.fr("FR-145")
@pytest.mark.parametrize("step", sorted({step.name for table in tables.TABLES for step in table}))
def test_every_step_of_every_table_is_in_one_group(step):
    assert [group for group, steps in tables.STAGE_GROUPS.items() if step in steps] == [tables.group_of(step)]
    assert tables.group_of(step) in workflow.GROUPS


# ---- what each stage's state is, from the steps the run took ----

@pytest.mark.fr("FR-145")
def test_a_plain_run_waiting_for_approval_has_its_plan_done_your_approval_current_and_the_rest_to_come(
        home, target, fake_notify):
    drive_with(FakeAgent(script()))
    run = operations.request("Add a greeting", target)
    shown = operations.show(run.id).stages
    assert [stage.name for stage in shown] == PLAIN
    assert states(run.id, PLAIN) == ["done", "current", *["to-come"] * 9]
    approval = shown[1]
    assert (approval.by, approval.group, approval.tries) == ("operator", "waiting", 0)
    assert (shown[0].by, shown[0].group, shown[0].tries) == ("planner", "planning", 1)


@pytest.mark.fr("FR-145")
def test_an_accepted_run_has_every_stage_done_and_says_how_often_each_step_ran(cycle):
    run, _, _, _ = cycle(script(write_tests=WRONG_TEST, build=[DEFECT, MENDED]))
    shown = operations.show(run.id).stages
    assert [stage.name for stage in shown] == ["plan", "approval", "baseline", "write_tests", "red", "build",
                                                "mend_tests", *PLAIN[-5:]]     # taken off the path: shown
    assert {stage.state for stage in shown} == {"done"}            # the build, sent on to mend_tests, is done
    assert [(s.name, s.tries) for s in shown if s.name in ("build", "mend_tests")] == [("build", 1), ("mend_tests", 1)]
    assert [s.group for s in shown] == ["planning", "waiting", *["building"] * 6, *["reviewing"] * 4]


@pytest.mark.fr("FR-145")
def test_advice_that_failed_and_was_carried_past_is_failed_in_an_accepted_run(cycle):
    run, _, _, _ = cycle(script(architecture_review={"error": "the agent program fell over"}))
    assert run.outcome == "accepted"
    assert states(run.id, ["test", "architecture_review", "document"]) == ["done", "failed", "done"]


@pytest.mark.fr("FR-145")
@pytest.mark.parametrize("ends, at, failed", [
    (lambda run: None, "review", "review"),                                     # rejected by the review
    (lambda run: operations.abandon(run.id), "plan", "approval"),               # abandoned at your approval
])
def test_where_a_run_ended_short_is_failed_and_what_it_never_reached_is_skipped(home, target, fake_notify, ends, at,
                                                                                failed):
    drive_with(FakeAgent(script(review=REJECT)))
    run = operations.request("Add a greeting", target)
    if at == "review":
        run = operations.approve(run.id)
    ends(run)
    after = PLAIN.index(failed)
    assert states(run.id, PLAIN) == [*["done"] * after, "failed", *["skipped"] * (len(PLAIN) - after - 1)]


@pytest.mark.fr("FR-145")
def test_a_dialogue_moves_from_your_answers_to_your_agreement_to_your_approval(home, target, fake_notify):
    sprint = commit_files(target, sprint_settings())
    drive_with(FakeAgent([speaks([WHO]), planner_says(), speaks(blocking=()), speaks(blocking=()),
                          *aligned_round(), *BUILD_TO_THE_END]))
    run = operations.request("Add a greeting", sprint)
    waits = ["answers", "agreement", "approval"]
    assert states(run.id, [*DIALOGUE, *waits, "baseline"]) == ["done"] * 4 + ["current", "to-come", "to-come", "to-come"]
    operations.answer(run.id, filled(run.id, {WHO: "a) you"}))
    assert states(run.id, waits) == ["done", "current", "to-come"]
    operations.agree(run.id)
    assert states(run.id, waits) == ["done", "done", "current"]
    run = operations.approve(run.id)
    assert run.outcome == "accepted" and set(states(run.id, SPRINT)) == {"done"}


@pytest.mark.fr("FR-145")
def test_a_dialogue_aligned_at_once_skips_your_answers(home, target, fake_notify):
    sprint = commit_files(target, sprint_settings())
    drive_with(FakeAgent([*aligned_round(), *BUILD_TO_THE_END]))
    run = operations.request("Add a greeting", sprint)
    operations.agree(run.id)
    operations.approve(run.id)
    assert states(run.id, ["dialogue_check", "answers", "agreement", "approval"]) == ["done", "skipped", "done", "done"]


@pytest.mark.fr("FR-145")
def test_a_step_waiting_on_your_answer_to_its_question_is_the_current_stage(home, target, fake_notify):
    drive_with(FakeAgent([{"envelope": PLAN}, WRITE_TESTS, QUESTION, LEAD_UNSURE, BUILD]))
    run = operations.approve(operations.request("Add a greeting", target).id)
    assert run.state == "awaiting_approval"
    assert states(run.id, ["approval", "red", "build", "test"]) == ["done", "done", "current", "to-come"]


@pytest.mark.fr("FR-145")
def test_a_spike_has_no_wait_and_ends_with_every_stage_done(home, tmp_path, fake_notify):
    run, *_ = spike(home, tmp_path, [SPIKE_PLAN, probe(), findings(), retro])
    shown = operations.show(run.id).stages
    assert [(s.name, s.state, s.group) for s in shown] == [
        ("spike_plan", "done", "planning"), ("probe", "done", "building"), ("run_probe", "done", "building"),
        ("write_findings", "done", "reviewing"), ("spike_retro", "done", "reviewing"), ("finish", "done", "reviewing")]


@pytest.mark.fr("FR-145")
def test_a_run_whose_codebase_can_no_longer_be_read_has_no_stages(home, target, fake_notify):
    drive_with(FakeAgent(script()))
    run = operations.request("Add a greeting", target)
    operations.abandon(run.id)
    (target / ".git").rename(target / "not-git")            # its table cannot be read at its starting commit
    assert operations.show(run.id).stages == []


@pytest.mark.fr("FR-145")
def test_a_run_that_took_a_step_its_table_no_longer_has_has_no_stages(home, target, fake_notify, monkeypatch):
    drive_with(FakeAgent(script()))
    run = operations.request("Add a greeting", target)
    operations.abandon(run.id)
    monkeypatch.setitem(tables.RUN_KINDS, "change", (tables.SPIKE_STEPS,) * 2)    # as if its table changed
    assert operations.show(run.id).stages == []


# ---- published: show --json and status --json ----

@pytest.mark.fr("FR-145")
@pytest.mark.parametrize("command, view", [(["show", "--json"], lambda out: out),
                                           (["status", "--json"], lambda out: out[0])])
def test_show_and_status_publish_the_stages_as_json(home, target, fake_notify, capsys, command, view):
    drive_with(FakeAgent(script()))
    operations.request("Add a greeting", target)
    capsys.readouterr()
    assert cli.main(command) == 0
    published = view(json.loads(capsys.readouterr().out))["stages"]
    assert published[:2] == [{"name": "plan", "by": "planner", "group": "planning", "state": "done", "tries": 1},
                             {"name": "approval", "by": "operator", "group": "waiting", "state": "current",
                              "tries": 0}]
    assert [stage["name"] for stage in published] == PLAIN


@pytest.mark.fr("FR-145")
def test_the_stage_vocabularies_are_written_once():
    assert workflow.STAGE_STATES == ("done", "current", "to-come", "failed", "skipped")
    assert workflow.GROUPS == ("planning", "waiting", "building", "reviewing")
    assert workflow.WAITS == ("approval",) and workflow.DIALOGUE_WAITS == ("answers", "agreement", "approval")
