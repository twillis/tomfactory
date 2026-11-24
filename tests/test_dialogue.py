"""Planning is a dialogue from an ask to an executable plan (FR-119 to FR-129, from specification 005).

On a sprint codebase an ask starts a dialogue: each round the analyst, the planner, the architect and the plan check
all speak, each with its own batch for the asker; the run waits for the asker's answers, given as one batch; the
planner proposes "aligned" with the plan and an estimate; the asker agrees; approval is a separate decision.
"""
import stat

import pytest

from factory import cli, config, dialogue, operations, records, run_record, tables, workflow
from factory.operations import Refused
from factory.store import open_store
from tests.conftest import (ARCHITECT, BUILD, CODE, DOCUMENT, PLAN, REVIEW, TEST, WRITE_TESTS, aligned_round,
                            commit_files, drive_with, git, planner_says, speaks, sprint_settings, to_the_end)
from tests.fake_agent import FakeAgent

SPEAKERS = ["dialogue_analyst", "dialogue_planner", "dialogue_architect", "dialogue_check"]
CONVERGE = {"envelope": {"verdict": "accept", "unbuilt": [], "details": [], "requirement_changes": [],
                         "reasons": ["it matches the plan"], "ideals_broken": []}}
RETRO = {"envelope": {"summary": "fine", "worked": [], "did_not": [], "opportunities": [], "threats": []}}
BUILD_TO_THE_END = [WRITE_TESTS, BUILD, ARCHITECT, DOCUMENT, CONVERGE, RETRO]

WHO = "Who is greeted first? a) you  b) a visitor"
HOW_LOUD = "Should it shout? a) yes  b) no"
MEASURE = "What does `python --version` print in the test environment?"


@pytest.fixture
def sprint(target):
    return commit_files(target, sprint_settings())


def start(target, entries, request="Add a greeting", **kw):
    fake = drive_with(FakeAgent(entries))
    return operations.request(request, target, **kw), fake


def names(home, run):
    return [s.name for s in open_store(home).query("steps", {"run_id": run.id})]


def prompts_of(fake, persona):
    return [call["prompt"] for call in fake.calls if call["persona"].startswith(persona)]


def filled(run_id, answers):
    """The waiting batch as `factory questions` gives it, with each answer written under its question."""
    text = operations.questions(run_id).text
    for question, answer in answers.items():
        start = text.index(question)
        at = text.index("answer:", start) + len("answer:")
        text = text[:at] + " " + answer + text[at:]
    return text


# ---- FR-119: an ask starts a dialogue, in place of plan, check_plan and amend_plan ----

@pytest.mark.fr("FR-119")
@pytest.mark.parametrize("kind", ["change", "tidy-code", "tidy-tests"])
def test_on_a_sprint_codebase_an_ask_starts_a_dialogue_in_place_of_the_plan_and_its_check(kind):
    table = tables.table_for(False, kind, "sprint")
    assert [s.name for s in table][:4] == SPEAKERS
    assert all(s.dialogue for s in table[:4]) and not any(s.dialogue for s in table[4:])
    assert not {"plan", "check_plan", "amend_plan"} & {s.name for s in table}
    waits = [s for s in table if s.on_pass == workflow.WAIT]
    assert [s.name for s in waits] == ["dialogue_check"]                 # the one wait: the dialogue's
    assert waits[0].revise_from == "dialogue_analyst" and waits[0].on_approve == "baseline"


@pytest.mark.fr("FR-119")
def test_the_plain_and_spec_kit_cycles_and_spikes_have_no_dialogue():
    for table in (tables.STEPS, tables.SPEC_KIT_STEPS, tables.TIDY_CODE, tables.TIDY_TESTS, tables.SPIKE_STEPS):
        assert not any(s.dialogue for s in table)
    assert tables.table_for(False, "change", "auto")[0].name == "plan"
    assert tables.table_for(False, "spike", "sprint") is tables.SPIKE_STEPS
    assert not (config.PROMPTS_DIR / "check_plan.md").exists() and not (config.PROMPTS_DIR / "amend_plan.md").exists()


@pytest.mark.fr("FR-119")
def test_a_whole_run_from_an_ask_through_the_dialogue_to_the_end(home, sprint, fake_notify):
    run, waits = to_the_end(sprint, FakeAgent([*aligned_round(), *BUILD_TO_THE_END]))
    assert run.outcome == "accepted", run.reason
    assert names(home, run)[:4] == SPEAKERS and waits == 1


# ---- FR-120: rounds, every speaker side by side, each with its own batch ----

@pytest.mark.fr("FR-120")
@pytest.mark.parametrize("said, in_a_row, outcome", [
    ([{"questions": ["a?"]}, {}, {}, {}], 0, "questions"),
    ([{}, {"measure": ["b?"]}, {}, {}], 0, "questions"),
    ([{}, {}, {"points": ["c"], "questions": ["d?"]}, {}], 0, "questions"),         # the asker is asked first
    ([{}, {}, {"points": ["c"]}, {}], 0, "points"),                                # the agents go round again
    ([{}, {}, {}, {"points": ["c"]}], 2, "stuck"),                                 # at the limit: shown to the asker
    ([{}, {"aligned": "yes"}, {"points": []}, {"points": []}], 0, "aligned"),
])
def test_how_a_round_ends(said, in_a_row, outcome):
    assert workflow.round_outcome(said, in_a_row, 3) == outcome
    assert workflow.after_round(outcome, "dialogue_analyst") == (
        workflow.Run("dialogue_analyst") if outcome == "points" else workflow.Wait())


@pytest.mark.fr("FR-120")
def test_every_speaker_speaks_in_a_round_and_the_run_waits_with_each_ones_batch_kept_apart(home, sprint, fake_notify):
    run, fake = start(sprint, [speaks([WHO]), planner_says(questions=[HOW_LOUD]), speaks(points=()),
                               speaks(points=())])
    assert names(home, run) == SPEAKERS and run.state == "awaiting_approval"
    asked = open_store(home).query("questions", {"run_id": run.id})
    assert [(q.step, q.asked_by, q.round) for q in asked] == [("dialogue_analyst", "analyst", 1),
                                                              ("dialogue_planner", "planner", 1)]
    text = operations.questions(run.id).text
    assert text.index("the analyst asks") < text.index(WHO) < text.index("the planner asks") < text.index(HOW_LOUD)
    assert fake_notify[-1][0] == f"Run {run.id}: answers to 2 questions from the analyst and the planner"


@pytest.mark.fr("FR-120")
def test_the_next_round_is_given_every_question_and_answer_so_far(home, sprint, fake_notify):
    run, fake = start(sprint, [speaks([WHO]), planner_says(questions=[HOW_LOUD]), speaks(points=()),
                               speaks(points=()), *aligned_round()])
    operations.answer(run.id, filled(run.id, {WHO: "a", HOW_LOUD: "b, never"}))
    later = fake.calls[4:8]
    assert len(later) == 4
    for call in later:
        assert WHO in call["prompt"] and "b, never" in call["prompt"] and "round 2" in call["prompt"].lower()


@pytest.mark.fr("FR-120")
def test_the_first_round_asks_open_questions_before_any_reading_of_the_ask(home, sprint, fake_notify):
    run, fake = start(sprint, aligned_round())
    analyst = fake.calls[0]["prompt"]
    assert "This is round 1" in analyst and "open questions" in analyst
    assert "before you show any reading of the ask" in (config.PROMPTS_DIR / "dialogue_analyst.md").read_text()


@pytest.mark.fr("FR-120")
def test_the_architect_and_the_plan_check_are_shown_the_planners_plan_from_their_own_round(home, sprint, fake_notify):
    run, fake = start(sprint, aligned_round("Add hello.py; greet() returns hello."))
    for persona in ("# Architect", "# Reviewer"):
        assert "Add hello.py; greet() returns hello." in prompts_of(fake, persona)[0]


@pytest.mark.fr("FR-120")
def test_points_for_the_planner_alone_go_round_again_without_the_asker(home, sprint, fake_notify):
    point = "greet() is named hello() in the plan's test; use one name"
    run, fake = start(sprint, [speaks(), planner_says(), speaks(points=[point]), speaks(points=()),
                               *aligned_round()])
    assert names(home, run) == SPEAKERS * 2 and run.state == "awaiting_approval"
    assert point in fake.calls[5]["prompt"]                                   # the planner, in round 2
    assert operations.waiting(run.id)["for"] == "agreement"


@pytest.mark.fr("FR-120")
def test_points_still_raised_after_the_attempt_limit_of_rounds_are_put_to_the_asker(home, sprint, fake_notify):
    point = "the plan never says where hello.py goes"
    stubborn = [speaks(), planner_says(), speaks(points=[point]), speaks(points=())]
    run, fake = start(sprint, stubborn * 2, attempts=2)
    assert names(home, run) == SPEAKERS * 2
    waiting = operations.questions(run.id).questions
    assert len(waiting) == 1 and waiting[0].asked_by == "factory" and point in waiting[0].question


@pytest.mark.fr("FR-120")
def test_a_measurement_is_part_of_the_batch_and_answered_with_it(home, sprint, fake_notify):
    run, fake = start(sprint, [speaks([WHO]), planner_says(measure=[MEASURE]), speaks(points=()),
                               speaks(points=()), *aligned_round()])
    waiting = operations.waiting(run.id)
    assert waiting["measure"] and "a measurement" in waiting["says"]
    assert "asks for a measurement" in operations.questions(run.id).text
    operations.answer(run.id, filled(run.id, {WHO: "a", MEASURE: "Python 3.13.1, measured"}))
    assert "Python 3.13.1, measured" in fake.calls[5]["prompt"]


# ---- FR-121: answering a batch, in the editor or from a file or stdin ----

@pytest.mark.fr("FR-121")
def test_a_batch_is_written_with_a_place_for_each_answer_and_read_back(home, sprint, fake_notify):
    run, _ = start(sprint, [speaks([WHO, HOW_LOUD]), planner_says(questions=["Which file? a) hello.py  b) app.py"]),
                            speaks(points=()), speaks(points=())])
    batch = operations.questions(run.id)
    assert batch.text.count("\nanswer:\n") == 3 and all(f"[Q{q.id}]" in batch.text for q in batch.questions)
    text = filled(run.id, {WHO: "a", HOW_LOUD: "no\n# a note to myself", "Which file?": "a"})
    assert dialogue.parse_batch(text, batch.questions) == dict(zip([q.id for q in batch.questions], ["a", "no", "a"]))


@pytest.mark.fr("FR-121")
@pytest.mark.parametrize("change, says", [
    (lambda text, ids: text, "has no answer"),
    (lambda text, ids: text.replace("answer:", "answer: yes") + "\n[Q999] made up\nanswer: x\n", "Q999"),
])
def test_a_batch_with_an_answer_missing_or_a_question_not_asked_is_refused(home, sprint, fake_notify, change, says):
    run, _ = start(sprint, [speaks([WHO]), planner_says(questions=[HOW_LOUD]), speaks(points=()), speaks(points=())])
    batch = operations.questions(run.id)
    with pytest.raises(Refused, match=says):
        operations.answer(run.id, change(batch.text, [q.id for q in batch.questions]))
    assert records.pending_question(open_store(home), run.id) is not None         # nothing was recorded


@pytest.mark.fr("FR-121")
def test_factory_answer_with_no_words_opens_the_batch_in_the_editor(home, sprint, fake_notify, tmp_path, monkeypatch):
    run, fake = start(sprint, [speaks([WHO]), planner_says(questions=[HOW_LOUD]), speaks(points=()),
                               speaks(points=()), *aligned_round()])
    editor = tmp_path / "editor"
    editor.write_text("#!/bin/sh\nsed -i 's/^answer:$/answer: b/' \"$1\"\n")
    editor.chmod(editor.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("EDITOR", str(editor))
    assert cli.main(["answer"]) == 0
    answered = open_store(home).query("questions", {"run_id": run.id})
    assert [q.answer for q in answered] == ["b", "b"] and {q.answered_by for q in answered} == {"operator"}
    assert operations.waiting(run.id)["for"] == "agreement"


@pytest.mark.fr("FR-121")
def test_an_editor_left_with_an_answer_missing_keeps_the_draft_for_next_time(home, sprint, fake_notify, tmp_path,
                                                                             monkeypatch, capsys):
    run, _ = start(sprint, [speaks([WHO]), planner_says(questions=[HOW_LOUD]), speaks(points=()), speaks(points=()),
                            *aligned_round()])
    editor = tmp_path / "editor"
    editor.write_text("#!/bin/sh\nsed -i '0,/^answer:$/s//answer: a/' \"$1\"\n")         # answers the first only
    editor.chmod(editor.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("EDITOR", str(editor))
    assert cli.main(["answer"]) == 1
    assert "kept" in capsys.readouterr().err
    editor.write_text("#!/bin/sh\nsed -i 's/^answer:$/answer: b/' \"$1\"\n")           # the second, next time
    assert cli.main(["answer"]) == 0
    assert [q.answer for q in open_store(home).query("questions", {"run_id": run.id})] == ["a", "b"]


@pytest.mark.fr("FR-121")
@pytest.mark.parametrize("how", ["file", "stdin"])
def test_answers_can_be_given_from_a_file_or_stdin_for_an_orchestrator(home, sprint, fake_notify, tmp_path,
                                                                        monkeypatch, how):
    run, _ = start(sprint, [speaks([WHO]), planner_says(questions=[HOW_LOUD]), speaks(points=()),
                            speaks(points=()), *aligned_round()])
    text = filled(run.id, {WHO: "a", HOW_LOUD: "b"})
    if how == "file":
        (tmp_path / "answers.md").write_text(text)
        argv = ["answer", "--file", str(tmp_path / "answers.md")]
    else:
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO(text))
        argv = ["answer", "--file", "-"]
    assert cli.main(argv) == 0
    assert [q.answer for q in open_store(home).query("questions", {"run_id": run.id})] == ["a", "b"]


@pytest.mark.fr("FR-121")
def test_one_waiting_question_may_be_answered_in_words_and_several_may_not(home, sprint, fake_notify):
    run, _ = start(sprint, [speaks([WHO]), planner_says(questions=[HOW_LOUD]), speaks(points=()), speaks(points=())])
    with pytest.raises(Refused, match="2 questions are waiting"):
        operations.answer(run.id, "a")
    run, _ = start_again(home, sprint, [speaks([WHO]), planner_says(), speaks(points=()), speaks(points=()),
                                        *aligned_round()])
    operations.answer(run.id, "a")
    assert operations.waiting(run.id)["for"] == "agreement"


def start_again(home, target, entries):
    operations.abandon()
    return start(target, entries)


@pytest.mark.fr("FR-121")
def test_factory_questions_prints_the_batch_and_its_json(home, sprint, fake_notify, capsys):
    run, _ = start(sprint, [speaks([WHO]), planner_says(), speaks(points=()), speaks(points=())])
    capsys.readouterr()
    assert cli.main(["questions"]) == 0
    out = capsys.readouterr().out
    assert WHO in out and "answer:" in out
    assert cli.main(["questions", "--json"]) == 0
    assert WHO in capsys.readouterr().out


@pytest.mark.fr("FR-121")
def test_the_playbook_tells_an_orchestrator_to_walk_the_asker_through_a_batch_and_return_it_whole():
    playbook = (config.PACKAGE_DIR.parent / "orchestrator" / "playbook.md").read_text()
    for says in ("## In a dialogue", "one\n  at a time", "factory answer --file", "Agreement is not approval"):
        assert says in playbook, says


# ---- FR-122: only the agents propose aligned; the asker agrees; agreement is not approval ----

@pytest.mark.fr("FR-122")
@pytest.mark.parametrize("change, passed", [
    ({}, True),
    ({"plan": ""}, False),                                    # aligned, with no plan
    ({"estimate": " "}, False),                               # aligned, with no estimate
    ({"questions": ["one more?"]}, False),                    # aligned, and still asking
    ({"aligned": "no"}, False),                               # not aligned, and asking nothing
    ({"aligned": "no", "plan": "", "measure": ["what?"]}, True),
])
def test_the_planner_proposes_aligned_with_a_plan_and_an_estimate_or_asks_something(change, passed):
    from factory import checks
    envelope = dict(planner_says()["envelope"], **change)
    context = checks.CheckContext(run=None, step=workflow.get("dialogue_planner", tables.SPRINT_STEPS),
                                  checkout=None, target_config=config.TargetConfig(), changed=set(),
                                  envelope=envelope, before="")
    assert checks.get("dialogue_moves")(context).passed is passed


@pytest.mark.fr("FR-122")
def test_agreement_is_not_approval_and_approval_waits_for_it(home, sprint, fake_notify):
    run, _ = start(sprint, [*aligned_round(), *BUILD_TO_THE_END])
    assert operations.waiting(run.id)["for"] == "agreement"
    with pytest.raises(Refused, match="agree"):
        operations.approve(run.id)
    run = operations.agree(run.id)
    assert (run.state, operations.plan(run.id).decision) == ("awaiting_approval", "agreed")
    assert operations.waiting(run.id)["for"] == "approval"
    with pytest.raises(Refused, match="has no plan proposed"):
        operations.agree(run.id)
    assert operations.approve(run.id).outcome == "accepted"


@pytest.mark.fr("FR-122")
def test_an_aligned_planner_with_a_point_raised_beside_it_is_not_aligned(home, sprint, fake_notify):
    run, _ = start(sprint, [speaks(), planner_says(), speaks(points=()), speaks(points=["a refusal has no test"]),
                            *aligned_round()])
    assert names(home, run) == SPEAKERS * 2
    assert records.current_plan(open_store(home), run.id).version == 1       # one plan: the one aligned on


@pytest.mark.fr("FR-122")
def test_replying_to_a_proposed_plan_continues_the_dialogue(home, sprint, fake_notify):
    run, fake = start(sprint, [*aligned_round(), *aligned_round("Add hello.py and say hi."), *BUILD_TO_THE_END])
    run = operations.revise(run.id, "Say hi, not hello.")
    assert names(home, run) == SPEAKERS * 2
    assert "Say hi, not hello." in fake.calls[5]["prompt"]
    assert operations.plan(run.id).text.startswith("Add hello.py and say hi.")
    with pytest.raises(Refused, match="no questions"):
        operations.answer(run.id, "fine")


@pytest.mark.fr("FR-122")
@pytest.mark.fr("FR-104")
def test_a_point_the_planner_declines_is_shown_with_its_reason(home, sprint, fake_notify):
    reason = "NOT NULL is checked first: it is not; the column is optional (measured)"
    run, _ = start(sprint, [speaks(), planner_says(), speaks(points=()), speaks(points=["NOT NULL is checked first"]),
                            speaks(), planner_says(declined=[reason]), speaks(points=()), speaks(points=())])
    shown = operations.plan(run.id).text
    assert reason in shown and "Declined by the planner" in shown


@pytest.mark.fr("FR-122")
def test_a_home_made_before_the_dialogue_keeps_its_plans_and_gains_agreement_and_rounds(home):
    import sqlite3
    from factory import store as store_module
    db = sqlite3.connect(home / "factory.db")
    db.executescript(store_module.BASE)
    db.execute("INSERT INTO runs (request, target, base_commit, state, created_at) VALUES ('r', '/t', 'c', 'planning',"
               " 'now')")
    db.execute("INSERT INTO plans VALUES (1, 1, 'the plan', '[]', '[]', NULL, 'pending', 'now')")
    db.execute("PRAGMA user_version = 5")
    db.commit()
    db.close()
    gw = open_store(home)
    assert records.decide(gw, 1, "agreed").text == "the plan"
    asked = records.ask(gw, 1, "dialogue_analyst", "analyst", "Who? a) you", round=1, measure=True)
    assert (asked.round, asked.measure) == (1, True)
    with pytest.raises(sqlite3.IntegrityError):
        records.decide(gw, 1, "maybe")


# ---- FR-123: the estimate, beside similar past runs ----

@pytest.mark.fr("FR-123")
def test_the_estimate_is_shown_beside_the_last_accepted_runs_of_its_kind_on_its_codebase(home, sprint, fake_notify):
    first, _ = to_the_end(sprint, FakeAgent([*aligned_round(), *BUILD_TO_THE_END]))
    run, fake = start(sprint, [speaks(), planner_says(estimate="half an hour, about $6"), speaks(points=()),
                               speaks(points=())])
    shown = operations.plan(run.id).text
    assert "half an hour, about $6" in shown and f"Run {first.id} (accepted" in shown
    assert f"Run {first.id} (accepted" in fake.calls[1]["prompt"]            # the planner is shown them too


@pytest.mark.fr("FR-123")
def test_similar_runs_are_the_last_five_accepted_of_the_same_kind_on_the_same_codebase(home):
    store = open_store(home)

    def ended(target, kind="change", outcome="accepted", cost=1.0):
        run = records.new_run(store, "x", target, "abc", run_kind=kind)
        step = records.start_step(store, run.id, "build", "agent", "code_writer", "")
        records.finish_step(store, step.id, {}, [], True, cost_estimate=cost)
        return records.end(store, run.id, outcome, "r")

    same = [ended("/a", cost=n) for n in range(1, 8)]
    others = [ended("/b"), ended("/a", kind="tidy-code"), ended("/a", outcome="rejected")]
    mine = records.new_run(store, "y", "/a", "abc")
    found = dialogue.similar_runs(store, mine)
    assert [line.split(" ")[1] for line in found] == [str(r.id) for r in reversed(same[-5:])]
    assert "$7.00" in found[0] and not any(f"Run {r.id} " in " ".join(found) for r in others)


# ---- FR-124: a budget per dialogue; at it, the asker is asked whether to spend more ----

@pytest.mark.fr("FR-124")
def test_the_dialogue_budget_is_ten_dollars_unless_the_codebase_says_otherwise():
    assert config.TargetConfig().dialogue_budget_dollars == 10.0
    assert "dialogue_budget_dollars = 10.0" in config.DEFAULT_FACTORY_TOML
    assert workflow.dialogue_over_budget(10.0, 10.0) and not workflow.dialogue_over_budget(9.99, 10.0)
    assert not workflow.dialogue_over_budget(50.0, 0)
    assert [workflow.spend_more(said) for said in ("yes", "A", " no ", "b", "maybe")] == [True, True, False, False,
                                                                                          None]


def over_budget(target, planner=None, then=()):
    """A codebase with a $1.00 dialogue budget, and a first round that costs $1.20 and asks two questions."""
    toml = sprint_settings()[".factory.toml"].replace("dialogue_budget_dollars = 10.0", "dialogue_budget_dollars = 1.0")
    commit_files(target, {".factory.toml": toml})
    run, fake = start(target, [speaks([WHO], cost=0.6), planner or planner_says(questions=[HOW_LOUD], cost=0.6),
                               speaks(points=()), speaks(points=()), *then])
    budget = next(q for q in operations.questions(run.id).questions if q.asked_by == "factory")
    return run, fake, budget


@pytest.mark.fr("FR-124")
def test_at_its_budget_the_dialogue_asks_whether_to_spend_more_and_yes_goes_on(home, target, fake_notify):
    run, _, budget = over_budget(target, then=aligned_round())
    assert "$1.20" in budget.question and "$1.00" in budget.question
    with pytest.raises(Refused, match="yes or no"):
        operations.answer(run.id, filled(run.id, {WHO: "a", HOW_LOUD: "b", budget.question: "maybe"}))
    operations.answer(run.id, filled(run.id, {WHO: "a", HOW_LOUD: "b", budget.question: "yes"}))
    assert operations.waiting(run.id)["for"] == "agreement"


@pytest.mark.fr("FR-124")
def test_no_at_the_budget_pauses_the_dialogue_with_everything_kept_and_a_later_yes_goes_on(home, target, fake_notify,
                                                                                           capsys):
    run, fake, budget = over_budget(target, then=aligned_round())
    run = operations.answer(run.id, filled(run.id, {WHO: "a visitor", HOW_LOUD: "b", budget.question: "no"}))
    assert (run.state, run.outcome, operations.waiting(run.id)["for"]) == ("awaiting_approval", None, "paused")
    assert len(fake.calls) == 4                                                 # nothing more was spent
    kept = operations.questions(run.id)
    assert kept.questions == [] and WHO in kept.text and "a visitor" in kept.text and "paused" in kept.text
    record = git(target, "show", f"{run.branch}:{run_record.name(run)}")
    assert WHO in record and "a visitor" in record                             # the record keeps it too
    capsys.readouterr()
    assert cli.main(["status"]) == 0 and "paused at its budget" in capsys.readouterr().out
    with pytest.raises(Refused, match="paused at its budget"):
        operations.answer(run.id, "no")
    operations.answer(run.id, "yes")                                            # spend more after all
    assert WHO in fake.calls[4]["prompt"] and "a visitor" in fake.calls[4]["prompt"]
    assert "round 2" in fake.calls[4]["prompt"].lower()
    assert operations.waiting(run.id)["for"] == "agreement"                    # a fresh allowance: not asked again


@pytest.mark.fr("FR-124")
def test_a_dialogue_paused_at_its_budget_may_agree_to_the_planners_draft(home, target, fake_notify):
    drafting = planner_says(questions=[HOW_LOUD], cost=0.6)
    drafting["envelope"].update(plan="Add hello.py, quietly.", estimate="ten minutes, $3")
    run, _, budget = over_budget(target, planner=drafting, then=BUILD_TO_THE_END)
    operations.answer(run.id, filled(run.id, {WHO: "a", HOW_LOUD: "b", budget.question: "no"}))
    run = operations.agree(run.id)
    shown = operations.plan(run.id)
    assert shown.decision == "agreed" and shown.text.startswith("Add hello.py, quietly.") and "$3" in shown.text
    assert operations.approve(run.id).outcome == "accepted"


# ---- FR-125: an agreed plan approved after the codebase moved is re-checked first ----

@pytest.mark.fr("FR-125")
def test_an_agreed_plan_approved_after_the_codebase_moved_is_re_checked_against_it_first(home, sprint, fake_notify):
    still = {"envelope": {"verdict": "accept", "findings": []}}
    run, fake = start(sprint, [*aligned_round(), still, *BUILD_TO_THE_END])
    operations.agree(run.id)
    moved = git(commit_files(sprint, {"NOTES.md": "merged meanwhile\n"}), "rev-parse", "HEAD")
    run = operations.approve(run.id)
    assert run.outcome == "accepted", run.reason
    assert names(home, run)[4] == "recheck_plan" and run.base_commit == moved
    recheck = prompts_of(fake, "# Reviewer")[1]
    assert moved[:7] in recheck and "NOTES.md" in recheck
    assert "NOTES.md" in git(sprint, "ls-tree", "-r", "--name-only", run.branch).split()


@pytest.mark.fr("FR-125")
def test_a_plan_found_stale_goes_back_to_the_dialogue(home, sprint, fake_notify):
    stale = {"envelope": {"verdict": "stale", "findings": ["hello.py now exists; the plan creates it"]}}
    run, fake = start(sprint, [*aligned_round(), stale, *aligned_round("Change hello.py."), *BUILD_TO_THE_END])
    operations.agree(run.id)
    commit_files(sprint, {"hello.py": "print('hello')\n"})
    run = operations.approve(run.id)
    assert (run.state, operations.waiting(run.id)["for"]) == ("awaiting_approval", "agreement")
    store = open_store(home)
    assert [p.decision for p in store.query("plans", {"run_id": run.id})] == ["stale", "pending"]
    assert "hello.py now exists" in fake.calls[5]["prompt"]                 # the next round is told why
    run, _ = to_the_end_from(run)
    assert run.outcome == "accepted" and names(home, run).count("recheck_plan") == 1     # not moved again


def to_the_end_from(run):
    operations.agree(run.id)
    return operations.approve(run.id), None


@pytest.mark.fr("FR-125")
def test_a_plan_approved_on_the_codebase_it_was_agreed_on_is_not_re_checked(home, sprint, fake_notify):
    run, _ = to_the_end(sprint, FakeAgent([*aligned_round(), *BUILD_TO_THE_END]))
    assert "recheck_plan" not in names(home, run)


# ---- FR-126: the agents say how much dialogue a change needs; a tidy may align at once ----

@pytest.mark.fr("FR-126")
def test_a_tidy_may_reach_aligned_in_its_first_round_with_no_questions(home, sprint, fake_notify):
    commit_files(sprint, {"hello.py": CODE, "tests/test_hello.py": TEST})
    tidied = {"envelope": {"summary": "gave the greeting one home", "files_changed": ["hello.py"]},
              "files": {"hello.py": "GREETING = 'hello'\n\n\ndef greet(name=''):\n    return GREETING\n"}}
    run, waits = to_the_end(sprint, FakeAgent([speaks(), planner_says(how_much="none: a tidy with a plain aim"),
                                               speaks(points=()), speaks(points=()), tidied, REVIEW]),
                            run_kind="tidy-code")
    assert run.outcome == "accepted", run.reason
    assert names(home, run)[:4] == SPEAKERS and waits == 1
    record = git(sprint, "show", f"{run.branch}:{run_record.name(run)}")
    assert "none: a tidy with a plain aim" in record


@pytest.mark.fr("FR-126")
def test_every_speaker_is_told_to_decide_how_much_dialogue_the_change_needs():
    for name in SPEAKERS:
        assert "how much dialogue" in (config.PROMPTS_DIR / f"{name}.md").read_text().lower(), name
    assert "how_much" in workflow.get("dialogue_planner", tables.SPRINT_STEPS).envelope


# ---- FR-127: the whole dialogue is in the run's record ----

@pytest.mark.fr("FR-127")
def test_the_record_holds_every_round_question_answer_measurement_and_the_agreed_plan(home, sprint, fake_notify):
    run, _ = start(sprint, [speaks([WHO]), planner_says(measure=[MEASURE]), speaks(points=["name the file"]),
                            speaks(points=()), speaks(), planner_says(estimate="a quarter hour, $4"),
                            speaks(points=()), speaks(points=()), *BUILD_TO_THE_END])
    operations.answer(run.id, filled(run.id, {WHO: "a visitor", MEASURE: "Python 3.13.1"}))
    run = operations.approve(operations.agree(run.id).id)
    assert run.outcome == "accepted", run.reason
    record = git(sprint, "show", f"{run.branch}:{run_record.name(run)}")
    dialogue_part = record[record.index("## The dialogue"):record.index("## The approved plan")]
    for said in ("### Round 1", "### Round 2", WHO, "a visitor", MEASURE, "Python 3.13.1", "name the file",
                 "agreed"):
        assert said in dialogue_part, said
    assert "a quarter hour, $4" in record[record.index("## The approved plan"):]


# ---- FR-128: status, watch and plan say what a dialogue run waits for ----

@pytest.mark.fr("FR-128")
def test_status_watch_and_plan_say_what_the_dialogue_waits_for(home, sprint, fake_notify, monkeypatch, capsys):
    run, _ = start(sprint, [speaks([WHO]), planner_says(), speaks(points=()), speaks(points=()),
                            *aligned_round()])
    capsys.readouterr()
    assert cli.main(["status"]) == 0
    assert "answers: the analyst" in capsys.readouterr().out
    with pytest.raises(Refused, match="no plan to read"):
        operations.plan(run.id)
    assert cli.main(["watch"]) == 0
    assert "factory questions" in capsys.readouterr().out
    operations.answer(run.id, "a")
    assert cli.main(["status"]) == 0
    assert "agreement" in capsys.readouterr().out
    assert cli.main(["plan"]) == 0
    out = capsys.readouterr().out
    assert "proposed" in out and "factory agree" in out


@pytest.mark.fr("FR-128")
def test_a_plan_replied_to_is_never_shown_as_the_current_one(home, sprint, fake_notify):
    run, _ = start(sprint, [*aligned_round(), speaks([WHO]), planner_says(), speaks(points=()), speaks(points=())])
    operations.revise(run.id, "Say hi.")
    with pytest.raises(Refused, match="version 1 was replied to"):
        operations.plan(run.id)


# ---- FR-129: what every speaker is told ----

@pytest.mark.fr("FR-129")
@pytest.mark.parametrize("says", ["an ask, not a directive", "one candidate way", "only what the asker can answer",
                                  "settle by reading", "short", "lettered choices"])
def test_every_speaker_is_told_the_ask_is_an_ask_and_how_to_ask(home, sprint, fake_notify, says):
    run, fake = start(sprint, aligned_round())
    for call in fake.calls:
        assert says in call["prompt"], says
