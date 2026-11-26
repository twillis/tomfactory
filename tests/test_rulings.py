"""The operator's rulings are applied, not asked (FR-154 to FR-157).

From bttr_erp's run 103: a ruling of 2026-11-21 was quoted in the ask and in the standing documents, the planner
applied it in part and left the rest for the backlog, and the plan check asked the operator whether to apply the
rest. The operator: "Shouldn't the team have been aware of the rulings?"
"""
import pytest

from factory import checks, config, operations, tables, workflow
from factory.store import open_store
from tests.conftest import aligned_round, commit_files, drive_with, planner_says, speaks, sprint_settings
from tests.fake_agent import FakeAgent

SPEAKERS = ["dialogue_analyst", "dialogue_planner", "dialogue_architect", "dialogue_check"]
WHO = "Who is greeted first? a) you  b) a visitor"
HOW_LOUD = "Should it shout? a) yes  b) no"
WHY_WHO = "requirements/rulings.md has no ruling on who is greeted; the run order is silent on it"


@pytest.fixture
def sprint(target):
    return commit_files(target, sprint_settings())


def start(target, entries, request="Add a greeting"):
    drive_with(FakeAgent(entries))
    return operations.request(request, target)


def answered(run_id, answer="a") -> str:
    """The waiting batch, with one question in it, answered."""
    return operations.questions(run_id).text.replace("\nanswer:\n", f"\nanswer: {answer}\n")


def text_of(file) -> str:
    return " ".join((config.PACKAGE_DIR.parent / file).read_text().split())


# ---- FR-154: a point a ruling settles is applied and cited, never asked ----

@pytest.mark.fr("FR-154")
@pytest.mark.parametrize("file, says", [
    ("prompts/fragments/dialogue.md", ("a ruling settles is never put to the asker", "apply it whole",
                                       "who made it, when, and where it is recorded")),
    ("prompts/dialogue_analyst.md", ("never ask whether the asker wants a ruling otherwise",)),
    ("prompts/dialogue_planner.md", ("never left for the backlog or a later run",)),
    ("personas/planner.md", ("never left for the backlog", "applied whole")),
])
def test_every_speaker_is_told_to_apply_and_cite_a_ruling_not_ask_about_it(file, says):
    text = text_of(file)
    for phrase in says:
        assert phrase in text, phrase


@pytest.mark.fr("FR-154")
def test_the_analyst_is_no_longer_told_to_put_what_the_record_says_to_the_asker():
    assert "only when the asker may want it otherwise" not in text_of("prompts/dialogue_analyst.md")


# ---- FR-155: a ruling applied in part is blocking ----

@pytest.mark.fr("FR-155")
@pytest.mark.parametrize("file, says", [
    ("prompts/dialogue_check.md", ("applies a ruling only in part", "is blocking",
                                   "never a note and never a question")),
    ("prompts/dialogue_architect.md", ("applies a ruling only in part",)),
    ("personas/reviewer.md", ("applied in part",)),
])
def test_a_ruling_applied_in_part_is_blocking_for_the_plan_check_and_the_architect(file, says):
    text = text_of(file)
    for phrase in says:
        assert phrase in text, phrase


# ---- FR-156: a question asked anyway says why no ruling settles it, and the asker sees it ----

def context_for(step, said):
    return checks.CheckContext(run=None, step=workflow.get(step, tables.SPRINT_STEPS), checkout=None,
                               target_config=config.TargetConfig(), changed=set(), envelope=said, before="")


@pytest.mark.fr("FR-156")
@pytest.mark.parametrize("step", SPEAKERS)
def test_every_speaker_gives_rulings_checked_and_is_held_to_it(step):
    entry = workflow.get(step, tables.SPRINT_STEPS)
    assert entry.envelope.get("rulings_checked") == "list"
    assert "rulings_checked" in entry.checks
    assert "- `rulings_checked`: one item per question" in (config.PROMPTS_DIR / f"{step}.md").read_text()


@pytest.mark.fr("FR-156")
@pytest.mark.parametrize("said, passed", [
    ({"questions": [], "measure": [], "rulings_checked": []}, True),
    ({"questions": [WHO], "measure": [], "rulings_checked": [WHY_WHO]}, True),
    ({"questions": [WHO], "measure": [], "rulings_checked": []}, False),                    # asked, and no reason
    ({"questions": [WHO, HOW_LOUD], "measure": [], "rulings_checked": [WHY_WHO]}, False),   # one short
    ({"questions": [WHO], "measure": [], "rulings_checked": [WHY_WHO, "another"]}, False),  # one too many
    ({"questions": [WHO], "measure": [], "rulings_checked": ["  "]}, False),                # a blank reason
    ({"questions": [], "measure": ["What does `python --version` print?"], "rulings_checked": []}, True),
])
def test_a_reply_that_asks_without_saying_why_no_ruling_settles_it_is_not_accepted(said, passed):
    for step in SPEAKERS:
        result = checks.get("rulings_checked")(context_for(step, said))
        assert result.passed is passed, step
        assert passed or "rulings_checked" in result.note


@pytest.mark.fr("FR-156")
def test_a_speaker_that_asks_without_a_reason_is_sent_back_and_told_why(home, sprint, fake_notify):
    bare = {"envelope": {"questions": [WHO], "measure": [], "rulings_checked": []}}
    seen = {}

    def analyst_again(call):
        seen["prompt"] = call["prompt"]
        return speaks([WHO])

    run = start(sprint, [bare, analyst_again, planner_says(), speaks(blocking=()), speaks(blocking=())])
    assert "1 question(s) and 0 item(s) in `rulings_checked`" in seen["prompt"]     # the failure, told back
    assert [q.question for q in open_store(home).query("questions", {"run_id": run.id})] == [WHO]


@pytest.mark.fr("FR-156")
def test_the_batch_shows_each_question_with_why_no_ruling_settles_it_on_the_line_before(home, sprint, fake_notify):
    analyst = speaks([WHO])
    analyst["envelope"]["rulings_checked"] = [WHY_WHO]
    run = start(sprint, [analyst, planner_says(), speaks(blocking=()), speaks(blocking=()), *aligned_round()])
    lines = operations.questions(run.id).text.splitlines()
    at = next(i for i, line in enumerate(lines) if line.endswith(WHO))
    assert lines[at - 1] == f"# Checked against the rulings: {WHY_WHO}"
    operations.answer(run.id, answered(run.id))
    assert [q.answer for q in open_store(home).query("questions", {"run_id": run.id})] == ["a"]


@pytest.mark.fr("FR-156")
def test_the_transcript_keeps_why_no_ruling_settled_each_question(home, sprint, fake_notify):
    analyst = speaks([WHO])
    analyst["envelope"]["rulings_checked"] = [WHY_WHO]
    seen = {}

    def analyst_in_round_2(call):
        seen["prompt"] = call["prompt"]
        return speaks()

    run = start(sprint, [analyst, planner_says(), speaks(blocking=()), speaks(blocking=()),
                         analyst_in_round_2, planner_says(), speaks(blocking=()), speaks(blocking=())])
    operations.answer(run.id, answered(run.id))
    assert f"Checked against the rulings: {WHY_WHO}" in seen["prompt"]


@pytest.mark.fr("FR-156")
def test_a_question_asked_before_speakers_gave_a_reason_is_shown_without_one(home, sprint, fake_notify):
    run = start(sprint, [speaks([WHO]), planner_says(), speaks(blocking=()), speaks(blocking=())])
    store = open_store(home)
    reply = next(s for s in store.query("steps", {"run_id": run.id}) if s.name == "dialogue_analyst")
    store.update("steps", {"id": reply.id}, {"produced": {"questions": [WHO], "measure": []}})   # an older reply
    text = operations.questions(run.id).text
    assert WHO in text and "Checked against the rulings" not in text


# ---- FR-157: an index of rulings in the standing documents is named first ----

@pytest.mark.fr("FR-157")
@pytest.mark.parametrize("files, first", [
    ({"requirements/rulings.md": "- 2026-11-21: a ruling\n", "requirements/run-order.md": "rows\n"},
     ".factory-main/requirements/rulings.md"),
    ({"requirements/decisions/rulings.md": "- a ruling\n", "requirements/run-order.md": "rows\n"},
     ".factory-main/requirements/decisions/rulings.md"),
    ({"requirements/run-order.md": "rows\n"}, None),
])
def test_an_index_of_rulings_among_the_standing_documents_is_named_to_be_read_first(home, sprint, fake_notify, files,
                                                                                    first):
    commit_files(sprint, files)
    seen = {}

    def analyst(call):
        seen["prompt"] = call["prompt"]
        return speaks()

    start(sprint, [analyst, planner_says(), speaks(blocking=()), speaks(blocking=())])
    prompt = seen["prompt"]
    if first is None:
        assert "Read first the codebase's index of rulings" not in prompt
    else:
        said = f"Read first the codebase's index of rulings, `{first}`"
        assert said in prompt
        assert prompt.index(said) < prompt.index(".factory-main/requirements/run-order.md")


@pytest.mark.fr("FR-157")
def test_the_speakers_are_told_to_read_an_index_of_rulings_first_where_there_is_one():
    assert "an index of rulings" in text_of("prompts/fragments/dialogue.md")
    assert "bttr" not in text_of("prompts/fragments/dialogue.md")


# ---- FR-159: plan for what the change touches, and presume the rest works ----

@pytest.mark.fr("FR-159")
@pytest.mark.parametrize("phrase", [
    "architecture overview", "presumed to work", "only when the change cannot be planned without it",
    "a backlog note, never a blocking point", "to the cases this change touches", "what changed in the draft",
])
def test_every_speaker_is_told_to_plan_for_what_the_change_touches(phrase):
    assert phrase in text_of("prompts/fragments/dialogue.md")


@pytest.mark.fr("FR-159")
@pytest.mark.parametrize("file", ["prompts/dialogue_planner.md", "prompts/dialogue_check.md",
                                  "prompts/dialogue_architect.md"])
def test_a_ruling_is_applied_whole_to_what_the_change_touches(file):
    assert "the change touches" in text_of(file)
