"""The store: five repos over one SQLite file and a folder of per-run files.

The schema is the contract with the observability app (contracts/run-store.md).
"""
import dataclasses
import sqlite3
import threading

import pytest

from factory import store as store_module
from factory.store import Event, Plan, Run, StepRecord, open_store


@pytest.fixture
def store(home):
    return open_store(home)


def new_run(store, request="Create a hello page", **kw):
    return store.runs.create(request=request, target="/tmp/target", base_commit="abc123", **kw)


@pytest.mark.fr("FR-025")
def test_a_new_store_has_the_contract_schema_in_wal_mode(store, home):
    db = sqlite3.connect(home / "factory.db")
    names = {row[0] for row in db.execute("select name from sqlite_master")}
    assert {"runs", "plans", "steps", "events", "one_open_run", "one_approved_plan",
            "events_by_run", "steps_by_run"} <= names
    assert db.execute("pragma journal_mode").fetchone()[0] == "wal"
    columns = {row[1] for row in db.execute("pragma table_info(runs)")}
    assert columns == {"id", "request", "target", "base_commit", "branch", "workspace", "state",
                       "current_step", "outcome", "reason", "ideals", "attempt_limit", "driver_pid",
                       "driver_started", "child_pgid", "created_at", "ended_at"}
    columns = {row[1] for row in db.execute("pragma table_info(steps)")}
    assert columns == {"id", "run_id", "name", "kind", "persona", "attempt", "asked", "produced",
                       "checks", "passed", "failure", "started_at", "ended_at", "tokens", "cost_estimate"}
    columns = {row[1] for row in db.execute("pragma table_info(plans)")}
    assert columns == {"run_id", "version", "text", "ideals_addressed", "conflicts", "comment",
                       "decision", "created_at"}
    columns = {row[1] for row in db.execute("pragma table_info(events)")}
    assert columns == {"id", "run_id", "step_id", "at", "kind", "summary", "payload"}


@pytest.mark.fr("FR-001")
def test_creating_a_run_sets_its_branch_and_workspace(store, home):
    run = new_run(store, "Create a hello-world app, please!")
    assert isinstance(run, Run)
    assert run.state == "planning" and run.outcome is None and run.attempt_limit == 3
    assert run.branch == f"factory/{run.id}-create-a-hello-world-app-please"
    assert run.workspace == str(home / "workspaces" / str(run.id))
    assert run.workspace == str(store.files.workspace_path(run.id))
    assert run.created_at.endswith("Z")


@pytest.mark.fr("FR-001")
@pytest.mark.parametrize("request_text, slug", [
    ("!!!", "run"),
    ("Fix   the\tBUG now", "fix-the-bug-now"),
    ("one two three four five six seven", "one-two-three-four-five"),
    ("x" * 200, "x" * 40),
])
def test_the_branch_slug_follows_the_rule(store, request_text, slug):
    run = new_run(store, request_text)
    assert run.branch == f"factory/{run.id}-{slug}"
    store.runs.end(run.id, "rejected", "test")


@pytest.mark.fr("FR-033")
def test_a_second_open_run_is_refused_by_the_database(store):
    new_run(store)
    with pytest.raises(sqlite3.IntegrityError):
        new_run(store, "another")


@pytest.mark.fr("FR-001")
def test_run_ids_are_never_reused(store):
    first = new_run(store)
    store.runs.end(first.id, "rejected", "abandoned by operator")
    second = new_run(store)
    assert second.id == first.id + 1
    assert store.runs.latest().id == second.id
    assert [r.id for r in store.runs.all()] == [second.id, first.id]
    assert store.runs.open().id == second.id


@pytest.mark.fr("FR-015")
@pytest.mark.fr("FR-016")
def test_state_changes_write_their_own_history_and_ending_is_once(store):
    run = new_run(store)
    before = len(store.events.after(run.id))
    updated = store.runs.set_state(run.id, "awaiting_approval", current_step="plan")
    assert updated.state == "awaiting_approval" and updated.current_step == "plan"
    added = store.events.after(run.id)[before:]
    assert [e.kind for e in added] == ["run_state"]
    assert added[0].payload["state"] == "awaiting_approval"

    store.runs.update(run.id, driver_pid=4321, driver_started="99", child_pgid=4322)
    ended = store.runs.end(run.id, "needs-me", "stopped by operator")
    assert (ended.state, ended.outcome, ended.reason) == ("ended", "needs-me", "stopped by operator")
    assert ended.ended_at and ended.ended_at.endswith("Z")
    assert (ended.driver_pid, ended.driver_started, ended.child_pgid) == (None, None, None)
    assert store.events.after(run.id)[-1].kind == "run_state"
    with pytest.raises(ValueError):
        store.runs.end(run.id, "accepted", "again")
    with pytest.raises(LookupError):
        store.runs.get(999)


@pytest.mark.fr("FR-004")
def test_plan_versions_are_kept_and_only_one_is_approved(store):
    run = new_run(store)
    first = store.plans.add(run.id, "plan one", ["follows layers"], [])
    assert isinstance(first, Plan) and first.version == 1 and first.decision == "pending"
    store.plans.decide(run.id, 1, "revised", comment="also show the end time")
    second = store.plans.add(run.id, "plan two", [], ["conflicts with ideal X"])
    assert second.version == 2
    plans = store.plans.list(run.id)
    assert [(p.version, p.decision, p.comment) for p in plans] == [
        (1, "revised", "also show the end time"), (2, "pending", None)]
    assert plans[0].text == "plan one" and plans[0].ideals_addressed == ["follows layers"]
    assert plans[1].conflicts == ["conflicts with ideal X"]
    assert store.plans.current(run.id).version == 2
    store.plans.decide(run.id, 2, "approved")
    with pytest.raises(sqlite3.IntegrityError):
        store.plans.decide(run.id, 1, "approved")


@pytest.mark.fr("FR-026")
@pytest.mark.fr("FR-027")
@pytest.mark.fr("FR-028")
@pytest.mark.fr("FR-047")
def test_step_records_exist_from_the_start_and_count_attempts(store):
    run = new_run(store)
    step = store.steps.start(run.id, "build", "agent", "code_writer", "the full prompt")
    assert isinstance(step, StepRecord)
    assert (step.attempt, step.persona, step.asked) == (1, "code_writer", "the full prompt")
    assert step.ended_at is None and step.passed is None and step.checks is None
    assert store.steps.list(run.id)[0].ended_at is None  # visible while running

    checks = [{"name": "envelope_valid", "passed": True, "note": ""},
              {"name": "tests_pass", "passed": False, "note": "1 failed"}]
    done = store.steps.finish(step.id, produced={"summary": "did it"}, checks=checks, passed=False,
                              failure="check", tokens={"input": 10, "output": 5}, cost_estimate=0.01)
    assert done.ended_at and done.passed is False and done.failure == "check"
    assert done.produced == {"summary": "did it"} and done.checks == checks
    assert done.tokens == {"input": 10, "output": 5} and done.cost_estimate == 0.01
    with pytest.raises(ValueError):
        store.steps.finish(step.id, produced=None, checks=[], passed=True)

    again = store.steps.start(run.id, "build", "agent", "code_writer", "second prompt")
    other = store.steps.start(run.id, "test", "code", None, "pytest")
    assert (again.attempt, other.attempt, other.persona) == (2, 1, None)
    assert store.steps.count(run.id, "build") == 2
    assert [s.name for s in store.steps.list(run.id)] == ["build", "build", "test"]
    assert store.steps.get(other.id).name == "test"


@pytest.mark.fr("FR-025")
def test_the_follow_query_never_misses_or_repeats_while_another_connection_writes(store, home):
    run = new_run(store)
    start = store.events.after(run.id)[-1].id
    writer = open_store(home)

    def write():
        for i in range(200):
            writer.events.add(run.id, "agent_text", f"line {i}", {"n": i})

    thread = threading.Thread(target=write)
    thread.start()
    seen, cursor = [], start
    while thread.is_alive() or len(seen) < 200:
        batch = store.events.after(run.id, cursor, limit=7)
        if batch:
            assert all(isinstance(e, Event) for e in batch)
            seen += [e.payload["n"] for e in batch]
            cursor = batch[-1].id
    thread.join()
    assert seen == list(range(200))
    ids = [e.id for e in store.events.after(run.id)]
    assert ids == sorted(ids) and len(set(ids)) == len(ids)
    step = store.steps.start(run.id, "plan", "agent", "planner", "p")
    store.events.add(run.id, "tool_call", "edit: a.py", {"ok": True}, step_id=step.id)
    assert [e.summary for e in store.events.for_step(step.id)] == ["edit: a.py"]


@pytest.mark.fr("FR-025")
def test_a_read_only_reader_is_not_blocked_by_an_open_write(store, home):
    run = new_run(store)
    store.db.execute("begin immediate")
    store.db.execute("insert into events(run_id, at, kind, summary, payload) values (?,?,?,?,?)",
                     (run.id, "now", "agent_text", "uncommitted", "{}"))
    reader = sqlite3.connect(f"file:{home / 'factory.db'}?mode=ro", uri=True, timeout=0.5)
    rows = reader.execute("select summary from events where run_id = ?", (run.id,)).fetchall()
    assert ("uncommitted",) not in rows and rows  # sees committed rows, does not wait
    store.db.execute("rollback")


@pytest.mark.fr("FR-026")
def test_records_are_typed_and_refuse_values_outside_their_sets(store):
    run = new_run(store)
    assert dataclasses.is_dataclass(run)
    assert dataclasses.asdict(run)["request"] == "Create a hello page"
    with pytest.raises(ValueError):
        dataclasses.replace(run, state="paused")
    with pytest.raises(ValueError):
        dataclasses.replace(run, outcome="great")
    with pytest.raises(ValueError):
        store.plans.decide(run.id, 1, "maybe")
    with pytest.raises(ValueError):
        store.steps.start(run.id, "plan", "robot", None, "x")
    step = store.steps.start(run.id, "plan", "agent", "planner", "x")
    with pytest.raises(ValueError):
        store.steps.finish(step.id, produced=None, checks=[], passed=False, failure="bored")
    with pytest.raises(ValueError):
        store.runs.update(run.id, request="rewritten")  # not a field that may change
    assert set(store_module.STATES) == {"planning", "awaiting_approval", "working", "ended"}
    assert set(store_module.OUTCOMES) == {"accepted", "rejected", "needs-me"}


@pytest.mark.fr("FR-025")
@pytest.mark.fr("FR-029")
def test_the_files_repo_owns_every_per_run_file(store, home):
    sink = store.files.raw_sink(7, 3)
    sink('{"type":"assistant"}')
    sink('{"type":"result"}')
    raw = home / "runs" / "7" / "steps" / "3.jsonl"
    assert raw.read_text() == '{"type":"assistant"}\n{"type":"result"}\n'  # on disk as it happens

    with store.files.stderr_file(7, 3) as err:
        err.write("warning\n")
    assert (home / "runs" / "7" / "steps" / "3.stderr").read_text() == "warning\n"

    with store.files.driver_log(7) as log:
        log.write("started\n")
    with store.files.driver_log(7) as log:
        log.write("again\n")
    assert (home / "runs" / "7" / "driver.log").read_text() == "started\nagain\n"

    assert store.files.snapshot_dir(7) == home / "runs" / "7" / "snapshot"
    assert store.files.workspace_path(7) == home / "workspaces" / "7"
