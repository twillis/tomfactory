"""The engine's general abilities, shown on small made-up step tables:

a step that can branch on its verdict, a run that waits more than once, sending work
back to the start of a stage, and setting a build aside to start again from the plan.
"""
import pytest

from factory import operations, workflow
from factory.store import open_store
from factory.workflow import END_ACCEPTED, WAIT, End, Replan, Rework, Step
from tests.conftest import drive_with, git
from tests.fake_agent import FakeAgent

# ---- a whole run on a made-up table: two waits, a rework, and a replan ----

TABLE = [
    Step("draft", "agent", persona="planner", on_pass=WAIT, on_approve="design", capabilities="read+edit", may_change="docs",
         commit_after=True, inputs=("request", "failure"), envelope={"plan": "text"}),
    Step("design", "agent", persona="planner", on_pass=WAIT, on_approve="make", capabilities="read+edit", may_change="docs",
         commit_after=True, inputs=("request", "failure"), envelope={"plan": "text"}),
    Step("make", "agent", persona="code_writer", on_pass="judge", capabilities="read+edit", may_change="not_tests",
         commit_after=True, inputs=("request", "failure"), envelope={"summary": "text"}),
    Step("judge", "agent", persona="reviewer", on_pass="finish", inputs=("request", "diff"),
         envelope={"verdict": "verdict", "reasons": "list"},
         routes={"rework": Rework("make"), "replan": Replan("draft"), "reject": End("rejected")}),
    Step("finish", "code", on_pass=END_ACCEPTED),
]


@pytest.fixture
def made_up(monkeypatch, tmp_path, home, target, fake_notify):
    from factory import config
    monkeypatch.setattr(workflow, "table_for", lambda spec_kit, run_kind: TABLE)
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for name in ("draft", "design", "make", "judge"):
        (prompts / f"{name}.md").write_text(f"# {name}\n\n{{{{request}}}}\n\nEarlier problem: "
                                            + ("{{diff}}" if name == "judge" else "{{failure}}") + "\n")
    for shared in ("asking.md", "answer_question.md"):      # every agent is told how to ask; the lead answers
        (prompts / shared).write_text((config.PROMPTS_DIR / shared).read_text())
    monkeypatch.setattr(config, "PROMPTS_DIR", prompts)
    return target


def doc(name, text):
    return {"envelope": {"plan": text}, "files": {f"docs/{name}.md": text + "\n"}}


def code(text):
    return {"envelope": {"summary": text}, "files": {"app.py": f"print({text!r})\n"}}


def verdict(value, *reasons):
    return {"envelope": {"verdict": value, "reasons": list(reasons)}}


@pytest.mark.fr("FR-057")
def test_a_run_waits_twice_and_each_approval_moves_it_on(made_up, home):
    fake = FakeAgent([doc("draft", "the spec"), doc("design", "the design"), code("v1"), verdict("accept", "fine")])
    drive_with(fake)
    run = operations.request("Build it", made_up)
    assert (run.state, run.current_step) == ("awaiting_approval", "draft")
    assert operations.plan(run.id).text == "the spec"
    run = operations.approve(run.id)
    assert (run.state, run.current_step) == ("awaiting_approval", "design")      # the second wait
    assert operations.plan(run.id).text == "the design"
    run = operations.approve(run.id)
    assert run.outcome == "accepted"
    store = open_store(home)
    assert [s.name for s in store.query("steps", {"run_id": run.id})] == ["draft", "design", "make", "judge", "finish"]
    assert [p.decision for p in store.query("plans", {"run_id": run.id})] == ["approved", "approved"]


@pytest.mark.fr("FR-059")
def test_unbuilt_work_returns_to_the_build_and_a_detail_does_not(made_up, home):
    fake = FakeAgent([doc("draft", "the spec"), doc("design", "the design"), code("v1"),
                      verdict("rework", "the help text is missing"), code("v2"), verdict("accept", "now complete")])
    drive_with(fake)
    run = operations.request("Build it", made_up)
    run = operations.approve(run.id)
    run = operations.approve(run.id)
    assert run.outcome == "accepted"
    assert "the help text is missing" in fake.calls[4]["prompt"]                 # told what was unbuilt
    names = [s.name for s in open_store(home).query("steps", {"run_id": run.id})]
    assert names == ["draft", "design", "make", "judge", "make", "judge", "finish"]


@pytest.mark.fr("FR-059")
@pytest.mark.fr("FR-060")
def test_a_requirement_change_goes_back_to_planning_and_the_build_is_set_aside(made_up, home):
    fake = FakeAgent([doc("draft", "the spec"), doc("design", "the design"), code("v1 with a login page"),
                      verdict("replan", "it adds a login page nobody asked for"),
                      doc("draft", "the spec, now with login"), doc("design", "the design, with login"),
                      code("v2"), verdict("accept", "matches the amended plan")])
    drive_with(fake)
    run = operations.request("Build it", made_up)
    run = operations.approve(run.id)
    run = operations.approve(run.id)

    assert (run.state, run.current_step) == ("awaiting_approval", "draft")       # back with the operator
    assert "login page nobody asked for" in fake.calls[4]["prompt"]              # the planner was told why
    assert operations.plan(run.id).text == "the spec, now with login"
    aside = [b.strip(" +*") for b in git(made_up, "branch", "--list", f"{run.branch}-aside-*").splitlines()]
    assert len(aside) == 1, "the earlier build must be kept where the operator can find it"
    assert "login page" in git(made_up, "show", f"{aside[0]}:app.py")
    assert "app.py" not in git(made_up, "ls-tree", "-r", "--name-only", run.branch).split()   # and is gone from the run
    store = open_store(home)
    assert "set_aside" in [e.kind for e in store.query("events", {"run_id": run.id})]

    run = operations.approve(run.id)                  # the amended spec
    run = operations.approve(run.id)                  # the amended design
    assert run.outcome == "accepted"
    assert git(made_up, "show", f"{run.branch}:app.py") == "print('v2')"         # built again from the plan
    names = [s.name for s in store.query("steps", {"run_id": run.id})]
    assert names == ["draft", "design", "make", "judge", "draft", "design", "make", "judge", "finish"]


@pytest.mark.fr("FR-057")
def test_sending_a_later_stage_back_does_not_disturb_an_approved_earlier_one(made_up, home):
    fake = FakeAgent([doc("draft", "the spec"), doc("design", "first design"), doc("design", "second design"),
                      code("v1"), verdict("accept")])
    drive_with(fake)
    run = operations.request("Build it", made_up)
    operations.approve(run.id)
    run = operations.revise(run.id, "simpler please")
    assert (run.state, run.current_step) == ("awaiting_approval", "design")
    assert "simpler please" in fake.calls[2]["prompt"]
    assert operations.approve(run.id).outcome == "accepted"
    assert [p.decision for p in open_store(home).query("plans", {"run_id": run.id})] == ["approved", "revised", "approved"]
