"""Questions that ask for the same decision are merged, however their options are worded (FR-151).

The cases are bttr_erp's own: run 99 asked one reason-for-a-change choice three times (Q89, Q92, Q94) and run 100 one
end-date choice twice (Q98, Q101), and neither was merged. Run 100's merge was proposed, as one flat list, and thrown
away; run 99's was not proposed. The shape is tested here against the factory's own reading of a reply; the judgment,
which only a model makes, against the real light model in the live test at the end (`uv run pytest -m live`).
"""
import pytest

from factory import agent, config, dialogue, driver, records, tables
from factory.store import open_store

PROMPT = (config.PROMPTS_DIR / "merge_questions.md").read_text()

RUN_99 = [   # who asked, and what; the three that ask whether a reason is required are one decision
    ("dialogue_analyst", "analyst", "Record history (old values, who, when, why) is ruled for period facts. Which"
     " tables can have it in this run? a) period facts only  b) any table that declares it, with every period fact"
     " having it"),
    ("dialogue_analyst", "analyst", "A change to a period-fact row: must the writer give a reason ('why')? a)"
     " required on every edit and every recorded-in-error removal, refused without one  b) required only when the"
     " change rewrites the past (a start moved earlier, recorded in error)  c) optional"),
    ("dialogue_analyst", "analyst", "A period-fact row changed outside bttr (raw SQL through psql): must its old"
     " values still be kept in the record history? a) yes, every change is kept, with who unknown  b) no, only"
     " changes made through bttr"),
    ("dialogue_planner", "planner", "When a row of a table that keeps history is created, edited or removed, must the"
     " person give a reason (the 'why')? a) optional everywhere, recorded when given, as django-simple-history (Odoo,"
     " ERPNext and Tryton record no reason at all); b) required only when a row is removed as recorded in error; c)"
     " required on every create, edit and removal of such a row."),
    ("dialogue_planner", "planner", "Does every declared period fact keep its history without its declaration asking"
     " for it? a) yes, always, with no way to turn it off, per your 2026-11-25 ruling that every change to a period"
     " is kept; b) only when its declaration says `history: true`, as for any other table (Tryton and"
     " django-simple-history are opt-in)."),
    ("dialogue_architect", "architect", "Must every edit or removal of a period-fact row carry a reason ('why'), or is"
     " the reason optional? a) required, refused without one  b) optional, recorded when given (as Odoo, ERPNext,"
     " Tryton)  c) required only on a removal (recorded in error)"),
]
REASON = (1, 3, 5)      # the reason-for-a-change choice, by place in RUN_99

RUN_100 = [  # the end date asked twice; whether a correction must be marked looks alike and is another decision
    ("dialogue_analyst", "analyst", "A period-fact row's END moved later into time the entity's periods did not cover"
     " (a mistyped end date, or an ended period reopened). The ruling names only a start moved earlier. a) still"
     " refused, as run 97's Q52 answer; only a start may move (recommended, the ruling's words) b) allowed too, as a"
     " correction"),
    ("dialogue_analyst", "analyst", "A save that moves an existing period's start earlier into uncovered time: must"
     " the writer mark it as a correction? a) no: any such edit is allowed, the record history keeps the old value"
     " and the why stays optional (recommended, Q89) b) yes: allowed only when the write says it is a correction,"
     " otherwise refused as today"),
    ("dialogue_planner", "planner", "A period-fact row's start may now be edited earlier into time no other period of"
     " its entity covers (a caseworker's intake date typed 03-15 for 03-05), with the old value kept in the record"
     " history. May an existing row's END also be edited later into such time (an exit date typed too early, or an"
     " ended period reopened)? a) no: only a start moves earlier, as the ruling words it, and an end moved later into"
     " uncovered time stays refused  b) yes, both bounds: the 'reaches time the entity did not cover' refusal goes"
     " for every edit of an existing row (recommended: Odoo, ERPNext and HUD HMIS let either date be edited,"
     " Fowler's valid time is corrected either way, and one refusal is deleted rather than split in two)"),
]
END, MARKED = (0, 2), 1


def asked(home, batch):
    """A run whose round 1 holds these questions, waiting; returns the store and the questions."""
    store = open_store(home)
    run = store.insert("runs", {"request": "r", "target": "/t", "base_commit": "c", "state": "working",
                                "created_at": "2026-11-25T10:00:00.000Z"})
    return store, run, [records.ask(store, run.id, step, who, text, round=1) for step, who, text in batch]


def ids(questions, places):
    return [f"Q{questions[i].id}" for i in places]


# ---- the reply's shape ----

@pytest.mark.fr("FR-151")
def test_one_group_given_as_a_flat_list_is_merged_as_run_100s_was_not(home):
    store, run, questions = asked(home, RUN_100)
    flat = ids(questions, (2, 0))                               # what run 100's merge replied: ["Q101", "Q98"]
    into = dialogue.merge(store, run.id, {"merged": flat}, dialogue.to_merge(store, run.id))
    assert into == {questions[0].id: questions[2].id}
    assert [q.id for q in dialogue.batch(store, run.id)] == [questions[1].id, questions[2].id]


@pytest.mark.fr("FR-151")
@pytest.mark.parametrize("merged, holds", [
    ("groups", True),                       # each group its own list, as the prompt shows
    ("mixed", False),                       # a group and a loose number: not a merge the factory can read
])
def test_a_list_of_groups_still_merges_and_a_mixed_reply_merges_nothing(home, merged, holds):
    store, run, questions = asked(home, RUN_99)
    reason = ids(questions, REASON)
    said = [reason] if merged == "groups" else [reason, f"Q{questions[0].id}"]
    into = dialogue.merge(store, run.id, {"merged": said}, dialogue.to_merge(store, run.id))
    assert bool(into) is holds
    if holds:
        assert into == {questions[3].id: questions[1].id, questions[5].id: questions[1].id}


@pytest.mark.fr("FR-151")
def test_the_prompt_shows_a_list_of_groups_and_judges_the_decision_not_the_options():
    assert '[["Q3", "Q5"]]' in PROMPT                          # run 100 copied the flat example it was shown
    for says in ("the same decision", "letters", "order", "nothing left to decide"):
        assert says in PROMPT, says
    assert "When in doubt, do not merge" not in PROMPT         # run 99: three askings of one choice, none merged


@pytest.mark.fr("FR-151")
def test_the_merge_runs_on_the_middle_grade():
    assert tables.MERGE.model == "middle"       # the light model kept two of run 99's three askings apart, 1 time in 3


# ---- the judgment, by the real model the merge runs on ----

def judged(tmp_path, batch):
    """The merge step's own prompt and persona, given these questions, run once on its own grade's model."""
    store, run, questions = asked(tmp_path / "home", batch)
    waiting = dialogue.merge_input(store, run.id)
    reply = driver.fill(PROMPT, {"to_merge": waiting}) + "\n" + driver.fill(
        (config.PROMPTS_DIR / "fragments" / "reply.md").read_text(), {"shape": driver.reply_shape(tables.MERGE)})
    persona = (config.PERSONAS_DIR / f"{tables.MERGE.persona}.md").read_text()
    with open(tmp_path / "stderr.txt", "w") as err:
        result = agent.run_agent(persona=persona, prompt=reply, cwd=tmp_path, capabilities="read", timeout=300,
                                 on_event=lambda *event: None, raw_sink=lambda line: None, stderr_file=err,
                                 model=tables.MERGE.model)
    assert result.ok, result.error
    into = dialogue.merge(store, run.id, result.envelope, dialogue.to_merge(store, run.id))
    groups = {}
    for duplicate, kept in into.items():
        groups.setdefault(kept, {kept}).add(duplicate)
    return questions, [frozenset(group) for group in groups.values()]


@pytest.mark.live
@pytest.mark.fr("FR-151")
def test_the_three_askings_of_one_reason_choice_are_merged(tmp_path):
    questions, groups = judged(tmp_path, RUN_99)
    assert frozenset(questions[i].id for i in REASON) in groups, groups


@pytest.mark.live
@pytest.mark.fr("FR-151")
def test_the_end_date_asked_twice_is_merged_and_the_look_alike_stays_apart(tmp_path):
    questions, groups = judged(tmp_path, RUN_100)
    assert frozenset(questions[i].id for i in END) in groups, groups
    assert not any(questions[MARKED].id in group for group in groups), groups
