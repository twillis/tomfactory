"""Tuning the dialogue after its first real run (FR-130 to FR-138; bttr_erp's run 95 and its retro).

The plan check stops blocking on polish; the agents read before they ask; questions that ask the same thing are
answered once; rulings reach a dialogue while it runs; the factory deletes what an agent asks it to; the documenter
states only what the factory measured; the budget's figures reconcile; and a test of a module not yet built has one
convention.
"""
import re
import stat

import pytest

from factory import cli, config, dialogue, driver, operations, records, run_record, tables, workflow
from factory.operations import Refused
from factory.store import open_store
from tests.conftest import (BUILD, CODE, DOCUMENT, REVIEW, TEST, WRITE_TESTS, aligned_round, commit_files,
                            drive_with, git, merges, planner_says, script, speaks, sprint_settings)
from tests.fake_agent import FakeAgent
from tests.test_dialogue import BUILD_TO_THE_END, HOW_LOUD, SPEAKERS, WHO, filled, names, prompts_of, start

SAME = "Who should be greeted first? a) the operator  b) a guest"


@pytest.fixture
def sprint(target):
    return commit_files(target, sprint_settings())


def ids_in(prompt) -> list[str]:
    return re.findall(r"\[(Q\d+)\]", prompt)


# ---- FR-130: only a blocking point holds alignment open; everything else is a note ----

@pytest.mark.fr("FR-130")
def test_the_architect_and_the_plan_check_reply_with_blocking_points_and_notes_apart():
    for name in ("dialogue_architect", "dialogue_check"):
        step = workflow.get(name, tables.SPRINT_STEPS)
        assert {"blocking", "notes"} <= set(step.envelope) and "points" not in step.envelope, name


@pytest.mark.fr("FR-130")
def test_a_round_with_only_notes_is_aligned_and_the_notes_are_shown_beside_the_plan(home, sprint, fake_notify):
    note = "the greeting could live in a constant"
    run, _ = start(sprint, [speaks(), planner_says(), speaks(blocking=(), notes=[note]), speaks(blocking=())])
    assert names(home, run) == SPEAKERS                                       # one round: a note holds nothing open
    assert operations.waiting(run.id)["for"] == "agreement"
    shown = operations.plan(run.id).text
    assert note in shown and "Notes" in shown
    said = dialogue.transcript(open_store(home), run)
    assert f"A note for the planner: {note}" in said


@pytest.mark.fr("FR-130")
def test_a_blocking_point_goes_round_again_and_its_notes_reach_the_planner_with_it(home, sprint, fake_notify):
    blocking, note = "greet() is hello() in the plan's test: the build cannot pass", "name the module greeting"
    run, fake = start(sprint, [speaks(), planner_says(), speaks(blocking=(), notes=[note]),
                               speaks(blocking=[blocking]), *aligned_round()])
    assert names(home, run) == SPEAKERS * 2
    assert blocking in fake.calls[5]["prompt"] and note in fake.calls[5]["prompt"]
    assert "Blocking:" in fake.calls[5]["prompt"]


@pytest.mark.fr("FR-130")
def test_the_plan_check_is_a_colleague_in_the_dialogue_and_still_the_assayer_in_the_final_review():
    check = (config.PROMPTS_DIR / "dialogue_check.md").read_text()
    for says in ("a colleague at the planning table, not the assayer", "would break the build or contradict a ruling",
                 "A good plan agreed today beats a perfect plan in round twelve", "`blocking`", "`notes`"):
        assert says in " ".join(check.split()), says
    architect = " ".join((config.PROMPTS_DIR / "dialogue_architect.md").read_text().split())
    assert "`blocking`" in architect and "`notes`" in architect
    assert "Assayer" in (config.PERSONAS_DIR / "reviewer.md").read_text()
    for final in ("review", "converge"):
        assert "colleague" not in (config.PROMPTS_DIR / f"{final}.md").read_text()


@pytest.mark.fr("FR-130")
def test_points_still_blocking_after_the_attempt_limit_are_put_to_the_asker_as_before(home, sprint, fake_notify):
    stubborn = [speaks(), planner_says(), speaks(blocking=["the build cannot import hello"]), speaks(blocking=())]
    run, _ = start(sprint, stubborn * 2, attempts=2)
    asked = operations.questions(run.id).questions
    assert len(asked) == 1 and "the build cannot import hello" in asked[0].question


# ---- FR-131: the agents read the artifacts before they ask ----

@pytest.mark.fr("FR-131")
def test_the_analyst_reads_the_artifacts_first_and_asks_only_what_they_do_not_settle(home, sprint, fake_notify):
    text = " ".join((config.PROMPTS_DIR / "dialogue_analyst.md").read_text().split())
    assert "before you show any reading of the ask" not in text
    assert "ask your open questions before" not in text
    for says in ("Read the ask against the artifacts first", "requirements and rulings", "knowledge/",
                 "run records", "ask only what they do not settle"):
        assert says in text, says
    run, fake = start(sprint, aligned_round())
    first = fake.calls[0]["prompt"]
    assert "This is round 1" in first and "Read the artifacts first" in first


# ---- FR-132: questions that ask the same thing are answered once ----

def same_from_two(then=()):
    """Round 1: the analyst and the planner ask the same thing; the merge says so."""
    return [speaks([WHO]), planner_says(questions=[SAME]), speaks(blocking=()), speaks(blocking=()),
            lambda call: merges(ids_in(call["prompt"])), *then]


@pytest.mark.fr("FR-132")
def test_questions_from_two_agents_that_ask_the_same_thing_are_merged_and_answered_once(home, sprint, fake_notify):
    run, fake = start(sprint, same_from_two(aligned_round()))
    merge = fake.calls[4]
    assert merge["persona"].startswith("# Facilitator") and merge["model"] == "middle"
    assert WHO in merge["prompt"] and SAME in merge["prompt"]
    waiting = operations.questions(run.id).questions
    assert [q.question for q in waiting] == [WHO]                       # the asker answers it once
    operations.answer(run.id, "b, a guest")
    asked = open_store(home).query("questions", {"run_id": run.id})
    assert [(q.asked_by, q.answer) for q in asked] == [("analyst", "b, a guest"), ("planner", "b, a guest")]
    said = dialogue.transcript(open_store(home), run)
    assert f"merged into Q{asked[0].id}" in said
    for call in fake.calls[5:7]:                                      # the analyst and the planner, in round 2
        assert "b, a guest" in call["prompt"] and SAME in call["prompt"] and WHO in call["prompt"]


@pytest.mark.fr("FR-132")
@pytest.mark.parametrize("merged", [
    {"text": "no JSON at all"},                                         # the merge step failed
    {"envelope": {"merged": [["Q1", "Q999"]]}},                         # names a question not waiting
    {"envelope": {"merged": [["Q1"]]}},                                 # a group of one merges nothing
])
def test_a_merge_that_fails_or_does_not_hold_leaves_the_batches_unmerged(home, sprint, fake_notify, merged):
    run, _ = start(sprint, [speaks([WHO]), planner_says(questions=[SAME]), speaks(blocking=()), speaks(blocking=()),
                            merged])
    assert [q.question for q in operations.questions(run.id).questions] == [WHO, SAME]
    assert run.state == "awaiting_approval"


@pytest.mark.fr("FR-132")
def test_no_merge_is_asked_for_when_only_one_agent_asks(home, sprint, fake_notify):
    run, fake = start(sprint, [speaks([WHO, HOW_LOUD]), planner_says(), speaks(blocking=()), speaks(blocking=())])
    assert len(fake.calls) == 4 and len(operations.questions(run.id).questions) == 2


# ---- FR-133: a ruling or fact added to a run while it plans ----

@pytest.mark.fr("FR-133")
def test_a_note_reaches_every_speaker_from_the_next_round_on_and_is_in_the_record(home, sprint, fake_notify, capsys):
    ruling = "Ruling: greet in French from now on"
    run, fake = start(sprint, [speaks([WHO]), planner_says(), speaks(blocking=()), speaks(blocking=()),
                               *aligned_round(), *BUILD_TO_THE_END])
    assert cli.main(["note", str(run.id), ruling]) == 0
    assert "note" in capsys.readouterr().out.lower()
    operations.answer(run.id, "a")
    for call in fake.calls[4:8]:
        assert ruling in call["prompt"] and "the operator" in call["prompt"], call["persona"][:20]
        assert re.search(r"\d{4}-\d\d-\d\d \d\d:\d\d UTC", call["prompt"])
    run = operations.approve(operations.agree(run.id).id)
    assert run.outcome == "accepted", run.reason
    assert ruling in git(sprint, "show", f"{run.branch}:{run_record.name(run)}")


@pytest.mark.fr("FR-133")
def test_a_note_is_refused_when_empty_after_the_run_ended_or_on_a_run_with_no_dialogue(home, sprint, target,
                                                                                        fake_notify):
    run, _ = start(sprint, [speaks([WHO]), planner_says(), speaks(blocking=()), speaks(blocking=())])
    with pytest.raises(Refused, match="say what"):
        operations.note(run.id, "  ")
    operations.abandon(run.id)
    with pytest.raises(Refused, match="ended"):
        operations.note(run.id, "too late")


@pytest.mark.fr("FR-133")
def test_a_note_is_refused_on_a_run_that_plans_without_a_dialogue(home, target, fake_notify):
    drive_with(FakeAgent(script()))
    run = operations.request("Add a greeting", target)
    with pytest.raises(Refused, match="dialogue"):
        operations.note(run.id, "a ruling")


# ---- FR-134: each round reads the standing documents from the codebase's main line as it is now ----

@pytest.mark.fr("FR-134")
def test_each_round_reads_the_requirements_from_main_now_not_from_the_start_commit(home, sprint, fake_notify):
    commit_files(sprint, {"requirements/rulings.md": "8: the old wording\n", "IDEALS.md": "Be kind.\n"})
    seen = {}

    def analyst_in_round_2(call):
        side = config.pathlib.Path(call["cwd"]) / ".factory-main"
        seen["text"] = (side / "requirements" / "rulings.md").read_text()
        seen["ideals"] = (side / "IDEALS.md").read_text()
        seen["writable"] = bool((side / "requirements" / "rulings.md").stat().st_mode & stat.S_IWUSR)
        seen["prompt"] = call["prompt"]
        return speaks()

    run, _ = start(sprint, [speaks([WHO]), planner_says(), speaks(blocking=()), speaks(blocking=()),
                            analyst_in_round_2, planner_says(), speaks(blocking=()), speaks(blocking=())])
    head = git(commit_files(sprint, {"requirements/rulings.md": "8 (ruling): the new wording\n"}), "rev-parse",
               "HEAD")
    operations.answer(run.id, "a")
    assert seen["text"] == "8 (ruling): the new wording\n" and seen["ideals"] == "Be kind.\n"
    assert not seen["writable"]
    assert ".factory-main/requirements/rulings.md" in seen["prompt"] and head[:10] in seen["prompt"]
    checkout = open_store(home).get("runs", run.id).workspace
    assert git(checkout, "status", "--porcelain") == ""                       # nothing a step would commit
    assert (config.pathlib.Path(checkout) / "requirements" / "rulings.md").read_text() == "8: the old wording\n"


# ---- FR-135: the factory deletes the files an agent asks it to, checked like any other change ----

def deleting(*paths):
    return dict(BUILD, envelope={**BUILD["envelope"], "delete": list(paths)})


@pytest.mark.fr("FR-135")
def test_the_builder_asks_and_the_factory_deletes_the_file_with_the_steps_work(cycle):
    run, _, _, target = cycle(script(build=deleting("old.py")), files={"old.py": "OLD = 1\n"})
    assert run.outcome == "accepted", run.reason
    on_branch = git(target, "ls-tree", "-r", "--name-only", run.branch).split()
    assert "old.py" not in on_branch and "hello.py" in on_branch
    assert "old.py" in git(target, "log", "--stat", "--format=", f"{run.base_commit}..{run.branch}")


@pytest.mark.fr("FR-135")
def test_a_builder_asking_to_delete_a_test_is_undone_and_fails_as_a_guard(cycle):
    run, _, store, target = cycle(script(build=deleting("tests/test_hello.py")))
    assert run.outcome == "needs-me" and "build" in run.reason and "may not" in run.reason
    assert (config.pathlib.Path(run.workspace) / "tests" / "test_hello.py").is_file()


@pytest.mark.fr("FR-135")
@pytest.mark.parametrize("where", ["../outside.txt", "/tmp/../outside-absolute.txt", ".git/HEAD"])
def test_a_deletion_outside_the_checkout_or_of_gits_own_files_is_refused_as_a_guard(cycle, tmp_path, where):
    outside = tmp_path / "outside.txt"
    outside.write_text("keep me\n")
    path = str(outside) if where.startswith("/tmp") else where
    run, _, store, target = cycle(script(build=deleting(path)))
    assert run.outcome == "needs-me" and "delete" in run.reason
    assert outside.read_text() == "keep me\n"
    assert (config.pathlib.Path(run.workspace) / "hello.py").exists() is False      # the step's work was undone


@pytest.mark.fr("FR-135")
def test_every_step_that_may_change_files_is_told_how_to_ask_for_a_deletion(home, sprint, fake_notify):
    run, fake = start(sprint, [*aligned_round(), *BUILD_TO_THE_END])
    operations.approve(operations.agree(run.id).id)
    for call in fake.calls:
        told = "## Deleting a file" in call["prompt"]
        assert told == (call["capabilities"] == "read+edit"), call["persona"][:30]
    assert "delete" in " ".join((config.PROMPTS_DIR / "dialogue_planner.md").read_text().split())


# ---- FR-136: the documenter states only what the factory measured ----

@pytest.mark.fr("FR-136")
def test_the_documenter_is_given_the_measured_facts_and_told_to_claim_nothing_else(cycle):
    run, fake, store, target = cycle(script())
    documenter = next(c["prompt"] for c in fake.calls if c["persona"].startswith("# Documenter"))
    lines = len(TEST.splitlines())
    assert f"Lines of tests this run added: {lines}" in documenter
    assert "budget for one run: 300" in documenter and "Smells" in documenter
    told = " ".join((config.PROMPTS_DIR / "document.md").read_text().split())
    assert "only from these facts" in told and "never from the plan" in told
    record = git(target, "show", f"{run.branch}:{run_record.name(run)}")
    assert "## What the factory measured" in record and f"Lines of tests this run added: {lines}" in record


# ---- FR-137: the budget question and the record's table come from one computation ----

@pytest.mark.fr("FR-137")
def test_the_figure_in_the_budget_question_is_the_one_the_record_shows(home, target, fake_notify):
    toml = sprint_settings()[".factory.toml"].replace("dialogue_budget_dollars = 10.0", "dialogue_budget_dollars = 1.0")
    commit_files(target, {".factory.toml": toml})
    run, _ = start(target, [speaks([WHO], cost=0.55), planner_says(questions=[HOW_LOUD], cost=0.6),
                            speaks(blocking=(), cost=0.05), speaks(blocking=(), cost=0.07), merges(),
                            speaks(cost=0.1), planner_says(cost=0.2), speaks(blocking=()),
                            speaks(blocking=(), cost=0.3), *BUILD_TO_THE_END])
    budget = next(q for q in operations.questions(run.id).questions if q.asked_by == "factory")
    quoted = re.search(r"\$(\d+\.\d\d)", budget.question).group(1)
    assert quoted == "1.27"
    operations.answer(run.id, filled(run.id, {WHO: "a", HOW_LOUD: "b", budget.question: "yes"}))
    run = operations.approve(operations.agree(run.id).id)
    record = git(target, "show", f"{run.branch}:{run_record.name(run)}")
    rows = re.findall(r"^\| (dialogue_\w+) \| \d+ \| [^|]+ \| [^|]+ \| [^|]+ \| \$(\d+\.\d\d) \|$", record, re.M)
    assert round(sum(float(cost) for _, cost in rows), 2) == 1.87
    line = next(line for line in record.splitlines() if line.startswith("The dialogue's speakers:"))
    assert "$1.87" in line and f"${quoted}" in line and "$0.60" in line


# ---- FR-138: a test of a module the build will create imports it inside the test ----

@pytest.mark.fr("FR-138")
def test_the_test_writer_has_one_convention_for_a_module_not_yet_built_and_the_builder_clears_scaffolding():
    writer = " ".join((config.PROMPTS_DIR / "write_tests.md").read_text().split())
    assert "import it inside the test" in writer and "ImportError" in writer
    builder = " ".join((config.PROMPTS_DIR / "build.md").read_text().lower().split())
    assert "scaffolding" in builder and "importerror" in builder and "is removed" in builder


@pytest.mark.fr("FR-133")
@pytest.mark.fr("FR-130")
@pytest.mark.fr("FR-135")
def test_the_playbook_tells_an_orchestrator_about_notes_blocking_points_and_deletion():
    playbook = " ".join((config.PACKAGE_DIR.parent / "orchestrator" / "playbook.md").read_text().split())
    in_a_dialogue = playbook[playbook.index("## In a dialogue"):playbook.index("## At the approval")]
    for says in ("factory note <run>", "Only a blocking point", "never holds alignment", "`delete`",
                 "Do not `git rm`"):
        assert says in in_a_dialogue, says
