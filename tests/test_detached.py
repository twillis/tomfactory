"""The real detached driver: the operator is not needed, and nothing is left running."""
import json
import os
import stat
import time

import pytest

from factory import operations, proc, records
from factory.store import open_store
from tests.conftest import PLAN, script


@pytest.fixture
def detached(tmp_path, monkeypatch, home, target):
    """Run real driver processes against the fake agent, with a silent desktop."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    silent = bin_dir / "notify-send"
    silent.write_text(f"#!/bin/sh\necho \"$1|$2\" >> {tmp_path / 'notifications.txt'}\n")
    silent.chmod(silent.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("TOMFACTORY_AGENT", "tests.fake_agent:run_agent")
    script = tmp_path / "script.json"
    monkeypatch.setenv("TOMFACTORY_FAKE_SCRIPT", str(script))

    def use(entries):
        script.write_text(json.dumps(entries))

    use.release = tmp_path / "release"
    use.notifications = tmp_path / "notifications.txt"
    use.home, use.target = home, target
    yield use
    for run in open_store(home).query("runs", order="-id", limit=20):   # leave nothing behind, whatever the test did
        proc.stop_group(run.child_pgid, grace=0.5)
        if run.driver_pid:
            proc.stop_group(run.driver_pid, grace=0.5)


def wait_for(condition, seconds=15.0, what="the condition"):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = condition()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {what}")


def current(home, run_id):
    return open_store(home).get("runs", run_id)


@pytest.mark.fr("FR-005")
@pytest.mark.fr("FR-014")
def test_request_returns_at_once_and_the_plan_arrives_without_the_operator(detached):
    detached([{"envelope": PLAN, "block": str(detached.release)}])
    started = time.monotonic()
    run = operations.request("Create a hello page", detached.target)
    assert time.monotonic() - started < 5, "request must not wait for the plan"

    run = wait_for(lambda: (r := current(detached.home, run.id)).child_pgid and r, what="the plan step to start")
    assert run.state == "planning" and run.current_step == "plan"
    assert proc.is_alive(run.driver_pid, run.driver_started)
    driver_pid, child_group = run.driver_pid, run.child_pgid

    detached.release.write_text("go")
    run = wait_for(lambda: (r := current(detached.home, run.id)).state == "awaiting_approval" and r,
                   what="the run to wait for approval")
    assert (run.driver_pid, run.driver_started, run.child_pgid) == (None, None, None)
    assert (detached.home / "runs" / str(run.id) / "driver.log").exists()
    assert records.current_plan(open_store(detached.home), run.id).text == PLAN["plan"]
    wait_for(lambda: proc.started_at(driver_pid) is None, what="the driver process to exit")
    assert not proc._signal_group(child_group, 0), "the plan step's process group is still alive"
    assert "plan ready" in detached.notifications.read_text()


def approved_and_blocked(detached, entries):
    """Request, approve, and wait until a later step is blocked inside a real child process."""
    detached(entries)
    run = operations.request("Create a hello page", detached.target)
    wait_for(lambda: current(detached.home, run.id).state == "awaiting_approval", what="the plan")
    operations.approve(run.id)
    return wait_for(lambda: (r := current(detached.home, run.id)).child_pgid and r.current_step == "write_tests" and r,
                    what="the write_tests step to start")


@pytest.mark.fr("FR-014")
@pytest.mark.fr("FR-029")
@pytest.mark.fr("FR-017")
def test_stop_ends_everything_the_run_started_and_keeps_its_record(detached):
    run = approved_and_blocked(detached, [{"envelope": PLAN}, {"block": True}])
    assert run.state == "working" and run.current_step == "write_tests"
    driver_pid, started, child_group = run.driver_pid, run.driver_started, run.child_pgid
    recorded = len(records.events_after(open_store(detached.home), run.id, limit=5000))

    stopped = operations.stop(run.id)

    assert (stopped.state, stopped.outcome, stopped.reason) == ("ended", "needs-me", "stopped by operator")
    assert not proc.is_alive(driver_pid, started), "the driver is still running"
    assert not proc._signal_group(child_group, 0), "the step's process group is still running"
    store = open_store(detached.home)
    assert [s.name for s in store.query("steps", {"run_id": run.id})] == ["plan", "baseline", "write_tests"]
    assert len(records.events_after(store, run.id, limit=5000)) >= recorded
    assert f"Run {run.id}: needs-me|stopped by operator" in detached.notifications.read_text()
    with pytest.raises(operations.Refused, match="not running"):
        operations.stop(run.id)


@pytest.mark.fr("FR-014")
def test_stop_applies_while_planning_and_is_refused_while_waiting(detached):
    detached([{"block": True}])
    run = operations.request("Create a hello page", detached.target)
    run = wait_for(lambda: (r := current(detached.home, run.id)).child_pgid and r, what="the plan step to start")
    child_group = run.child_pgid
    stopped = operations.stop(run.id)
    assert stopped.outcome == "needs-me" and stopped.reason == "stopped by operator"
    assert not proc._signal_group(child_group, 0)

    operations.abandon(run.id)          # set aside, so the next request is not held behind it (FR-161)
    detached([{"envelope": PLAN}])
    (detached.home.parent / "script.calls.jsonl").unlink()
    waiting = operations.request("Another", detached.target)
    wait_for(lambda: current(detached.home, waiting.id).state == "awaiting_approval", what="the plan")
    with pytest.raises(operations.Refused, match="not running"):
        operations.stop(waiting.id)


@pytest.mark.fr("FR-005")
def test_after_approval_the_whole_cycle_runs_with_no_further_call(detached):
    detached(script())
    run = operations.request("Add a greeting", detached.target)
    wait_for(lambda: current(detached.home, run.id).state == "awaiting_approval", what="the plan")
    operations.approve(run.id)                      # the last thing the operator does
    done = wait_for(lambda: (r := current(detached.home, run.id)).state == "ended" and r, seconds=60,
                    what="the run to end")
    assert done.outcome == "accepted", done.reason
    wait_for(lambda: f"Run {run.id}: accepted" in detached.notifications.read_text(), what="the notification")
    assert (done.driver_pid, done.child_pgid) == (None, None)


@pytest.mark.fr("FR-027")
def test_status_shows_the_step_in_progress_and_what_came_before(detached):
    run = approved_and_blocked(detached, [{"envelope": PLAN}, {"block": True}])
    view = operations.status()[0]
    assert view.run.id == run.id and view.run.state == "working" and view.run.current_step == "write_tests"
    assert [(s.name, s.passed) for s in view.steps] == [("plan", True), ("baseline", True), ("write_tests", None)]
    current_step = view.steps[-1]
    assert current_step.started_at and current_step.ended_at is None      # visible while it runs
    operations.stop(run.id)


@pytest.mark.fr("FR-029")
@pytest.mark.fr("FR-014")
@pytest.mark.fr("FR-017")
def test_a_killed_driver_is_noticed_and_its_orphaned_step_is_stopped(detached):
    import os
    import signal
    run = approved_and_blocked(detached, [{"envelope": PLAN}, {"block": True}])
    driver_pid, started, child_group = run.driver_pid, run.driver_started, run.child_pgid
    recorded = len(records.events_after(open_store(detached.home), run.id, limit=5000))

    os.kill(driver_pid, signal.SIGKILL)                       # no chance to clean up
    wait_for(lambda: not proc.is_alive(driver_pid, started), what="the driver to die")
    assert proc._signal_group(child_group, 0), "the test needs the orphaned step to still be running"
    assert current(detached.home, run.id).state == "working"  # nothing has noticed yet

    seen = operations.status()[0].run                         # the next command of any kind notices
    assert (seen.state, seen.outcome, seen.reason) == ("ended", "needs-me", "interrupted")
    assert not proc._signal_group(child_group, 0), "the orphaned step is still running"
    store = open_store(detached.home)
    assert len(records.events_after(store, run.id, limit=5000)) >= recorded
    assert [s.name for s in store.query("steps", {"run_id": run.id})] == ["plan", "baseline", "write_tests"]
    assert f"Run {run.id}: needs-me|interrupted" in detached.notifications.read_text()
    assert operations.status()[0].run.state == "ended"
