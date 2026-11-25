"""Control: operations. What the operator can do to a run, and when it is refused.

The Run is the resource. Each function below is one operation on it and reads top to
bottom the same way: find the run, check its state, do the work through the store's repos.
Every operation returns plain data — rows as mappings; turning that into text is the command line's job.
When an operation cannot go ahead it raises `Refused` with a reason the operator can read.
"""
import os
import pathlib
import shlex
import shutil
import sys
from dataclasses import dataclass, field

from factory import (agent, config, dialogue, driver, own_files, proc, records, run_record, sandbox, speckit, tables,
                     workflow, workspace)
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
    waiting: dict | None = None                        # what a dialogue waiting for the asker waits for (FR-128)


@dataclass
class Batch:
    """A dialogue's questions waiting for the asker, and the text the asker writes the answers into (FR-121)."""
    run: dict
    questions: list
    text: str


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
        raise Refused(f"run {run.id} is not waiting for a decision; it is {records.described(run)}")
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


def _launch_at(store, run, step) -> dict:
    """Hand the run to a driver at this step, in the state the step implies."""
    state = "planning" if workflow.is_planning(step, driver.table_of(run)) else "working"
    launch(store, run, state, step)
    return store.get("runs", run.id)


def run_kinds() -> list[str]:
    """The kinds of run a request can be."""
    return list(tables.RUN_KINDS)


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


def resolved_table(target, commit, run_kind="change") -> list:
    """The steps a run of `run_kind` on `target` at `commit` would go through, with the project's overrides
    (FR-112), checked as a run checks its table. Refused, saying why, if they are not sound."""
    try:
        settings = config.read_target_config(target, commit)
        table = tables.table_for(speckit.available_at(target, commit), run_kind, settings.cycle)
        table = tables.overridden(table, settings.steps)
        driver.validate(table)
    except (config.ConfigError, ValueError) as problem:
        raise Refused(str(problem)) from None
    return table


def table(target, run_kind="change") -> list:
    """The table a run on `target` would use now (`factory table`)."""
    target = pathlib.Path(target).resolve()
    try:
        commit = workspace.head_of(target)
    except workspace.WorkspaceError as problem:
        raise Refused(str(problem)) from None
    return resolved_table(target, commit, run_kind)


def request(text, target, attempts=3, run_kind="change") -> dict:
    """Hand the factory a request. A plan is written in the background; then the run waits."""
    store = _open()
    if not text.strip():
        raise Refused("the request is empty; say what you want changed")
    if attempts < 1:
        raise Refused("the attempt limit must be at least 1")
    target = pathlib.Path(target).resolve()
    try:
        base = workspace.head_of(target)
        settings = config.read_target_config(target, base)
    except (workspace.WorkspaceError, config.ConfigError) as problem:
        raise Refused(str(problem)) from None
    open_run = records.open_run(store)
    if open_run:    # one run at a time (FR-033)
        raise Refused(f"run {open_run.id} has not ended ({records.described(open_run)});"
                      " let it finish, or stop or abandon it, before making another request")
    if run_kind not in tables.RUN_KINDS:
        raise Refused(f"a run is one of: {', '.join(tables.RUN_KINDS)}; not {run_kind!r}")
    if run_kind == tables.SPIKE:
        _can_spike(settings)
    resolved_table(target, base, run_kind)          # a project's overrides are checked before anything is paid for

    run = records.new_run(store, text.strip(), target, base, ideals=config.ideals_for(target, base),
                          attempt_limit=attempts, run_kind=run_kind)
    try:
        Workspace.create(target, run.workspace, run.branch, base)
        own_files.snapshot(config.factory_paths(), store.files.snapshot_dir(run.id))
    except Exception as problem:
        driver.end_run(store, run.id, "needs-me", f"the run's checkout could not be created: {problem}")
        raise Refused(f"the run's checkout could not be created: {problem}") from None
    return _launch_at(store, run, driver.table_of(run)[0].name)    # the table of its own checkout


def _can_spike(settings) -> None:
    """A spike is refused, naming the setting, on a codebase that could not run its probe or keep its findings
    (FR-113)."""
    if not settings.probe_command:
        raise Refused("a spike's probe is run by the codebase's `probe_command`, which its committed .factory.toml"
                      " does not set; add one, with {path} where the probe's file goes")
    if "{path}" not in settings.probe_command:
        raise Refused(f"this codebase's `probe_command` ({settings.probe_command}) has no {{path}}, so the probe's"
                      " file could not be given to it")
    if not config.under("docs/spikes/", settings.docs_paths):
        raise Refused("a spike's findings are written to docs/spikes/, which is not in this codebase's `docs_paths`"
                      f" ({', '.join(settings.docs_paths)})")


def plan(run_id=None) -> dict:
    """The current version of a run's plan. A dialogue's plan that was replied to, or found stale, is not shown as
    the current one, nor is there one while the agents' questions wait (FR-128)."""
    store = _open()
    run = _find(store, run_id)
    current = records.current_plan(store, run.id)
    why = dialogue.not_current(store, run)
    if why:
        raise Refused(why)
    if current is None:
        raise Refused(f"run {run.id} has no plan yet")
    return current


def waiting(run_id=None) -> dict | None:
    """What a dialogue run waits for: answers, agreement or approval; None if it is not waiting on its dialogue."""
    store = _open()
    return dialogue.waiting(store, _find(store, run_id))


def _carry_on(store, run, decision, moved=False) -> dict:
    """After a decision at a wait: launch a driver at whatever step that decision leads to."""
    then = workflow.after_wait(decision, workflow.get(run.current_step, driver.table_of(run)), moved=moved)
    return _launch_at(store, run, then.step)


def approve(run_id=None) -> dict:
    """Approve what is waiting. The run carries on to its next wait, or to its end, unattended. A dialogue's plan is
    approved only once agreed; approved after the codebase moved, it is re-checked against it first (FR-122, FR-125)."""
    store = _open()
    run = _waiting(store, run_id)
    step = workflow.get(run.current_step, driver.table_of(run))
    moved = False
    if step.dialogue:
        current = records.current_plan(store, run.id)
        if not current or current.decision != "agreed":
            raise Refused(f"run {run.id}'s plan is not agreed, and agreement is not approval: read it with"
                          " factory plan, agree with factory agree, then approve")
        moved = _restart_if_moved(store, run, step)
        run = store.get("runs", run.id)
    records.decide(store, run.id, "approved")
    checkout = Workspace.of(run)
    if not step.speckit:     # spec kit commits its own documents
        run_record.write(store, run, checkout, run_record.approved_message(store, run))
    records.event(store, run.id, "approved", f"approved at {run.current_step}", {"commit": checkout.head()})
    return _carry_on(store, run, "approve", moved)


def _restart_if_moved(store, run, step) -> bool:
    """Where the codebase has moved since the dialogue read it, start the run's checkout again from its head, so the
    plan is re-checked against it and built on it (FR-125). Refused if anything was built, or the new head's
    settings would give a run of this kind another table."""
    head = workspace.head_of(run.target)
    if head == run.base_commit:
        return False
    checkout = Workspace.of(run)
    built = set(checkout.files_changed_since_base()) - {run_record.name(run)}
    names = {entry.name for entry in resolved_table(run.target, head, run.run_kind)}
    if built or not {step.name, step.on_moved} <= names:
        raise Refused(f"the codebase has moved since run {run.id}'s dialogue read it, and the run cannot start again"
                      " from its head" + (f": {', '.join(sorted(built))} were built" if built else
                                          ": its settings there give this kind of run another table")
                      + "; abandon it and request again")
    checkout.move_to(head)
    records.restart_from(store, run.id, head)
    return True


def agree(run_id=None) -> dict:
    """Agree to the plan the agents proposed aligned. Agreement is not approval: the run waits for that (FR-122)."""
    store = _open()
    run = _waiting(store, run_id)
    current = records.current_plan(store, run.id)
    drafted = dialogue.latest_draft(store, run.id)
    if dialogue.paused(store, run.id) and drafted and not (current and current.decision == "pending"):
        current = records.add_plan(store, run.id, dialogue.proposal(store, run, drafted),     # the draft (FR-124)
                                   drafted.get("ideals_addressed") or [], drafted.get("conflicts") or [])
    if not dialogue.rounds(store, run.id) or not current or current.decision != "pending":
        raise Refused(f"run {run.id} has no plan proposed for agreement"
                      + (f"; plan version {current.version} is {current.decision}" if current else ""))
    records.decide(store, run.id, "agreed")
    records.event(store, run.id, "agreed", f"plan version {current.version} agreed", {"version": current.version})
    return store.get("runs", run.id)


def revise(run_id=None, comment="") -> dict:
    """Send what is waiting back with a comment. Its stage is done again, in the background."""
    store = _open()
    run = _waiting(store, run_id)
    if not comment.strip():
        raise Refused("say what to change: a plan is sent back with a comment")
    if records.current_plan(store, run.id) is None:
        raise Refused(f"run {run.id} has no plan to send back; it is waiting for {dialogue.waiting(store, run)['says']}"
                      if dialogue.waiting(store, run) else f"run {run.id} has no plan to send back")
    records.decide(store, run.id, "revised", comment=comment.strip())
    return _carry_on(store, run, "revise")


def abandon(run_id=None) -> dict:
    """Give up on a request whose plan is waiting. Nothing in the target was changed."""
    store = _open()
    run = _waiting(store, run_id, with_question=True)
    if records.current_plan(store, run.id):
        records.decide(store, run.id, "abandoned")
    steps = driver.table_of(run)
    then = workflow.after_wait("abandon", workflow.get(run.current_step, steps), steps)
    Workspace.of(run).remove()
    return driver.end_run(store, run.id, then.outcome, then.reason)

def stop(run_id=None) -> dict:
    """Stop a run that is being worked. Nothing it started is left running; its record is kept."""
    store = _open()
    run = _find(store, run_id)
    if run.state not in ("planning", "working"):
        raise Refused(f"run {run.id} is not running; it is {records.described(run)}")
    proc.terminate(run.driver_pid, run.driver_started)     # the driver stops its step and ends the run
    proc.stop_group(store.get("runs", run.id).child_pgid)      # in case the driver could not
    return driver.end_run(store, run.id, "needs-me", "stopped by operator")


def resume(run_id=None) -> dict:
    """Carry on a run that stopped as needs-me, from the step it stopped at. Earlier work is kept."""
    store = _open()
    run = _find(store, run_id)
    if run.outcome != "needs-me":
        raise Refused(f"run {run.id} cannot be resumed: only a run that ended as needs-me can be, "
                      f"and it is {records.described(run)}")
    if not pathlib.Path(run.workspace).is_dir():
        raise Refused(f"run {run.id}'s checkout no longer exists, so there is nothing to carry on from")
    other = records.open_run(store)
    if other:
        raise Refused(f"run {other.id} has not ended; let it finish, or stop or abandon it, before resuming another")
    steps = driver.table_of(run)
    stopped_at = next(entry for entry in steps if entry.name == run.current_step)
    if stopped_at.kind == "agent":
        Workspace.of(run).undo()        # whatever the stopped agent left half-done
    # A code step writes nothing of its own: what is uncommitted when one stops is the work it was
    # checking (the build's, when the tests failed), and the step that carries on checks it again.
    own_files.snapshot(config.factory_paths(), store.files.snapshot_dir(run.id))   # the factory as it is now
    state = "planning" if workflow.is_planning(run.current_step, steps) else "working"
    reopened = records.reopen(store, run.id, state)
    run_record.write(store, reopened, Workspace.of(reopened), run_record.resumed_message(reopened))    # FR-094
    return _launch_at(store, reopened, run.current_step)


def answer(run_id=None, text="", by="operator") -> dict:
    """Answer what a run is waiting on. A dialogue's batch is answered as one (FR-121): `text` is the batch with each
    answer under its question, or plain words where one question waits; the next round then begins. Any other
    question: the step that asked runs again with the answer. `by` is who answered: the operator, or the
    orchestrator driving the factory for him; in a batch, one answer may say otherwise (FR-139)."""
    if by not in workflow.ANSWERERS:
        raise Refused(f"{by} cannot answer here: an answer given here is the operator's or the orchestrator's")
    store = _open()
    run = _find(store, run_id)
    waiting = dialogue.batch(store, run.id)
    if waiting:
        return _answer_batch(store, run, waiting, text, by)
    asked = records.pending_question(store, run.id)
    if asked is None and dialogue.paused(store, run.id):
        return _resume_paused(store, run, text, by)
    if asked is None:
        now = dialogue.waiting(store, run)
        raise Refused(f"run {run.id} has no questions waiting for an answer"
                      + (f"; it is waiting for {now['says']}: {now['next']}" if now else ""))
    if not text.strip():
        raise Refused(f"give an answer to: {asked.question}")
    records.answer(store, asked.id, text.strip(), by)
    return _launch_at(store, run, run.current_step)


def _answer_batch(store, run, waiting, text, by) -> dict:
    if any(dialogue.MARK.match(line) for line in text.splitlines()):
        try:
            answers = dialogue.parse_batch(text, waiting, by)
        except ValueError as problem:
            raise Refused(str(problem)) from None
    elif len(waiting) == 1 and text.strip():
        answers = {waiting[0].id: dialogue.Answer(text.strip(), by)}
    else:
        raise Refused(f"{len(waiting)} questions are waiting: answer them with factory answer, which opens them in"
                      " your editor, or with factory answer --file, from the batch factory questions shows")
    budget = [q for q in waiting if q.step == dialogue.BUDGET]
    more = [workflow.spend_more(answers[q.id].text) for q in budget]
    if None in more:
        raise Refused("the budget question takes yes or no: whether to spend more on the dialogue")
    merged = dialogue.merged_into(store, run.id)
    with store.transaction():
        for q in waiting:
            records.answer(store, q.id, answers[q.id].text, answers[q.id].by)
        for duplicate, kept in merged.items():       # the same answer, by the same answerer, to each that asked it
            if kept in answers and store.get("questions", duplicate).answer is None:      # (FR-132, FR-139)
                records.answer(store, duplicate, answers[kept].text, answers[kept].by)
        records.event(store, run.id, "answered", f"round {waiting[0].round}: {len(waiting)} answered",
                      {"round": waiting[0].round})
        if False in more:      # paused at its budget: the run waits, everything kept, to go on later (FR-124)
            records.event(store, run.id, "paused", f"paused at its budget, after round {waiting[0].round}",
                          {"round": waiting[0].round})
    if False in more:
        run_record.write(store, run, Workspace.of(run), run_record.paused_message(store, run))
        return store.get("runs", run.id)
    return _carry_on(store, run, "revise")


def note(run_id=None, text="", by="the operator") -> dict:
    """Add a ruling or a fact to a run while it plans in a dialogue (FR-133). Every speaker is given it, with who
    added it and when, from its next round on; it is in the dialogue's transcript, and so in the run's record."""
    store = _open()
    run = _find(store, run_id)
    if not text.strip():
        raise Refused("say what the note is: a ruling or a fact for the dialogue's agents")
    if run.state == "ended":
        raise Refused(f"run {run.id} has ended; a note reaches only a run that is planning")
    steps = driver.table_of(run)
    if not steps[0].dialogue or not workflow.is_planning(run.current_step, steps):
        raise Refused(f"run {run.id} is not planning in a dialogue, so no agent would read a note;"
                      " a run planned without one is sent back with factory revise")
    records.event(store, run.id, "note", f"note from {by}: {text.strip()}", {"text": text.strip(), "by": by})
    return store.get("runs", run.id)


def _resume_paused(store, run, text, by) -> dict:
    """A dialogue paused at its budget goes on when the asker says yes: the next round, with a fresh allowance."""
    if workflow.spend_more(text) is not True:
        raise Refused(f"run {run.id}'s dialogue is paused at its budget: answer yes to spend more, agree to its"
                      " draft plan with factory agree, or abandon it")
    number = dialogue.rounds(store, run.id)[-1].payload["round"]
    with store.transaction():
        asked = records.ask(store, run.id, dialogue.BUDGET, "factory", "Spend more, after the pause at the budget?"
                            " yes / no", number)
        records.answer(store, asked.id, "yes", by)
        records.event(store, run.id, "answered", f"round {number}: spend more, after the pause", {"round": number})
    return _carry_on(store, run, "revise")


def questions(run_id=None) -> Batch:
    """The dialogue's questions waiting for the asker, as the text the answers are written into (FR-121)."""
    store = _open()
    run = _find(store, run_id)
    waiting = dialogue.batch(store, run.id)
    if not waiting and dialogue.paused(store, run.id):       # what it has so far, kept (FR-124)
        return Batch(run, [], dialogue.so_far(store, run))
    if not waiting:
        raise Refused(f"run {run.id} has no questions waiting for the asker")
    return Batch(run, waiting, dialogue.render_batch(run, waiting))


def answer_in_editor(run_id=None, by="operator") -> dict:
    """Open the waiting batch in the asker's editor, each question with a place for its answer; saving sends them
    all at once (FR-121). Answers refused are kept in the draft, which opens again next time."""
    store = _open()
    if not dialogue.batch(store, _find(store, run_id).id):
        return answer(run_id, "", by)               # refused, saying what is waiting instead
    batch = questions(run_id)
    draft = store.files.answers_draft(batch.run.id)
    asked = {f"[Q{q.id}]" for q in batch.questions}
    if not draft.exists() or {line.split(" ")[0] for line in draft.read_text().splitlines()
                              if dialogue.MARK.match(line)} != asked:
        draft.write_text(batch.text)
    if proc.interactive([*shlex.split(os.environ.get("EDITOR") or "nano"), str(draft)]) != 0:
        raise Refused(f"the editor did not finish; your answers are kept in {draft}")
    try:
        run = answer(batch.run.id, draft.read_text(), by)
    except Refused as problem:
        raise Refused(f"{problem}; your answers are kept in {draft}, and open again with factory answer") from None
    draft.unlink()
    return run


def is_dialogue(run) -> bool:
    """Does this run plan in a dialogue (FR-119)?"""
    return driver.table_of(run)[0].dialogue


def status(limit=10) -> list[RunView]:
    """The most recent runs, newest first, each with its steps so far."""
    store = _open()
    return [RunView(run, [], store.query("steps", {"run_id": run.id}), [],
                    store.query("questions", {"run_id": run.id}), dialogue.waiting(store, run))
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
    contained, reason = sandbox.available()
    found.append(Health("containment", contained, reason))
    return found


def drive(run_id) -> None:
    """What a detached driver process runs. Not something the operator calls."""
    driver.drive(open_store(config.home()), run_id)
