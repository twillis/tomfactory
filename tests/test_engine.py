"""The engine's general abilities, shown on small made-up step tables:

a step that can branch on its verdict, a run that waits more than once, sending work
back to the start of a stage, and setting a build aside to start again from the plan.
"""
import pytest

from factory import operations, workflow
from factory.checks import CheckResult
from factory.store import open_store
from factory.workflow import END_ACCEPTED, WAIT, End, Replan, Rework, Run, Step, StepResult, Wait, after_wait, next_step
from tests.conftest import git, in_process
from tests.fake_agent import FakeAgent

VERDICTS = ("accept", "rework", "replan", "reject")
JUDGE = Step("judge", "agent", persona="reviewer", on_pass="finish",
             envelope={"verdict": VERDICTS, "reasons": "list"},
             routes={"rework": Rework("make"), "replan": Replan("draft"), "reject": End("rejected")})


def judged(verdict, note="because"):
    return StepResult(False, "check", CheckResult("verdict", False, note), verdict=verdict)


@pytest.mark.fr("FR-059")
def test_a_step_can_send_the_run_three_ways_by_its_verdict():
    assert next_step(JUDGE, StepResult(True, verdict="accept"), {}, 3) == Run("finish")
    assert next_step(JUDGE, judged("rework"), {"make": 1}, 3) == Run("make")
    assert next_step(JUDGE, judged("replan", "it adds a login page"), {"draft": 1}, 3) == Replan("draft")
    assert next_step(JUDGE, judged("reject", "breaks an ideal"), {}, 3) == End("rejected", "breaks an ideal")


@pytest.mark.fr("FR-059")
def test_branches_are_bounded_by_the_attempt_limit():
    assert next_step(JUDGE, judged("rework", "tests missing"), {"make": 3}, 3).outcome == "needs-me"
    ended = next_step(JUDGE, judged("replan", "it adds a login page"), {"draft": 3}, 3)
    assert ended.outcome == "needs-me" and "draft" in ended.reason and "login page" in ended.reason


@pytest.mark.fr("FR-058")
def test_a_verdict_must_be_one_the_step_allows():
    from factory import checks
    from factory.checks import CheckContext
    from factory.config import TargetConfig

    def valid(envelope):
        return checks.get("envelope_valid")(CheckContext(None, JUDGE, None, TargetConfig(), set(), envelope, "")).passed

    assert valid({"verdict": "replan", "reasons": []}) and valid({"verdict": "accept", "reasons": ["ok"]})
    assert not valid({"verdict": "maybe", "reasons": []}) and not valid({"reasons": []})


@pytest.mark.fr("FR-057")
def test_sending_work_back_returns_to_the_start_of_its_stage():
    table = [Step("draft", "agent", persona="planner", on_pass="refine"),
             Step("refine", "agent", persona="planner", on_pass=WAIT, revise_from="draft"),
             Step("design", "agent", persona="planner", on_pass=WAIT),
             Step("finish", "code", on_pass=END_ACCEPTED)]
    assert after_wait("revise", table[1], table) == Run("draft")       # back to the start of the stage
    assert after_wait("approve", table[1], table) == Run("design")
    assert after_wait("revise", table[2], table) == Run("design")      # no revise_from: the step itself
    assert after_wait("approve", table[2], table) == Run("finish")
    assert next_step(table[1], StepResult(True), {}, 3) == Wait()


@pytest.mark.fr("FR-055")
def test_the_table_is_chosen_by_whether_the_target_uses_spec_kit():
    plain, kit = workflow.table_for(False), workflow.table_for(True)
    assert plain is workflow.STEPS and [s.name for s in plain][0] == "plan"
    assert kit is not plain and [s.name for s in kit][0] == "specify"
    assert workflow.get("converge", kit).routes and not any(s.routes for s in plain)


# ---- a whole run on a made-up table: two waits, a rework, and a replan ----

TABLE = [
    Step("draft", "agent", persona="planner", on_pass=WAIT, capabilities="read+edit", may_change="docs",
         commit_after=True, inputs=("request", "failure"), envelope={"plan": "text"}),
    Step("design", "agent", persona="planner", on_pass=WAIT, capabilities="read+edit", may_change="docs",
         commit_after=True, inputs=("request", "failure"), envelope={"plan": "text"}),
    Step("make", "agent", persona="code_writer", on_pass="judge", capabilities="read+edit", may_change="not_tests",
         commit_after=True, inputs=("request", "failure"), envelope={"summary": "text"}),
    Step("judge", "agent", persona="reviewer", on_pass="finish", inputs=("request", "diff"),
         envelope={"verdict": VERDICTS, "reasons": "list"},
         routes={"rework": Rework("make"), "replan": Replan("draft"), "reject": End("rejected")}),
    Step("finish", "code", on_pass=END_ACCEPTED),
]


@pytest.fixture
def made_up(monkeypatch, tmp_path, home, target, fake_notify):
    from factory import config
    monkeypatch.setattr(workflow, "table_for", lambda spec_kit: TABLE)
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for name in ("draft", "design", "make", "judge"):
        (prompts / f"{name}.md").write_text(f"# {name}\n\n{{{{request}}}}\n\nEarlier problem: "
                                            + ("{{diff}}" if name == "judge" else "{{failure}}") + "\n")
    (prompts / "asking.md").write_text((config.PROMPTS_DIR / "asking.md").read_text())   # every agent gets this
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
    run = operations.request("Build it", made_up, launcher=in_process(fake))
    assert (run.state, run.current_step) == ("awaiting_approval", "draft")
    assert operations.plan(run.id).text == "the spec"
    run = operations.approve(run.id, launcher=in_process(fake))
    assert (run.state, run.current_step) == ("awaiting_approval", "design")      # the second wait
    assert operations.plan(run.id).text == "the design"
    run = operations.approve(run.id, launcher=in_process(fake))
    assert run.outcome == "accepted"
    store = open_store(home)
    assert [s.name for s in store.query("steps", {"run_id": run.id})] == ["draft", "design", "make", "judge", "finish"]
    assert [p.decision for p in store.query("plans", {"run_id": run.id})] == ["approved", "approved"]


@pytest.mark.fr("FR-059")
def test_unbuilt_work_returns_to_the_build_and_a_detail_does_not(made_up, home):
    fake = FakeAgent([doc("draft", "the spec"), doc("design", "the design"), code("v1"),
                      verdict("rework", "the help text is missing"), code("v2"), verdict("accept", "now complete")])
    run = operations.request("Build it", made_up, launcher=in_process(fake))
    run = operations.approve(run.id, launcher=in_process(fake))
    run = operations.approve(run.id, launcher=in_process(fake))
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
    run = operations.request("Build it", made_up, launcher=in_process(fake))
    run = operations.approve(run.id, launcher=in_process(fake))
    run = operations.approve(run.id, launcher=in_process(fake))

    assert (run.state, run.current_step) == ("awaiting_approval", "draft")       # back with the operator
    assert "login page nobody asked for" in fake.calls[4]["prompt"]              # the planner was told why
    assert operations.plan(run.id).text == "the spec, now with login"
    aside = [b.strip(" +*") for b in git(made_up, "branch", "--list", f"{run.branch}-aside-*").splitlines()]
    assert len(aside) == 1, "the earlier build must be kept where the operator can find it"
    assert "login page" in git(made_up, "show", f"{aside[0]}:app.py")
    assert "app.py" not in git(made_up, "ls-tree", "-r", "--name-only", run.branch).split()   # and is gone from the run
    store = open_store(home)
    assert "set_aside" in [e.kind for e in store.query("events", {"run_id": run.id})]

    run = operations.approve(run.id, launcher=in_process(fake))                  # the amended spec
    run = operations.approve(run.id, launcher=in_process(fake))                  # the amended design
    assert run.outcome == "accepted"
    assert git(made_up, "show", f"{run.branch}:app.py") == "print('v2')"         # built again from the plan
    names = [s.name for s in store.query("steps", {"run_id": run.id})]
    assert names == ["draft", "design", "make", "judge", "draft", "design", "make", "judge", "finish"]


@pytest.mark.fr("FR-057")
def test_sending_a_later_stage_back_does_not_disturb_an_approved_earlier_one(made_up, home):
    fake = FakeAgent([doc("draft", "the spec"), doc("design", "first design"), doc("design", "second design"),
                      code("v1"), verdict("accept")])
    run = operations.request("Build it", made_up, launcher=in_process(fake))
    operations.approve(run.id, launcher=in_process(fake))
    run = operations.revise(run.id, "simpler please", launcher=in_process(fake))
    assert (run.state, run.current_step) == ("awaiting_approval", "design")
    assert "simpler please" in fake.calls[2]["prompt"]
    assert operations.approve(run.id, launcher=in_process(fake)).outcome == "accepted"
    assert [p.decision for p in open_store(home).query("plans", {"run_id": run.id})] == ["approved", "revised", "approved"]
