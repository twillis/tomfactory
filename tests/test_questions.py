"""Questions: an agent may ask instead of finishing. A lead answers if it can; otherwise
the question comes to the operator. Either way it is all on record (FR-061 to FR-064).
"""
import pytest

from factory import cli, operations, tables, workflow
from factory.checks import CheckResult
from factory.operations import Refused
from factory.store import open_store
from factory.workflow import Ask, StepResult, next_step
from tests.conftest import ARCHITECT, BUILD, DOCUMENT, drive_with, in_process, PLAN, REVIEW, WRITE_TESTS
from tests.fake_agent import FakeAgent

QUESTION = {"envelope": {"question": "Should the greeting end with an exclamation mark?"}}
LEAD_KNOWS = {"envelope": {"answer": "No. The plan says to return exactly 'hello'.", "confident": "yes"}}
LEAD_UNSURE = {"envelope": {"answer": "The documents do not say.", "confident": "no"}}
AFTER_BUILD = [ARCHITECT, DOCUMENT, REVIEW]


def start(target, entries):
    fake = FakeAgent(entries)
    drive_with(fake)
    run = operations.request("Add a greeting", target)
    return run, fake


def asked(result_note="Tabs or spaces?"):
    return StepResult(False, "question", CheckResult(False, result_note, name="question"))


@pytest.mark.fr("FR-061")
def test_a_question_is_one_of_the_ways_a_step_can_end():
    build = workflow.get("build", tables.STEPS)
    assert next_step(build, asked(), {"build": 1}, 3) == Ask("Tabs or spaces?")
    ended = next_step(build, asked(), {"build": 3}, 3)                  # it cannot ask for ever
    assert ended.outcome == "needs-me" and "build" in ended.reason and "Tabs or spaces?" in ended.reason
    lead = tables.LEAD
    assert (lead.capabilities, lead.may_change, lead.may_ask) == ("read", "nothing", False)   # it answers; it cannot ask


@pytest.mark.fr("FR-061")
@pytest.mark.fr("FR-062")
@pytest.mark.fr("FR-064")
def test_the_lead_answers_and_the_step_that_asked_runs_again_with_the_answer(home, target, fake_notify):
    run, fake = start(target, [{"envelope": PLAN}, WRITE_TESTS, QUESTION, LEAD_KNOWS, BUILD, *AFTER_BUILD])
    drive_with(fake)
    run = operations.approve(run.id)
    assert run.outcome == "accepted", run.reason                        # the operator was never involved

    names = [s.name for s in open_store(home).query("steps", {"run_id": run.id})]
    assert names[4:8] == ["build", "answer_question", "build", "test"]
    lead_call, second_build = fake.calls[3], fake.calls[4]
    assert "Expertise" in lead_call["persona"] and lead_call["capabilities"] == "read"
    assert "exclamation mark" in lead_call["prompt"] and PLAN["plan"] in lead_call["prompt"]
    assert "exclamation mark" in second_build["prompt"] and "return exactly 'hello'" in second_build["prompt"]

    view = operations.show(run.id)
    assert [(q.step, q.asked_by, q.answered_by) for q in view.questions] == [("build", "code_writer", "lead")]
    assert view.questions[0].question.startswith("Should the greeting") and "exactly 'hello'" in view.questions[0].answer
    kinds = [e.kind for e in open_store(home).query("events", {"run_id": run.id})]
    assert "question" in kinds and "answer" in kinds
    assert not [title for title, _ in fake_notify if "question" in title.lower()]


@pytest.mark.fr("FR-063")
@pytest.mark.fr("FR-064")
def test_a_question_the_lead_cannot_answer_comes_to_the_operator(home, target, fake_notify):
    run, fake = start(target, [{"envelope": PLAN}, WRITE_TESTS, QUESTION, LEAD_UNSURE, BUILD, *AFTER_BUILD])
    drive_with(fake)
    run = operations.approve(run.id)

    assert (run.state, run.current_step, run.outcome) == ("awaiting_approval", "build", None)
    assert fake_notify[-1] == (f"Run {run.id}: a question for you", "Should the greeting end with an exclamation mark?")
    pending = operations.show(run.id).questions[-1]
    assert (pending.asked_by, pending.answer, pending.answered_by) == ("code_writer", None, None)
    for refused in (operations.approve, lambda r: operations.revise(r, "a comment")):
        with pytest.raises(Refused, match="question"):
            refused(run.id)

    run = operations.answer(run.id, "Yes, end it with one.")
    assert run.outcome == "accepted", run.reason
    assert "Yes, end it with one." in fake.calls[4]["prompt"]
    answered = operations.show(run.id).questions[-1]
    assert (answered.answer, answered.answered_by) == ("Yes, end it with one.", "operator")
    with pytest.raises(Refused, match="no question"):
        operations.answer(run.id, "again")


@pytest.mark.fr("FR-063")
def test_a_question_during_planning_waits_and_then_the_plan_still_needs_approval(home, target, fake_notify):
    run, fake = start(target, [QUESTION, LEAD_UNSURE, {"envelope": PLAN}])
    assert (run.state, run.current_step) == ("awaiting_approval", "plan")
    with pytest.raises(Refused, match="no plan yet"):
        operations.plan(run.id)
    with pytest.raises(Refused, match="answer"):
        operations.answer(run.id, "   ")
    drive_with(fake)
    run = operations.answer(run.id, "No exclamation mark.")
    assert (run.state, run.current_step) == ("awaiting_approval", "plan")       # now the plan itself is waiting
    assert operations.plan(run.id).text == PLAN["plan"] and not [q for q in operations.show(run.id).questions if q.answer is None]


@pytest.mark.fr("FR-061")
def test_a_step_that_only_ever_asks_ends_needs_me(home, target, fake_notify):
    run, fake = start(target, [{"envelope": PLAN}, WRITE_TESTS, QUESTION, LEAD_KNOWS, QUESTION, LEAD_KNOWS, QUESTION])
    drive_with(fake)
    run = operations.approve(run.id)
    assert run.outcome == "needs-me" and "build" in run.reason and "3 times" in run.reason
    assert len(operations.show(run.id).questions) == 3


@pytest.mark.fr("FR-062")
def test_a_lead_that_fails_or_asks_back_is_treated_as_unable_to_answer(home, target, fake_notify):
    run, fake = start(target, [{"envelope": PLAN}, WRITE_TESTS, QUESTION, {"text": "no json at all"}])
    drive_with(fake)
    run = operations.approve(run.id)
    assert (run.state, run.current_step) == ("awaiting_approval", "build")      # it came to the operator


@pytest.mark.fr("FR-061")
def test_every_agent_is_told_how_to_ask_and_given_its_earlier_answers(home, target, fake_notify):
    run, fake = start(target, [{"envelope": PLAN}, WRITE_TESTS, BUILD, *AFTER_BUILD])
    drive_with(fake)
    operations.approve(run.id)
    for call in fake.calls:
        assert '"question"' in call["prompt"] and "If you cannot go on" in call["prompt"]


@pytest.mark.fr("FR-064")
def test_the_command_line_shows_and_answers_questions(home, target, fake_notify, monkeypatch, capsys):
    fake = FakeAgent([{"envelope": PLAN}, WRITE_TESTS, QUESTION, LEAD_UNSURE, BUILD, *AFTER_BUILD])
    monkeypatch.setattr(operations, "launch", in_process(fake))
    assert cli.main(["request", "Add a greeting", "--target", str(target)]) == 0
    assert cli.main(["approve"]) == 0
    capsys.readouterr()
    assert cli.main(["status"]) == 0
    assert "question for you" in capsys.readouterr().out
    assert cli.main(["approve"]) == 1 and "question" in capsys.readouterr().err
    assert cli.main(["answer", "Yes, with one."]) == 0
    capsys.readouterr()
    assert cli.main(["show"]) == 0
    out = capsys.readouterr().out
    assert "Should the greeting end with an exclamation mark?" in out and "Yes, with one." in out and "operator" in out
