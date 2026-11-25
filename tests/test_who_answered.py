"""Who answered, what the tests said, three prompt lines and the backlog's owner (FR-139 to FR-144; run 98).

An answer is recorded as the operator's or the orchestrator's, as it really was, and every text made from it says
so; only the operator's own words count as his. The record says why a check sent work back, and the documenter and
the retro are given what the final tests said. The dialogue's questions stand alone, the plan check asks whether a
wrong default fails loudly, and the planner quotes the backlog. Only the architect changes the backlog.
"""
import re
import sqlite3

import pytest

from factory import cli, config, dialogue, operations, records, run_record
from factory.operations import Refused
from factory.store import open_store
from tests.conftest import (BUILD, DOCUMENT, PLAN, WRITE_TESTS, WRONG, commit_files, drive_with, git, record, script,
                            sprint_settings)
from tests.test_dialogue import BUILD_TO_THE_END, HOW_LOUD, MEASURE, WHO, aligned_round, filled, planner_says, \
    speaks, start
from tests.test_questions import AFTER_BUILD
from tests.test_tuning import SAME, same_from_two

ASK_TO_MEASURE = {"envelope": {"measure": MEASURE}}


@pytest.fixture
def sprint(target):
    return commit_files(target, sprint_settings())


def asked(home, run):
    return open_store(home).query("questions", {"run_id": run.id})


# ---- FR-139: an answer is the operator's or the orchestrator's ----

@pytest.mark.fr("FR-139")
@pytest.mark.parametrize("by, recorded", [([], "operator"), (["--by", "orchestrator"], "orchestrator"),
                                          (["--by", "operator"], "operator")])
def test_factory_answer_records_who_answered(home, target, fake_notify, by, recorded):
    run, fake = start(target, [{"envelope": PLAN}, WRITE_TESTS, ASK_TO_MEASURE, BUILD, *AFTER_BUILD])
    drive_with(fake)
    operations.approve(run.id)
    assert cli.main(["answer", *by, "Python 3.13.1, measured"]) == 0
    assert asked(home, run)[-1].answered_by == recorded


@pytest.mark.fr("FR-139")
def test_an_answer_from_anyone_else_is_refused(home, target, fake_notify):
    run, fake = start(target, [{"envelope": PLAN}, WRITE_TESTS, ASK_TO_MEASURE, BUILD, *AFTER_BUILD])
    drive_with(fake)
    operations.approve(run.id)
    with pytest.raises(Refused, match="the operator's or the orchestrator's"):
        operations.answer(run.id, "It is.", by="lead")
    assert asked(home, run)[-1].answer is None


@pytest.mark.fr("FR-139")
def test_in_a_batch_each_answer_may_say_who_gave_it_and_a_plain_one_is_the_default(home, sprint, fake_notify):
    run, _ = start(sprint, [speaks([WHO]), planner_says(questions=[HOW_LOUD], measure=[MEASURE]),
                            speaks(blocking=()), speaks(blocking=()), lambda call: {"envelope": {"merged": []}},
                            *aligned_round()])
    text = filled(run.id, {WHO: "a", HOW_LOUD: "b", MEASURE: "Python 3.13.1, measured"})
    at = text.index(MEASURE)
    text = text[:at] + text[at:].replace("answer:", "answer (orchestrator):", 1)
    operations.answer(run.id, text)
    assert {q.question: q.answered_by for q in asked(home, run)} == {
        WHO: "operator", HOW_LOUD: "operator", MEASURE: "orchestrator"}


@pytest.mark.fr("FR-139")
@pytest.mark.parametrize("marker, says", [("answer (orchestrator):", None), ("answer (lead):", "lead")])
def test_a_batch_marker_names_the_orchestrator_or_is_refused(home, sprint, fake_notify, marker, says):
    run, _ = start(sprint, [speaks([WHO]), planner_says(questions=[HOW_LOUD]), speaks(blocking=()),
                            speaks(blocking=()), lambda call: {"envelope": {"merged": []}}, *aligned_round()])
    text = filled(run.id, {WHO: "a", HOW_LOUD: "b"}).replace("answer:", marker)
    if says:
        with pytest.raises(Refused, match=says):
            operations.answer(run.id, text, by="operator")
        assert all(q.answer is None for q in asked(home, run))
    else:
        operations.answer(run.id, text, by="operator")
        assert {q.answered_by for q in asked(home, run)} == {"orchestrator"}


@pytest.mark.fr("FR-139")
def test_a_merged_question_gets_the_answerer_of_the_one_it_was_merged_into(home, sprint, fake_notify):
    run, _ = start(sprint, same_from_two(aligned_round()))
    operations.answer(run.id, "b, a guest", by="orchestrator")
    kept, duplicate = asked(home, run)
    assert [(q.question, q.answered_by) for q in (kept, duplicate)] == [(WHO, "orchestrator"), (SAME, "orchestrator")]
    said = dialogue.transcript(open_store(home), run)
    assert said.count("b, a guest") == 1                              # answered once, and printed once
    assert f"Asked (Q{duplicate.id}): {SAME}\n  The same as another agent's question: merged into Q{kept.id}" in said


@pytest.mark.fr("FR-139")
def test_a_home_made_before_keeps_its_answers_and_may_record_the_orchestrators(home):
    from factory import store as store_module
    db = sqlite3.connect(home / "factory.db")
    db.executescript(store_module.BASE)
    db.execute("INSERT INTO runs (request, target, base_commit, state, created_at) VALUES ('r', '/t', 'c', 'planning',"
               " 'now')")
    db.execute("INSERT INTO questions (run_id, step, asked_by, question, answer, answered_by, asked_at, answered_at)"
               " VALUES (1, 'build', 'code_writer', 'Tabs?', 'Spaces.', 'operator', 'then', 'then')")
    db.execute("PRAGMA user_version = 2")          # brought up through every migration, the widening last
    db.commit()
    db.close()
    gw = open_store(home)
    kept = gw.query("questions", {"run_id": 1})[0]
    assert (kept.question, kept.answer, kept.answered_by, kept.round, kept.measure) == (
        "Tabs?", "Spaces.", "operator", None, False)
    later = records.ask(gw, 1, "build", "code_writer", "Which version?", measure=True)
    assert records.answer(gw, later.id, "3.13", "orchestrator").answered_by == "orchestrator"
    with pytest.raises(sqlite3.IntegrityError):
        records.answer(gw, later.id, "3.13", "someone")


@pytest.mark.fr("FR-139")
def test_the_playbook_says_to_answer_measurements_as_the_orchestrator_and_his_answers_as_his():
    playbook = " ".join((config.PACKAGE_DIR.parent / "orchestrator" / "playbook.md").read_text().split())
    for section, ends in (("## While a run is open", "## In a dialogue"), ("## In a dialogue", "## At the approval")):
        said = playbook[playbook.index(section):playbook.index(ends)]
        assert "--by orchestrator" in said, section
    in_a_dialogue = playbook[playbook.index("## In a dialogue"):playbook.index("## At the approval")]
    assert "answer (orchestrator):" in in_a_dialogue and "as his" in in_a_dialogue


# ---- FR-140: every text made from an answer says who really answered; only his own words count as his ----

@pytest.mark.fr("FR-140")
def test_the_orchestrators_answers_are_named_as_its_and_are_not_the_operators_feedback(home, sprint, fake_notify,
                                                                                          capsys):
    run, fake = start(sprint, [speaks([WHO]), planner_says(measure=[MEASURE]), speaks(blocking=()),
                               speaks(blocking=()), lambda call: {"envelope": {"merged": []}}, *aligned_round(),
                               *BUILD_TO_THE_END])
    text = filled(run.id, {WHO: "b, a visitor", MEASURE: "Python 3.13.1, measured"})
    at = text.index(MEASURE)
    operations.answer(run.id, text[:at] + text[at:].replace("answer:", "answer (orchestrator):", 1))
    run = operations.approve(operations.agree(run.id).id)
    assert run.outcome == "accepted", run.reason
    retro = next(c["prompt"] for c in fake.calls if c["prompt"].startswith("# Task: the sprint's retro"))
    feedback = retro[retro.index("in his own words"):retro.index("What the final review")]
    assert "b, a visitor" in feedback and "Python 3.13.1" not in feedback
    converge = next(c["prompt"] for c in fake.calls if c["prompt"].startswith("# Task: is what was built"))
    assert "The orchestrator answered: Python 3.13.1, measured" in converge
    assert "The operator answered: b, a visitor" in converge
    record = git(sprint, "show", f"{run.branch}:{run_record.name(run)}")
    assert "Answered by the orchestrator: Python 3.13.1, measured" in record
    assert "Answered by the operator: b, a visitor" in record
    capsys.readouterr()
    cli.main(["show", str(run.id)])
    assert "orchestrator answered: Python 3.13.1, measured" in capsys.readouterr().out


@pytest.mark.fr("FR-140")
@pytest.mark.fr("FR-105")
@pytest.mark.parametrize("answered_by, counted", [("lead", 1), ("operator", 0), ("orchestrator", 0)])
def test_a_step_that_asked_counts_as_an_attempt_only_when_the_lead_answered(home, answered_by, counted):
    gw = open_store(home)
    run = gw.insert("runs", {"request": "r", "target": "/t", "base_commit": "c", "state": "working",
                             "created_at": "2026-11-25T10:00:00.000Z"})
    gw.insert("steps", {"run_id": run.id, "name": "build", "kind": "agent", "attempt": 1, "asked": "",
                        "passed": False, "failure": "question", "started_at": "2026-11-25T10:01:00.000Z",
                        "ended_at": "2026-11-25T10:03:00.000Z"})
    question = records.ask(gw, run.id, "build", "code_writer", "Which version?", measure=True)
    gw.update("questions", {"id": question.id}, {"asked_at": "2026-11-25T10:02:00.000Z"})
    records.answer(gw, question.id, "3.13", answered_by)
    assert records.attempts_counted(gw, run.id, "build") == counted


# ---- FR-141: the record says why a check sent the work back ----

REPORTED = {".factory.toml": config.DEFAULT_FACTORY_TOML
            .replace('test_command = "python -m pytest -q -p no:cacheprovider"',
                     'test_command = "python -m pytest -q -p no:cacheprovider --junitxml=report.xml"')
            .replace('test_report = ""', 'test_report = "report.xml"'),
            ".gitignore": config.DEFAULT_GITIGNORE + "report.xml\n"}


@pytest.mark.fr("FR-141")
def test_the_record_and_the_builder_are_told_which_tests_the_report_names_as_failing(cycle):
    first = dict(BUILD, files={"hello.py": WRONG})
    run, fake, _, target = cycle(script(build=[first, BUILD]), files=REPORTED)
    record = git(target, "show", f"{run.branch}:{run_record.name(run)}")
    row = next(line for line in record.splitlines() if line.startswith("| test | 1 |"))
    assert row == ("| test | 1 | check: tests_pass (failed: tests.test_hello::test_greets,"
                   " tests.test_hello::test_empty_name_still_greets) |")
    second_build = [c["prompt"] for c in fake.calls if c["prompt"].startswith("# Task: build the change")][-1]
    assert "The test report names as failing: tests.test_hello::test_greets (" in second_build
    assert "goodbye" in second_build[second_build.index("The test report names"):]


@pytest.mark.fr("FR-141")
def test_with_no_test_report_the_record_gives_the_checks_message_shortened(cycle):
    first = dict(BUILD, files={"hello.py": WRONG})
    run, _, _, target = cycle(script(build=[first, BUILD]))
    record = git(target, "show", f"{run.branch}:{run_record.name(run)}")
    row = next(line for line in record.splitlines() if line.startswith("| test | 1 |"))
    assert row.startswith("| test | 1 | check: tests_pass (the tests fail:")
    assert row.count(" | ") == 2 and len(row) <= 200, row             # one cell, on one line, shortened


@pytest.mark.fr("FR-141")
@pytest.mark.parametrize("failing, shown, messages, named", [
    (None, 5, False, ""),
    ({"count": 0, "tests": []}, 5, False, ""),
    ({"count": 2, "tests": [{"test": "a::x", "message": "assert 1 == 2"}, {"test": "b::y", "message": ""}]}, 5, True,
     "a::x (assert 1 == 2), b::y"),
    ({"count": 30, "tests": [{"test": f"a::t{n}", "message": "boom"} for n in range(20)]}, 3, False,
     "a::t0, a::t1, a::t2 and 27 more"),
])
def test_the_failing_tests_are_named_capped_and_counted(failing, shown, messages, named):
    assert run_record.failing_tests(failing, shown=shown, messages=messages) == named


# ---- FR-142: the documenter and the retro are given what the final tests said ----

@pytest.mark.fr("FR-142")
def test_the_documenter_and_the_retro_are_given_the_final_test_steps_result(home, sprint, fake_notify):
    first = dict(BUILD, files={"hello.py": WRONG})
    run, fake = start(sprint, [*aligned_round(), WRITE_TESTS, first, BUILD, *BUILD_TO_THE_END[2:]])
    run = operations.approve(operations.agree(run.id).id)
    assert run.outcome == "accepted", run.reason
    said = re.compile(r"The tests after the build, as the factory ran them \(test, attempt 2\): passed\."
                      r" The test command's last line: `[^`\n]*\d+ passed")
    for task in ("# Task: document the change", "# Task: the sprint's retro"):
        prompt = next(c["prompt"] for c in fake.calls if c["prompt"].startswith(task))
        assert said.search(prompt), task
    assert said.search(git(sprint, "show", f"{run.branch}:{run_record.name(run)}"))


# ---- FR-143: three prompt lines ----

@pytest.mark.fr("FR-143")
@pytest.mark.parametrize("file, says", [
    ("prompts/fragments/dialogue.md", ("must stand alone", "the same setup", "name its referents")),
    ("prompts/dialogue_check.md", ("default or derived value", "loudly or silently", "B6")),
    ("personas/planner.md", ("quoting its text", "never by its line number")),
])
def test_the_prompts_say_what_run_98_showed_they_must(file, says):
    text = " ".join((config.PACKAGE_DIR.parent / file).read_text().split())
    for phrase in says:
        assert phrase in text, phrase


# ---- FR-144: the architect is the backlog's one owner ----

@pytest.mark.fr("FR-144")
@pytest.mark.parametrize("moved_to, written, owned", [
    (None, "docs/backlog.md", True),
    (None, "docs/backlog-done.md", True),
    (None, "docs/greeting.md", False),
    ("docs/todo.md", "docs/todo.md", True),                     # where the codebase says its backlog is
    ("docs/todo.md", "docs/backlog.md", False),
])
def test_only_the_architect_may_change_the_backlog_and_the_documenter_is_undone(cycle, moved_to, written, owned):
    toml = config.DEFAULT_FACTORY_TOML
    architect = None
    if moved_to:
        toml = toml.replace('backlog_file = "docs/backlog.md"', f'backlog_file = "{moved_to}"')
        architect = {"envelope": {"summary": "sound", "suggestions": ["one home"], "warnings": []},
                     "files": {moved_to: "- one home\n"}}
    documenter = dict(DOCUMENT, files={**DOCUMENT["files"], written: "- closed by the documenter\n"})
    entries = script(document=documenter, **({"architecture_review": architect} if architect else {}))
    run, _, store, _ = cycle(entries, files={".factory.toml": toml} if toml != config.DEFAULT_FACTORY_TOML else None)
    assert record(store, run, "architecture_review").passed                  # the architect may write it
    if owned:
        assert run.outcome == "needs-me" and "document" in run.reason
        assert written in next(c["note"] for c in record(store, run, "document").checks if not c["passed"])
    else:
        assert run.outcome == "accepted", run.reason


@pytest.mark.fr("FR-144")
@pytest.mark.parametrize("file, says", [
    ("prompts/document.md", ("{{backlog_file}}", "{{backlog_done_file}}", "the architect's")),
    ("prompts/architecture_review.md", ("{{backlog_file}}", "{{backlog_done_file}}", "names as answered")),
    ("personas/planner.md", ("backlog entries this run answers", "the architect")),
    ("prompts/fragments/dialogue.md", ("backlog entries the run answers", "the architect")),
])
def test_the_prompts_say_the_architect_closes_what_the_plan_names(file, says):
    text = " ".join((config.PACKAGE_DIR.parent / file).read_text().split())
    for phrase in says:
        assert phrase in text, phrase
