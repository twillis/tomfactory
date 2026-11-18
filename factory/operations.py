"""Control: operations. What the operator can do to a run, and when it is refused.

The Run is the resource. Each function below is one operation on it and reads top to
bottom the same way: find the run, check its state, do the work through the store's repos.
Every operation returns plain typed data; turning that into text is the command line's job.
When an operation cannot go ahead it raises `Refused` with a reason the operator can read.
"""
import os
import pathlib
import shutil
import sys
from dataclasses import dataclass

from factory import agent, config, driver, proc, workflow, workspace
from factory.store import Event, Plan, Run, StepRecord, open_store
from factory.workspace import Workspace


class Refused(Exception):
    """The operation was not carried out; the message says why."""


@dataclass
class RunView:
    """A run with what belongs to it, for showing."""
    run: Run
    plans: list[Plan]
    steps: list[StepRecord]
    events: list[Event]


@dataclass
class Health:
    """One thing the factory needs, and whether it is there."""
    name: str
    ok: bool
    detail: str


def _open():
    store = open_store(config.home())
    reconcile(store)
    return store


def reconcile(store) -> None:
    """Notice a run whose driver has died, and end it. Called at the start of every operation.

    A run is only ever "planning" or "working" while a driver process carries it. If that
    process is gone — killed, crashed, the machine restarted — the run is ended as needs-me,
    "interrupted", and anything the driver left running is stopped.
    """
    run = store.runs.open()
    if (run and run.state in ("planning", "working") and run.driver_pid
            and not proc.is_alive(run.driver_pid, run.driver_started)):
        driver.end_run(store, run.id, "needs-me", "interrupted")


def _find(store, run_id) -> Run:
    """The run with this id, or the most recent run when no id is given."""
    if run_id is None:
        latest = store.runs.latest()
        if latest is None:
            raise Refused("there are no runs yet")
        return latest
    try:
        return store.runs.get(run_id)
    except LookupError:
        raise Refused(f"there is no run {run_id}") from None


def _waiting(store, run_id) -> Run:
    run = _find(store, run_id)
    if run.state != "awaiting_approval":
        described = run.outcome or run.state.replace("_", " ")
        raise Refused(f"run {run.id} is not waiting for a decision; it is {described}")
    return run


def launch(store, run, state, step) -> None:
    """Hand a run to a detached driver process, which carries it on after this command returns."""
    with store.files.driver_log(run.id) as log:
        pid = proc.spawn_detached([sys.executable, "-m", "factory", "_drive", str(run.id)],
                                  cwd=config.PACKAGE_DIR.parent, log=log, env=os.environ.copy())
    # State, step and process are written together, so the run is never "working" with no driver.
    store.runs.set_state(run.id, state, current_step=step, driver_pid=pid,
                         driver_started=proc.started_at(pid))


def get_run(run_id=None) -> Run:
    return _find(_open(), run_id)


def init_target(path) -> pathlib.Path:
    """Create a new target codebase: a git repository with the default settings committed."""
    path = pathlib.Path(path)
    if path.exists() and any(path.iterdir()):
        raise Refused(f"{path} already has content; init-target only creates a new codebase")
    path.mkdir(parents=True, exist_ok=True)
    (path / ".factory.toml").write_text(config.DEFAULT_FACTORY_TOML)
    (path / ".gitignore").write_text(config.DEFAULT_GITIGNORE)
    (path / "README.md").write_text(f"# {path.name}\n\nBuilt by the factory, one request at a time.\n")
    for command in (["init", "-q", "-b", "main"], ["add", "-A"],
                    [*workspace.AUTHOR, "commit", "-q", "-m", "factory: new target codebase"]):
        code, _, err = proc.capture(["git", *command], cwd=path)
        if code != 0:
            raise Refused(f"git {command[0]} failed in {path}: {err.strip()}")
    return path


def request(text, target, attempts=3, launcher=None) -> Run:
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
    open_run = store.runs.open()
    if open_run:    # one run at a time (FR-033)
        raise Refused(f"run {open_run.id} has not ended ({open_run.state.replace('_', ' ')});"
                      " let it finish, or stop or abandon it, before making another request")

    first = workflow.STEPS[0].name
    run = store.runs.create(text.strip(), target, base, ideals=config.read_ideals(),
                            attempt_limit=attempts, current_step=first)
    try:
        Workspace.create(target, run.workspace, run.branch)
        workspace.snapshot(config.factory_paths(), store.files.snapshot_dir(run.id))
    except Exception as problem:
        driver.end_run(store, run.id, "needs-me", f"the run's checkout could not be created: {problem}")
        raise Refused(f"the run's checkout could not be created: {problem}") from None
    (launcher or launch)(store, run, "planning", first)
    return store.runs.get(run.id)


def plan(run_id=None) -> Plan:
    """The current version of a run's plan."""
    store = _open()
    run = _find(store, run_id)
    current = store.plans.current(run.id)
    if current is None:
        raise Refused(f"run {run.id} has no plan yet")
    return current


def approve(run_id=None, launcher=None) -> Run:
    """Approve the waiting plan. The rest of the run needs nothing more from the operator."""
    store = _open()
    run = _waiting(store, run_id)
    store.plans.decide(run.id, store.plans.current(run.id).version, "approved")
    then = workflow.after_wait("approve", workflow.get(run.current_step))
    (launcher or launch)(store, run, "working", then.step)
    return store.runs.get(run.id)


def revise(run_id=None, comment="", launcher=None) -> Run:
    """Send the waiting plan back with a comment. A new version is written in the background."""
    store = _open()
    run = _waiting(store, run_id)
    if not comment.strip():
        raise Refused("say what to change: a plan is sent back with a comment")
    store.plans.decide(run.id, store.plans.current(run.id).version, "revised", comment=comment.strip())
    then = workflow.after_wait("revise", workflow.get(run.current_step))
    (launcher or launch)(store, run, "planning", then.step)
    return store.runs.get(run.id)


def abandon(run_id=None) -> Run:
    """Give up on a request whose plan is waiting. Nothing in the target was changed."""
    store = _open()
    run = _waiting(store, run_id)
    store.plans.decide(run.id, store.plans.current(run.id).version, "abandoned")
    then = workflow.after_wait("abandon", workflow.get(run.current_step))
    Workspace(run.workspace, run.target, run.branch, run.base_commit).remove()
    return driver.end_run(store, run.id, then.outcome, then.reason)



def stop(run_id=None) -> Run:
    """Stop a run that is being worked. Nothing it started is left running; its record is kept."""
    store = _open()
    run = _find(store, run_id)
    if run.state not in ("planning", "working"):
        raise Refused(f"run {run.id} is not running; it is {run.outcome or run.state.replace('_', ' ')}")
    proc.terminate(run.driver_pid, run.driver_started)     # the driver stops its step and ends the run
    proc.stop_group(store.runs.get(run.id).child_pgid)      # in case the driver could not
    return driver.end_run(store, run.id, "needs-me", "stopped by operator")

def status(limit=10) -> list[RunView]:
    """The most recent runs, newest first, each with its steps so far."""
    store = _open()
    return [RunView(run, [], store.steps.list(run.id), []) for run in store.runs.all(limit)]


def show(run_id=None, step=None) -> RunView:
    """A whole run; or, given a step record's id, that one step with everything that happened in it."""
    store = _open()
    run = _find(store, run_id)
    steps = store.steps.list(run.id)
    if step is None:
        return RunView(run, store.plans.list(run.id), steps, [])
    chosen = [record for record in steps if record.id == step]
    if not chosen:
        raise Refused(f"run {run.id} has no step {step}")
    return RunView(run, [], chosen, store.events.for_step(step))


def follow(run_id=None, after=0) -> list[Event]:
    """The events of a run recorded after the one with this id."""
    store = _open()
    return store.events.after(_find(store, run_id).id, after)


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
