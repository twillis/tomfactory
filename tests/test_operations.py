"""What the operator can do to a run (Story 1: request, plan, approve, revise, abandon)."""
import dataclasses

import re

import pytest

from factory import operations, records
from factory.operations import Refused
from factory.store import open_store
from tests.conftest import drive_with, git, PLAN, script, tree
from tests.fake_agent import FakeAgent


def planned(target, fake_notify, script=None, **kw):
    """Make a request and carry it to the point where its plan is waiting."""
    fake = drive_with(FakeAgent(script or [{"envelope": PLAN}]))
    run = operations.request("Create a hello page", target, **kw)
    return run, fake


@pytest.mark.fr("FR-034")
def test_init_target_makes_a_committed_repository_with_the_defaults(tmp_path):
    made = operations.init_target(tmp_path / "viewer")
    assert made == tmp_path / "viewer"
    assert git(made, "status", "--porcelain") == ""
    assert set(git(made, "ls-files").split()) == {".factory.toml", ".gitignore", "README.md"}
    assert "test_command" in (made / ".factory.toml").read_text()
    assert "__pycache__/" in (made / ".gitignore").read_text()
    with pytest.raises(Refused, match="already has"):
        operations.init_target(made)


def _no_commit(target, tmp_path):
    (tmp_path / "plain").mkdir()
    git(tmp_path / "plain", "init", "-q")
    return tmp_path / "plain"


def _no_settings(target, tmp_path):
    git(target, "rm", "-q", ".factory.toml")
    git(target, "commit", "-q", "-m", "remove settings")
    return target


@pytest.mark.fr("FR-001")
@pytest.mark.fr("FR-010")
@pytest.mark.fr("FR-066")
@pytest.mark.parametrize("where, text, kw, refused", [
    (lambda target, tmp_path: target, "   ", {}, "empty"),
    (lambda target, tmp_path: tmp_path / "nowhere", "Do something", {}, "not a git repository"),
    (_no_commit, "Do something", {}, "not a git repository with at least one commit"),
    (_no_settings, "Do something", {}, ".factory.toml"),
    (lambda target, tmp_path: target, "Do something", {"attempts": 0}, "at least 1"),
    (lambda target, tmp_path: target, "Do something", {"run_kind": "rewrite"}, "tidy-tests"),
])
def test_a_request_is_refused_with_a_reason_when_it_cannot_start(home, target, tmp_path, fake_notify,
                                                               where, text, kw, refused):
    drive_with(FakeAgent([]))
    with pytest.raises(Refused, match=refused):
        operations.request(text, where(target, tmp_path), **kw)
    assert open_store(home).query("runs") == []          # nothing was recorded


@pytest.mark.fr("FR-033")
def test_a_second_request_is_declined_while_a_run_is_open(home, target, fake_notify):
    first, _ = planned(target, fake_notify)
    with pytest.raises(Refused, match=f"run {first.id}"):
        drive_with(FakeAgent([]))
        operations.request("Another thing", target)
    store = open_store(home)
    assert [r.id for r in store.query("runs", order="-id", limit=20)] == [first.id]
    assert store.get("runs", first.id) == first  # untouched


@pytest.mark.fr("FR-010")
def test_the_attempt_limit_can_be_set_when_making_the_request(home, target, fake_notify):
    run, _ = planned(target, fake_notify, attempts=2)
    assert run.attempt_limit == 2


@pytest.mark.fr("FR-002")
def test_after_the_plan_step_the_run_waits_and_nothing_has_changed(home, target, fake_notify):
    before = tree(target)
    run, fake = planned(target, fake_notify)
    assert isinstance(run, dict) and run["request"] == "Create a hello page"      # a plain row
    assert run.state == "awaiting_approval" and run.current_step == "plan"
    assert (run.driver_pid, run.driver_started, run.child_pgid) == (None, None, None)
    assert run.base_commit == git(target, "rev-parse", "HEAD")
    assert re.fullmatch(r"factory/\d{8}-\d{6}-create-a-hello-page", run.branch)

    store = open_store(home)
    plan = operations.plan(run.id)
    assert isinstance(plan, dict) and (plan.version, plan.decision) == (1, "pending")
    assert plan.text == PLAN["plan"] and plan.ideals_addressed == PLAN["ideals_addressed"]
    assert operations.plan().version == 1  # without a run id: the most recent run

    assert fake_notify == [(f"Run {run.id}: plan ready — waiting for you", "Create a hello page")]
    kinds = [e.kind for e in records.events_after(store, run.id)]
    assert "notify" in kinds and kinds.count("step_start") == 1 and kinds.count("step_end") == 1

    assert tree(target) == before                                    # the operator's working copy
    assert git(run.workspace, "status", "--porcelain") == ""         # the run's checkout
    assert git(run.workspace, "rev-parse", "HEAD") == run.base_commit
    assert fake.calls[0]["capabilities"] == "read+edit" and fake.calls[0]["cwd"] == run.workspace
    assert "(none)" in fake.calls[0]["prompt"]          # no spec kit in this target: nothing extra is asked


@pytest.mark.fr("FR-047")
def test_the_plan_step_is_recorded_with_its_persona_and_checks(home, target, fake_notify):
    run, fake = planned(target, fake_notify)
    step = open_store(home).query("steps", {"run_id": run.id})[0]
    assert (step.name, step.kind, step.persona, step.attempt, step.passed) == ("plan", "agent", "planner", 1, True)
    assert step.produced == PLAN and step.failure is None
    assert [c["name"] for c in step.checks] == ["factory_untouched", "changes_allowed", "deletions_inside",
                                                "envelope_valid", "plan_lines_within_length"]
    assert all(c["passed"] for c in step.checks)
    assert "## Expertise" in fake.calls[0]["persona"]                # the persona file's text
    assert "Create a hello page" in fake.calls[0]["prompt"] and step.asked == fake.calls[0]["prompt"]
    assert "{{" not in step.asked
    assert "No ideals have been stated." in step.asked
    assert step.tokens == {"input": 10, "output": 5}


@pytest.mark.fr("FR-004")
@pytest.mark.fr("FR-003")
def test_a_plan_sent_back_is_revised_with_the_comment_and_both_are_kept(home, target, fake_notify):
    second = dict(PLAN, plan="Add hello.py; also show the end time.")
    third = dict(PLAN, plan="Third version.")
    run, fake = planned(target, fake_notify, script=[{"envelope": PLAN}, {"envelope": second}, {"envelope": third}])

    revised = operations.revise(run.id, "Also show when the run ended.")
    assert revised.state == "awaiting_approval"
    prompt = fake.calls[1]["prompt"]
    assert PLAN["plan"] in prompt and "Also show when the run ended." in prompt
    operations.revise(run.id, "Shorter.")

    store = open_store(home)
    assert [(p.version, p.decision, p.comment) for p in store.query("plans", {"run_id": run.id})] == [
        (1, "revised", "Also show when the run ended."), (2, "revised", "Shorter."), (3, "pending", None)]
    assert operations.plan(run.id).text == "Third version."
    assert [s.attempt for s in store.query("steps", {"run_id": run.id})] == [1, 2, 3]
    assert store.get("runs", run.id).state == "awaiting_approval"      # revisions are not limited
    assert len(fake_notify) == 3
    with pytest.raises(Refused, match="comment"):
        operations.revise(run.id, "  ")


@pytest.mark.fr("FR-003")
def test_approve_moves_the_run_on_and_is_refused_unless_a_plan_is_waiting(home, target, fake_notify, monkeypatch):
    run, _ = planned(target, fake_notify)
    launched = []
    monkeypatch.setattr(operations, "launch", lambda store, r, state, step: launched.append((state, step)))
    approved = operations.approve(run.id)
    assert launched == [("working", "baseline")]
    assert records.current_plan(open_store(home), run.id).decision == "approved"
    assert approved.id == run.id
    records.set_state(open_store(home), run.id, "working", current_step="baseline")
    for operation in (operations.approve, operations.abandon):
        with pytest.raises(Refused, match="not waiting"):
            operation(run.id)
    with pytest.raises(Refused, match="not waiting"):
        operations.revise(run.id, "a comment")
    with pytest.raises(Refused, match="no run 99"):
        operations.approve(99)


@pytest.mark.fr("FR-003")
@pytest.mark.fr("FR-017")
def test_abandon_ends_the_run_rejected_and_removes_its_checkout(home, target, fake_notify):
    import pathlib
    run, _ = planned(target, fake_notify)
    ended = operations.abandon(run.id)
    assert (ended.state, ended.outcome, ended.reason) == ("ended", "rejected", "abandoned by operator")
    assert not pathlib.Path(run.workspace).exists()
    assert run.branch not in git(target, "branch", "--list", "factory/*")
    assert records.current_plan(open_store(home), run.id).decision == "abandoned"
    assert fake_notify[-1] == (f"Run {run.id}: rejected", "abandoned by operator")
    drive_with(FakeAgent([{"envelope": PLAN}]))
    assert operations.request("Next thing", target).id == run.id + 1


@pytest.mark.fr("FR-011")
@pytest.mark.fr("FR-028")
def test_a_plan_that_is_malformed_every_time_ends_needs_me_at_the_limit(home, target, fake_notify):
    run, fake = planned(target, fake_notify, script=[{"text": "no json"}, {"envelope": {"plan": 7}},
                                                    {"envelope": {"plan": "x"}}])
    assert (run.state, run.outcome) == ("ended", "needs-me")
    assert "plan" in run.reason and "3 times" in run.reason
    steps = open_store(home).query("steps", {"run_id": run.id})
    assert [(s.attempt, s.passed, s.failure) for s in steps] == [(n, False, "malformed") for n in (1, 2, 3)]
    assert "did not end with a JSON object" in fake.calls[1]["prompt"]   # told what was wrong
    assert fake_notify[-1][0] == f"Run {run.id}: needs-me"


@pytest.mark.fr("FR-032")
def test_a_planner_that_changes_a_file_is_undone_and_the_run_stops(home, target, fake_notify):
    run, _ = planned(target, fake_notify, script=[{"envelope": PLAN, "files": {"sneaky.py": "x\n"}}])
    assert run.outcome == "needs-me" and "sneaky.py" in run.reason
    assert git(run.workspace, "status", "--porcelain") == ""
    store = open_store(home)
    assert store.query("steps", {"run_id": run.id})[0].failure == "guard"
    assert "guard" in [e.kind for e in records.events_after(store, run.id)]


# ---- Story 3: seeing what a run is doing, and reading back what it did ----

def finished(target, fake_notify, entries=None):
    """Carry a request all the way to its end, with one plan revision on the way."""
    entries = entries or ([{"envelope": PLAN}] + script())
    fake = FakeAgent(entries)
    drive_with(fake)
    run = operations.request("Add a greeting", target)
    operations.revise(run.id, "Keep it small.")
    return operations.approve(run.id)


@pytest.mark.fr("FR-026")
@pytest.mark.fr("FR-028")
@pytest.mark.fr("FR-010")
def test_show_returns_the_whole_run_as_typed_records(home, target, fake_notify):
    run = finished(target, fake_notify)
    view = operations.show(run.id)
    assert dataclasses.is_dataclass(view) and view.run.id == run.id
    assert (view.run.outcome, view.run.attempt_limit, view.run.request) == ("accepted", 3, "Add a greeting")
    assert [(p.version, p.decision, p.comment) for p in view.plans] == [(1, "revised", "Keep it small."), (2, "approved", None)]
    assert [s.name for s in view.steps] == ["plan", "plan", "baseline", "write_tests", "red", "build", "test",
                                            "architecture_review", "document", "review", "finish"]
    for step in view.steps:
        assert step.started_at and step.ended_at and step.ended_at >= step.started_at
        assert step.checks and all(set(c) == {"name", "passed", "note", "output", "timed_out", "contained", "smell",
                                                  "measured"} for c in step.checks)
        assert (step.persona is not None) == (step.kind == "agent")
        assert bool(step.asked) == (step.kind == "agent")
    assert view.steps[3].produced["edge_cases"] == ["an empty name"]
    assert view.events == []                                  # the listing does not carry every event
    assert operations.show().run.id == run.id                 # no id: the most recent run


@pytest.mark.fr("FR-026")
def test_show_one_step_returns_it_with_its_events(home, target, fake_notify):
    run = finished(target, fake_notify)
    build = [s for s in operations.show(run.id).steps if s.name == "build"][0]
    view = operations.show(run.id, step=build.id)
    assert [s.id for s in view.steps] == [build.id]
    kinds = [e.kind for e in view.events]
    assert kinds[0] == "step_start" and kinds[-1] == "step_end" and "check" in kinds and "agent_text" in kinds
    assert all(e.step_id == build.id for e in view.events)
    with pytest.raises(Refused, match="no step 9999"):
        operations.show(run.id, step=9999)


@pytest.mark.fr("FR-025")
def test_follow_returns_only_what_came_after(home, target, fake_notify):
    run = finished(target, fake_notify)
    everything = operations.follow(run.id)
    assert [e.id for e in everything] == sorted(e.id for e in everything) and len(everything) > 30
    middle = everything[10].id
    later = operations.follow(run.id, after=middle)
    assert [e.id for e in later] == [e.id for e in everything[11:]]
    assert operations.follow(run.id, after=everything[-1].id) == []


@pytest.mark.fr("FR-027")
def test_status_lists_recent_runs_newest_first_with_their_last_step(home, target, fake_notify):
    first = finished(target, fake_notify)
    second, _ = planned(target, fake_notify)
    views = operations.status()
    assert [v.run.id for v in views] == [second.id, first.id]
    assert views[0].run.state == "awaiting_approval" and views[0].steps[-1].name == "plan"
    assert views[1].run.outcome == "accepted" and views[1].steps[-1].name == "finish"
    assert len(operations.status(limit=1)) == 1


@pytest.mark.fr("FR-029")
def test_a_run_whose_driver_id_now_belongs_to_another_process_is_interrupted(home, target, fake_notify):
    import os
    run, _ = planned(target, fake_notify)
    store = open_store(home)
    records.set_state(store, run.id, "working", current_step="build", driver_pid=os.getpid(),
                         driver_started="not-this-process")   # same id, different start time
    seen = operations.status()[0].run
    assert (seen.state, seen.outcome, seen.reason) == ("ended", "needs-me", "interrupted")
    assert fake_notify[-1] == (f"Run {run.id}: needs-me", "interrupted")
    assert [s.name for s in operations.show(run.id).steps] == ["plan"]     # what was recorded is kept
    assert operations.status()[0].run.state == "ended"                     # and it stays ended


@pytest.mark.fr("FR-004")
@pytest.mark.fr("FR-012")
def test_the_operators_comments_travel_with_the_request_to_every_later_step(home, target, fake_notify):
    """Found on a real run: the reviewer called the operator's own revision 'not asked for'."""
    fake = FakeAgent([{"envelope": PLAN}] + script())
    drive_with(fake)
    run = operations.request("Add a greeting", target)
    operations.revise(run.id, "Also greet in French.")
    done = operations.approve(run.id)
    assert done.outcome == "accepted"
    later = {name: call["prompt"] for name, call in
             zip(["write_tests", "build", "architecture_review", "document", "review"], fake.calls[2:])}
    for name, prompt in later.items():
        assert "Add a greeting" in prompt, name
        assert "Also greet in French." in prompt, f"the {name} step never saw the operator's comment"
    assert "Also greet in French." not in fake.calls[0]["prompt"]       # the first plan was written before it


@pytest.mark.fr("FR-016")
def test_a_home_made_by_an_earlier_version_is_refused_in_words(home, target):
    import sqlite3
    old = sqlite3.connect(home / "factory.db")
    old.execute("CREATE TABLE runs (id INTEGER PRIMARY KEY, request TEXT)")     # no version stamp
    old.commit()
    old.close()
    with pytest.raises(Refused, match=r"cannot\s+read"):
        operations.status()
    with pytest.raises(Refused, match=r"cannot\s+read"):
        operations.request("Do something", target)
