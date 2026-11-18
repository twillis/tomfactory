"""Record-keeping rules: what must be true of a run's record, whoever writes it.

These used to hide inside per-table repo classes. They are business rules, so they live
in the control layer (factory/records.py) and use the gateway's five plain operations.
"""
import sqlite3
import threading

import pytest

from factory import records
from factory.store import open_store


@pytest.fixture
def gw(home):
    return open_store(home)


def new_run(gw, request="Create a hello page", **kw):
    return records.new_run(gw, request=request, target="/tmp/target", base_commit="abc123", **kw)


@pytest.mark.fr("FR-001")
def test_a_new_run_gets_its_branch_and_checkout_and_starts_planning(gw, home):
    run = new_run(gw, "Create a hello-world app, please!")
    assert (run.state, run.outcome, run.attempt_limit) == ("planning", None, 3)
    assert run.branch == f"factory/{run.id}-create-a-hello-world-app-please"
    assert run.workspace == str(home / "workspaces" / str(run.id))
    assert run.created_at.endswith("Z")
    assert [e.kind for e in records.events_after(gw, run.id)] == ["run_state"]
    custom = dict(ideals="Layers.\n", attempt_limit=2, current_step="plan")
    records.end(gw, run.id, "rejected", "test")
    second = new_run(gw, **custom)
    assert {k: second[k] for k in custom} == custom


@pytest.mark.fr("FR-001")
@pytest.mark.parametrize("request_text, slug", [
    ("!!!", "run"),
    ("Fix   the\tBUG now", "fix-the-bug-now"),
    ("one two three four five six seven", "one-two-three-four-five"),
    ("x" * 200, "x" * 40),
])
def test_the_branch_slug_follows_the_rule(request_text, slug):
    assert records.slug(request_text) == slug


@pytest.mark.fr("FR-033")
@pytest.mark.fr("FR-001")
def test_one_open_run_at_a_time_and_ids_are_never_reused(gw):
    first = new_run(gw)
    with pytest.raises(sqlite3.IntegrityError):
        new_run(gw, "another")
    assert records.open_run(gw).id == first.id
    records.end(gw, first.id, "rejected", "abandoned by operator")
    assert records.open_run(gw) is None
    second = new_run(gw)
    assert second.id == first.id + 1


@pytest.mark.fr("FR-015")
@pytest.mark.fr("FR-016")
def test_a_state_change_writes_its_own_history_and_a_run_ends_once(gw):
    run = new_run(gw)
    before = len(records.events_after(gw, run.id))
    updated = records.set_state(gw, run.id, "awaiting_approval", current_step="plan")
    assert (updated.state, updated.current_step) == ("awaiting_approval", "plan")
    added = records.events_after(gw, run.id)[before:]
    assert [e.kind for e in added] == ["run_state"] and added[0].payload["state"] == "awaiting_approval"

    records.move(gw, run.id, driver_pid=4321, driver_started="99", child_pgid=4322)
    ended = records.end(gw, run.id, "needs-me", "stopped by operator")
    assert (ended.state, ended.outcome, ended.reason) == ("ended", "needs-me", "stopped by operator")
    assert ended.ended_at and ended.ended_at.endswith("Z")
    assert (ended.driver_pid, ended.driver_started, ended.child_pgid) == (None, None, None)
    assert records.events_after(gw, run.id)[-1].payload == {"state": "ended", "outcome": "needs-me",
                                                            "reason": "stopped by operator"}
    with pytest.raises(ValueError, match="already ended"):
        records.end(gw, run.id, "accepted", "again")
    with pytest.raises(ValueError, match="end\\(\\)"):
        records.set_state(gw, run.id, "ended")            # a run is ended only through end()
    with pytest.raises(ValueError, match="request"):
        records.move(gw, run.id, request="rewritten")     # only the fields that move may be moved


@pytest.mark.fr("FR-004")
def test_plan_versions_are_kept_and_the_decision_is_on_the_current_one(gw):
    run = new_run(gw)
    first = records.add_plan(gw, run.id, "plan one", ["follows layers"], [])
    assert (first.version, first.decision, first.comment) == (1, "pending", None)
    records.decide(gw, run.id, "revised", comment="also show the end time")
    second = records.add_plan(gw, run.id, "plan two", [], ["conflicts with ideal X"])
    assert second.version == 2 and records.current_plan(gw, run.id) == second
    plans = gw.query("plans", {"run_id": run.id})
    assert [(p.version, p.decision, p.comment) for p in plans] == [
        (1, "revised", "also show the end time"), (2, "pending", None)]
    assert plans[0].ideals_addressed == ["follows layers"] and plans[1].conflicts == ["conflicts with ideal X"]
    assert records.decide(gw, run.id, "approved").version == 2
    assert records.current_plan(gw, 99) is None


@pytest.mark.fr("FR-026")
@pytest.mark.fr("FR-027")
@pytest.mark.fr("FR-028")
@pytest.mark.fr("FR-047")
def test_a_step_is_on_record_from_its_start_and_every_execution_is_an_attempt(gw):
    run = new_run(gw)
    step = records.start_step(gw, run.id, "build", "agent", "code_writer", "the full prompt")
    assert (step.attempt, step.persona, step.asked) == (1, "code_writer", "the full prompt")
    assert step.ended_at is None and step.passed is None
    assert gw.query("steps", {"run_id": run.id})[0].ended_at is None        # visible while it runs

    checks = [{"name": "tests_pass", "passed": False, "note": "1 failed"}]
    done = records.finish_step(gw, step.id, produced={"summary": "did it"}, checks=checks, passed=False,
                               failure="check", tokens={"input": 10, "output": 5}, cost_estimate=0.01)
    assert done.ended_at and done.passed is False and done.failure == "check"
    assert (done.produced, done.checks, done.cost_estimate) == ({"summary": "did it"}, checks, 0.01)
    with pytest.raises(ValueError, match="already finished"):
        records.finish_step(gw, step.id, produced=None, checks=[], passed=True)

    again = records.start_step(gw, run.id, "build", "agent", "code_writer", "second prompt")
    other = records.start_step(gw, run.id, "test", "code", None, "")
    assert (again.attempt, other.attempt, other.persona) == (2, 1, None)
    assert records.attempts(gw, run.id, "build") == 2 and records.attempts(gw, run.id, "review") == 0


@pytest.mark.fr("FR-025")
def test_the_follow_query_never_misses_or_repeats_while_another_connection_writes(gw, home):
    run = new_run(gw)
    start = records.events_after(gw, run.id)[-1].id
    writer = open_store(home)

    def write():
        for number in range(200):
            records.event(writer, run.id, "agent_text", f"line {number}", {"n": number})

    thread = threading.Thread(target=write)
    thread.start()
    seen, cursor = [], start
    while thread.is_alive() or len(seen) < 200:
        batch = records.events_after(gw, run.id, cursor, limit=7)
        if batch:
            seen += [e.payload["n"] for e in batch]
            cursor = batch[-1].id
    thread.join()
    assert seen == list(range(200))
    step = records.start_step(gw, run.id, "plan", "agent", "planner", "p")
    added = records.event(gw, run.id, "tool_call", "edit: a.py", {"ok": True}, step_id=step.id)
    assert added.id > cursor and added.payload == {"ok": True}
    assert [e.summary for e in gw.query("events", {"step_id": step.id})] == ["edit: a.py"]
