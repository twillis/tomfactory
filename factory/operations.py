"""Control: operations. What the operator can do to a run, and when it is refused.

The Run is the resource. Each function below is one operation on it and reads top to
bottom the same way: find the run, check its state, do the work through the store's repos.
Every operation returns plain data — rows as mappings; turning that into text is the command line's job.
When an operation cannot go ahead it raises `Refused` with a reason the operator can read.
"""
import os
import pathlib
import shutil
import sys
from dataclasses import dataclass, field

from factory import agent, config, driver, proc, records, speckit, workflow, workspace
from factory import workflow as flow     # for the one function that takes an argument named workflow
from factory.store import open_store
from factory.workspace import Workspace


class Refused(Exception):
    """The operation was not carried out; the message says why."""


@dataclass
class RunView:
    """A run with what belongs to it, for showing."""
    run: dict
    plans: list
    steps: list
    events: list
    questions: list = field(default_factory=list)      # every question asked in the run, and its answer


@dataclass
class Health:
    """One thing the factory needs, and whether it is there."""
    name: str
    ok: bool
    detail: str


def _open():
    try:
        store = open_store(config.home())
    except RuntimeError as problem:     # a home this version cannot read
        raise Refused(str(problem)) from None
    reconcile(store)
    return store


def reconcile(store) -> None:
    """Notice a run whose driver has died, and end it. Called at the start of every operation.

    A run is only ever "planning" or "working" while a driver process carries it. If that
    process is gone — killed, crashed, the machine restarted — the run is ended as needs-me,
    "interrupted", and anything the driver left running is stopped.
    """
    run = records.open_run(store)
    if (run and run.state in ("planning", "working") and run.driver_pid
            and not proc.is_alive(run.driver_pid, run.driver_started)):
        driver.end_run(store, run.id, "needs-me", "interrupted")


def _find(store, run_id) -> dict:
    """The run with this id, or the most recent run when no id is given."""
    if run_id is None:
        latest = store.query("runs", order="-id", limit=1)
        if not latest:
            raise Refused("there are no runs yet")
        return latest[0]
    try:
        return store.get("runs", run_id)
    except LookupError:
        raise Refused(f"there is no run {run_id}") from None


def _waiting(store, run_id, with_question=False) -> dict:
    """The run, if it is waiting for the operator's decision; refused otherwise."""
    run = _find(store, run_id)
    if run.state != "awaiting_approval":
        described = run.outcome or run.state.replace("_", " ")
        raise Refused(f"run {run.id} is not waiting for a decision; it is {described}")
    asked = records.pending_question(store, run.id)
    if asked and not with_question:     # a run is not approved past a question that is still waiting
        raise Refused(f"run {run.id} is waiting for the answer to a question, not for approval: "
                      f"{asked.question}  Answer it with:  factory answer \"...\"")
    return run


def launch(store, run, state, step) -> None:
    """Hand a run to a detached driver process, which carries it on after this command returns."""
    with store.files.driver_log(run.id) as log:
        pid = proc.spawn_detached([sys.executable, "-m", "factory", "_drive", str(run.id)],
                                  cwd=config.PACKAGE_DIR.parent, log=log, env=os.environ.copy())
    # State, step and process are written together, so the run is never "working" with no driver.
    records.set_state(store, run.id, state, current_step=step, driver_pid=pid,
                         driver_started=proc.started_at(pid))


def get_run(run_id=None) -> dict:
    return _find(_open(), run_id)


def init_target(path, spec_kit=False) -> pathlib.Path:
    """Create a new target codebase: a git repository with the default settings committed.

    With `spec_kit`, spec kit is set up in it too, and the planner will write spec kit's
    own specification and plan documents there.
    """
    path = pathlib.Path(path)
    if path.exists() and any(path.iterdir()):
        raise Refused(f"{path} already has content; init-target only creates a new codebase")
    path.mkdir(parents=True, exist_ok=True)

    def git(*command):
        code, _, err = proc.capture(["git", *command], cwd=path)
        if code != 0:
            raise Refused(f"git {command[0]} failed in {path}: {err.strip()}")

    git("init", "-q", "-b", "main")
    if spec_kit:
        try:
            speckit.install(path)
        except speckit.SpecKitError as problem:
            raise Refused(str(problem)) from None
    (path / ".factory.toml").write_text(config.DEFAULT_FACTORY_TOML)
    (path / ".gitignore").write_text(config.DEFAULT_GITIGNORE)
    (path / "README.md").write_text(f"# {path.name}\n\nBuilt by the factory, one request at a time.\n")
    git("add", "-A")
    git(*workspace.AUTHOR, "commit", "-q", "-m", "factory: new target codebase")
    return path


def request(text, target, attempts=3, workflow="change", launcher=None) -> dict:
    """Hand the factory a request. A plan is written in the background; then the run waits."""
    store = _open()
    if not text.strip():
        raise Refused("the request is empty; say what you want changed")
    if attempts < 1:
        raise Refused("the attempt limit must be at least 1")
    target = pathlib.Path(target).resolve()
    try:
        base = config.head_commit(target)
        config.read_target_config(target, base)
    except config.ConfigError as problem:
        raise Refused(str(problem)) from None
    open_run = records.open_run(store)
    if open_run:    # one run at a time (FR-033)
        raise Refused(f"run {open_run.id} has not ended ({open_run.state.replace('_', ' ')});"
                      " let it finish, or stop or abandon it, before making another request")

    try:
        first = flow.table_for(speckit.available(target), workflow)[0].name
    except ValueError as problem:
        raise Refused(str(problem)) from None
    run = records.new_run(store, text.strip(), target, base, ideals=config.read_ideals(),
                            attempt_limit=attempts, current_step=first, workflow=workflow)
    try:
        Workspace.create(target, run.workspace, run.branch)
        workspace.snapshot(config.factory_paths(), store.files.snapshot_dir(run.id))
    except Exception as problem:
        driver.end_run(store, run.id, "needs-me", f"the run's checkout could not be created: {problem}")
        raise Refused(f"the run's checkout could not be created: {problem}") from None
    (launcher or launch)(store, run, "planning", first)
    return store.get("runs", run.id)


def plan(run_id=None) -> dict:
    """The current version of a run's plan."""
    store = _open()
    run = _find(store, run_id)
    current = records.current_plan(store, run.id)
    if current is None:
        raise Refused(f"run {run.id} has no plan yet")
    return current


def _table(run) -> list:
    """The steps this run goes through, chosen by its codebase."""
    return workflow.table_for(speckit.available(run.workspace), run.workflow)


def _carry_on(store, run, decision, launcher) -> dict:
    """After a decision at a wait: launch a driver at whatever step that decision leads to."""
    table = _table(run)
    then = workflow.after_wait(decision, workflow.get(run.current_step, table), table)
    state = "planning" if workflow.is_planning(then.step, table) else "working"
    (launcher or launch)(store, run, state, then.step)
    return store.get("runs", run.id)


def approve(run_id=None, launcher=None) -> dict:
    """Approve what is waiting. The run carries on to its next wait, or to its end, unattended."""
    store = _open()
    run = _waiting(store, run_id)
    records.decide(store, run.id, "approved")
    approved = Workspace(run.workspace, run.target, run.branch, run.base_commit).head()
    records.event(store, run.id, "approved", f"approved at {run.current_step}", {"commit": approved})
    return _carry_on(store, run, "approve", launcher)


def revise(run_id=None, comment="", launcher=None) -> dict:
    """Send what is waiting back with a comment. Its stage is done again, in the background."""
    store = _open()
    run = _waiting(store, run_id)
    if not comment.strip():
        raise Refused("say what to change: a plan is sent back with a comment")
    records.decide(store, run.id, "revised", comment=comment.strip())
    return _carry_on(store, run, "revise", launcher)


def abandon(run_id=None) -> dict:
    """Give up on a request whose plan is waiting. Nothing in the target was changed."""
    store = _open()
    run = _waiting(store, run_id, with_question=True)
    if records.current_plan(store, run.id):
        records.decide(store, run.id, "abandoned")
    table = _table(run)
    then = workflow.after_wait("abandon", workflow.get(run.current_step, table), table)
    Workspace(run.workspace, run.target, run.branch, run.base_commit).remove()
    return driver.end_run(store, run.id, then.outcome, then.reason)



def stop(run_id=None) -> dict:
    """Stop a run that is being worked. Nothing it started is left running; its record is kept."""
    store = _open()
    run = _find(store, run_id)
    if run.state not in ("planning", "working"):
        raise Refused(f"run {run.id} is not running; it is {run.outcome or run.state.replace('_', ' ')}")
    proc.terminate(run.driver_pid, run.driver_started)     # the driver stops its step and ends the run
    proc.stop_group(store.get("runs", run.id).child_pgid)      # in case the driver could not
    return driver.end_run(store, run.id, "needs-me", "stopped by operator")


def resume(run_id=None, launcher=None) -> dict:
    """Carry on a run that stopped as needs-me, from the step it stopped at. Earlier work is kept."""
    store = _open()
    run = _find(store, run_id)
    if run.outcome != "needs-me":
        now = run.outcome if run.state == "ended" else run.state.replace("_", " ")
        raise Refused(f"run {run.id} cannot be resumed: only a run that ended as needs-me can be, and it is {now}")
    if not pathlib.Path(run.workspace).is_dir():
        raise Refused(f"run {run.id}'s checkout no longer exists, so there is nothing to carry on from")
    other = records.open_run(store)
    if other:
        raise Refused(f"run {other.id} has not ended; let it finish, or stop or abandon it, before resuming another")
    checkout = Workspace(run.workspace, run.target, run.branch, run.base_commit)
    checkout.undo()                     # whatever the stopped step left half-done
    workspace.snapshot(config.factory_paths(), store.files.snapshot_dir(run.id))   # the factory as it is now
    state = "planning" if workflow.is_planning(run.current_step, _table(run)) else "working"
    run = records.reopen(store, run.id, state)
    (launcher or launch)(store, run, state, run.current_step)
    return store.get("runs", run.id)

def answer(run_id=None, text="", launcher=None) -> dict:
    """Answer the question a run is waiting on. The step that asked runs again with the answer."""
    store = _open()
    run = _find(store, run_id)
    asked = records.pending_question(store, run.id)
    if asked is None:
        raise Refused(f"run {run.id} has no question waiting for an answer")
    if not text.strip():
        raise Refused(f"give an answer to: {asked.question}")
    records.answer(store, asked.id, text.strip(), "operator")
    state = "planning" if workflow.is_planning(run.current_step, _table(run)) else "working"
    (launcher or launch)(store, run, state, run.current_step)
    return store.get("runs", run.id)


def status(limit=10) -> list[RunView]:
    """The most recent runs, newest first, each with its steps so far."""
    store = _open()
    return [RunView(run, [], store.query("steps", {"run_id": run.id}), [],
                    store.query("questions", {"run_id": run.id}))
            for run in store.query("runs", order="-id", limit=limit)]


def show(run_id=None, step=None) -> RunView:
    """A whole run; or, given a step record's id, that one step with everything that happened in it."""
    store = _open()
    run = _find(store, run_id)
    steps = store.query("steps", {"run_id": run.id})
    questions = store.query("questions", {"run_id": run.id})
    if step is None:
        return RunView(run, store.query("plans", {"run_id": run.id}), steps, [], questions)
    chosen = [record for record in steps if record.id == step]
    if not chosen:
        raise Refused(f"run {run.id} has no step {step}")
    return RunView(run, [], chosen, store.query("events", {"step_id": step}), questions)


def follow(run_id=None, after=0) -> list:
    """The events of a run recorded after the one with this id."""
    store = _open()
    return records.events_after(store, _find(store, run_id).id, after)


def ideals() -> tuple[pathlib.Path, str]:
    """Where the operator's ideals are kept, and what they say."""
    return config.ideals_path(), config.read_ideals()


def edit_ideals() -> pathlib.Path:
    """Open the ideals in the operator's editor."""
    path = config.ideals_path()
    path.touch()
    if proc.interactive([os.environ.get("EDITOR", "nano"), str(path)]) != 0:
        raise Refused(f"the editor did not open; edit {path} by hand")
    return path


def doctor() -> list[Health]:
    """Check that everything the factory needs is present and working."""
    found = []
    try:
        code, out, _ = proc.capture(["git", "--version"], cwd="/")
        found.append(Health("git", code == 0, out.strip()))
    except OSError as problem:
        found.append(Health("git", False, str(problem)))
    with open(os.devnull, "w") as nowhere:
        reply = agent.get_adapter()(
            persona="You answer in one word.", prompt="Reply with the single word: ready",
            cwd=config.home(), capabilities="read", timeout=120, on_event=lambda *event: None,
            raw_sink=lambda line: None, stderr_file=nowhere)
    found.append(Health("agent", reply.ok, "answered on your subscription" if reply.ok else str(reply.error)))
    notifier = shutil.which("notify-send")
    found.append(Health("notification", bool(notifier), notifier or "notify-send is not installed"))
    home = config.home()
    found.append(Health("home", os.access(home, os.W_OK), str(home)))
    return found


def drive(run_id) -> None:
    """What a detached driver process runs. Not something the operator calls."""
    driver.drive(open_store(config.home()), run_id)
