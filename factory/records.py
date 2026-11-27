"""Control: record-keeping. The rules about what a run's record must say.

The data layer (store.py) will write anything it is given. These functions are where the
factory's own rules about its records live, each stated once:

  * a run's branch is named from when it was requested and its request, never from its number
  * changing a run's state writes that into its history
  * a run ends exactly once, with its outcome, reason and end time together
  * plans are numbered in order, and a decision is made on the current one
  * every execution of a step is an attempt, numbered within its run
  * a step finishes once

Everything here is done through the gateway's five plain operations.
"""
import datetime

from factory.store import gt, is_null, ne, not_null, now
from factory.workflow import ANSWERERS, DEFECTIVE_TESTS
from factory.workspace import slug

MOVING = ("current_step", "driver_pid", "driver_started", "child_pgid")    # what changes as a run is carried on
NOT_RUNNING = {"driver_pid": None, "driver_started": None, "child_pgid": None}   # no process carries the run


# ---- runs ----

def stamp(moment) -> str:
    """A time as it appears in names shared between machines: 20261119-145203 (FR-081)."""
    return moment[:19].replace("-", "").replace(":", "").replace("T", "-")


def new_run(gw, request, target, base_commit, ideals="", attempt_limit=3, current_step=None, run_kind="change",
            ref=None, queued=False):
    """Start a run's record: planning, on its own branch, with its own checkout path. The branch is named by the
    run's `ref` (FR-160): the one given, else one made from the request's first line. Its record and retro take the
    same name. A `queued` run waits its turn (FR-161): its base commit is set again when it starts."""
    state = "queued" if queued else "planning"
    with gw.transaction():
        run = gw.insert("runs", {
            "request": request, "target": str(target), "base_commit": base_commit, "state": state,
            "current_step": current_step, "ideals": ideals, "attempt_limit": attempt_limit,
            "run_kind": run_kind, "created_at": now()})
        branch = f"factory/{stamp(run.created_at)}-{ref or made_ref(request)}"
        if gw.query("runs", {"branch": branch}):        # the same request twice in one second, on this machine
            branch += f"-{run.id}"
        run = gw.update("runs", {"id": run.id}, {
            "branch": branch,
            "workspace": str(gw.files.workspace_path(run.id))})[0]
        event(gw, run.id, "run_state", state, {"state": state})
    return run


def made_ref(request) -> str:
    """A ref made from the request when none is given (FR-160): its first line, as a slug, so a request that opens
    with a title ("Run 10a, sign-in: ...") names its run by that title. "run" if nothing in it is usable."""
    first = request.strip().splitlines()[0] if request.strip() else ""
    return slug(first, words=6) or "run"


def open_run(gw):
    """The run that has not ended, if there is one. There is never more than one."""
    found = gw.query("runs", [ne("state", "ended"), ne("state", "queued")])
    return found[0] if found else None


def queued(gw) -> list:
    """The requests waiting their turn, first in first (FR-161)."""
    return gw.query("runs", {"state": "queued"}, order="id")


def last_ended(gw):
    """The run that ended most recently, if any."""
    ended = gw.query("runs", {"state": "ended"}, order="-ended_at", limit=1)
    return ended[0] if ended else None


def move(gw, run_id, **fields):
    """Change the fields that move as a run is carried forward. Nothing else may change this way."""
    for name in fields:
        if name not in MOVING:
            raise ValueError(f"{name} is not a field that moves; a run's {name} is fixed once it is recorded")
    return gw.update("runs", {"id": run_id}, fields)[0] if fields else gw.get("runs", run_id)


def set_state(gw, run_id, state, **fields):
    """Set a run's state, and write the change into its history."""
    if state == "ended":
        raise ValueError("a run is ended only through end(), which records its outcome and reason")
    with gw.transaction():
        gw.update("runs", {"id": run_id}, {"state": state})
        run = move(gw, run_id, **fields)
        event(gw, run_id, "run_state", state, {"state": state, "current_step": run.current_step})
    return run


def await_operator(gw, run_id):
    """The run now waits for the operator: no process carries it until they decide."""
    return set_state(gw, run_id, "awaiting_approval", **NOT_RUNNING)


def described(run) -> str:
    """How a run is described in one word or two: its outcome if it has ended, else its state."""
    return run.outcome or run.state.replace("_", " ")


def end(gw, run_id, outcome, reason):
    """End a run: outcome, reason and end time together, exactly once, with nothing left recorded as running."""
    with gw.transaction():
        if gw.get("runs", run_id).state == "ended":
            raise ValueError(f"run {run_id} has already ended")
        run = gw.update("runs", {"id": run_id}, {
            "state": "ended", "outcome": outcome, "reason": reason, "ended_at": now(), **NOT_RUNNING})[0]
        event(gw, run_id, "run_state", f"ended: {outcome}",
              {"state": "ended", "outcome": outcome, "reason": reason})
    return run


def start_queued(gw, run_id, commit):
    """A queued request's turn has come (FR-161): it starts from the codebase as it is now, not as it was when it
    was queued."""
    with gw.transaction():
        run = gw.update("runs", {"id": run_id}, {"base_commit": commit})[0]
        event(gw, run_id, "started_from_queue", f"its turn came; it starts from {commit[:10]}", {"commit": commit})
    return run


def set_aside(gw, run_id):
    """A run that ended needing the operator, abandoned so the queue can go on (FR-161): rejected, its reason kept."""
    with gw.transaction():
        run = gw.get("runs", run_id)
        reason = f"abandoned after it ended needing you: {run.reason}"
        run = gw.update("runs", {"id": run_id}, {"outcome": "rejected", "reason": reason})[0]
        event(gw, run_id, "set_aside", reason, {"outcome": "rejected"})
    return run


def restart_from(gw, run_id, commit):
    """The one way a run's starting commit changes: a plan agreed in a dialogue, approved after the codebase moved,
    is built from the codebase as it is now, nothing having been built on it yet (FR-125)."""
    with gw.transaction():
        run = gw.get("runs", run_id)
        moved = gw.update("runs", {"id": run_id}, {"base_commit": commit})[0]
        event(gw, run_id, "restarted_from", f"the codebase moved: {run.base_commit[:10]} to {commit[:10]}",
              {"from": run.base_commit, "to": commit})
    return moved


def reopen(gw, run_id, state):
    """Take back a run's needs-me ending so it can carry on. The ending it had stays in its history."""
    with gw.transaction():
        run = gw.get("runs", run_id)
        if run.outcome != "needs-me":
            raise ValueError(f"run {run_id} did not end as needs-me, so it cannot be reopened")
        reopened = gw.update("runs", {"id": run_id}, {"state": state, "outcome": None, "reason": None,
                                                       "ended_at": None})[0]
        event(gw, run_id, "run_state", f"resumed at {run.current_step}",
              {"state": state, "resumed_from": {"outcome": run.outcome, "reason": run.reason}})
    return reopened


# ---- plans ----

def current_plan(gw, run_id):
    """The latest version of a run's plan, or None."""
    found = gw.query("plans", {"run_id": run_id}, order="-version", limit=1)
    return found[0] if found else None


def add_plan(gw, run_id, text, ideals_addressed, conflicts):
    """Record a new version of a run's plan, awaiting the operator's decision."""
    with gw.transaction():
        latest = current_plan(gw, run_id)
        return gw.insert("plans", {
            "run_id": run_id, "version": (latest.version if latest else 0) + 1, "text": text,
            "ideals_addressed": ideals_addressed, "conflicts": conflicts, "decision": "pending",
            "created_at": now()})


def decide(gw, run_id, decision, comment=None):
    """Record the operator's decision on the current plan."""
    changes = {"decision": decision} if comment is None else {"decision": decision, "comment": comment}
    return gw.update("plans", {"run_id": run_id, "version": current_plan(gw, run_id).version}, changes)[0]


def set_plan_aside(gw, run_id, reason):
    """The approved plan, when the run goes back to planning from it: marked stale, with why (FR-125)."""
    plan = current_plan(gw, run_id)
    if plan and plan.decision == "approved":
        decide(gw, run_id, "stale", comment=reason)


# ---- steps ----

def attempts(gw, run_id, name) -> int:
    """How many times this step has run in this run. Every execution counts, whatever caused it."""
    return len(gw.query("steps", {"run_id": run_id, "name": name}))


# Why an attempt ended that says nothing about the model's work, so a stronger one would not help (FR-109).
NOT_THE_WORK = ("error", "timeout", "question")


def sent_back_at(gw, run_id) -> str:
    """When the operator last sent the work back: a plan sent back, or a dialogue's batch answered (FR-105, FR-120).
    "" if never."""
    revised = [p.created_at for p in gw.query("plans", {"run_id": run_id}) if p.decision == "revised"]
    answered = [q.answered_at for q in gw.query("questions", [{"run_id": run_id}, not_null("round")]) if q.answered_at]
    return max([*revised, *answered], default="")


def attempts_climbed(gw, run_id, name) -> int:
    """How many grades this step's next attempt climbs (FR-109): its earlier attempts since the operator last sent
    the work back whose work was found wanting, by its own check, its reply's shape, a guard, or a later step
    sending it back. An attempt that ended in an error of the agent program, a timeout or a question is left out:
    a stronger model would not have helped. The attempt now starting is left out too."""
    since = sent_back_at(gw, run_id)
    earlier = [s for s in gw.query("steps", {"run_id": run_id, "name": name}) if s.ended_at and s.started_at >= since]
    return sum(1 for s in earlier if s.failure not in NOT_THE_WORK)


def attempts_counted(gw, run_id, name) -> int:
    """How many of this step's runs count toward its attempt limit: its own failures and successes since the
    operator last sent the work back, leaving out a run that asked a question the operator or the orchestrator
    answered (FR-105, FR-140). A question the lead answered still counts, so a step that only ever asks still ends."""
    since = sent_back_at(gw, run_id)
    answered_from_outside = [q for q in gw.query("questions", {"run_id": run_id, "step": name})
                             if q.answered_by in ANSWERERS]
    counted = 0
    for step in gw.query("steps", {"run_id": run_id, "name": name}):
        if step.started_at < since:
            continue                                        # before the operator's latest send-back
        asked_and_answered = step.failure == "question" and any(
            q.asked_at >= step.started_at and (step.ended_at is None or q.asked_at <= step.ended_at)
            for q in answered_from_outside)
        if not asked_and_answered:
            counted += 1
    return counted


def defect_reports(gw, run_id) -> list[tuple]:
    """The tests each report of a defective test in this run named, oldest first, since the operator last sent the
    work back (FR-150): a reply that names them under `defective_tests` and whose verdict sent the run on its route.
    A reply that failed for its shape or a guard was not acted on, so it is not a report."""
    since = sent_back_at(gw, run_id)
    return [tuple(map(str, s.produced[DEFECTIVE_TESTS] or ())) for s in gw.query("steps", {"run_id": run_id})
            if s.started_at >= since and s.failure == "check" and isinstance(s.produced, dict)
            and DEFECTIVE_TESTS in s.produced]


def so_far(gw, run_id) -> tuple[float, list[str]]:
    """What a run's steps have cost so far, by the agent program's own estimates, and the steps that passed (FR-117)."""
    steps = gw.query("steps", {"run_id": run_id})
    return sum(s.cost_estimate or 0 for s in steps), [s.name for s in steps if s.passed]


def minutes(started, ended) -> float:
    """The minutes between two of the store's times."""
    def at(text):
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    return (at(ended) - at(started)).total_seconds() / 60


def took(gw, run_id) -> tuple[float, float]:
    """The minutes a run's steps took and what they cost, as the factory measured them (FR-092, FR-123)."""
    steps = [s for s in gw.query("steps", {"run_id": run_id}) if s.ended_at]
    return sum(minutes(s.started_at, s.ended_at) for s in steps), sum(s.cost_estimate or 0 for s in steps)


def found(gw, run_id) -> dict:
    """What a spike's findings said (FR-116): the latest passed reply that gives an outcome, or nothing."""
    said = [s.produced for s in gw.query("steps", {"run_id": run_id})
            if s.passed and isinstance(s.produced, dict) and "outcome" in s.produced]
    return said[-1] if said else {}


def start_step(gw, run_id, name, kind, persona, asked):
    """Put a step on record as it begins, so a run in progress shows what it is doing."""
    with gw.transaction():
        return gw.insert("steps", {
            "run_id": run_id, "name": name, "kind": kind, "persona": persona, "asked": asked,
            "attempt": attempts(gw, run_id, name) + 1, "started_at": now()})


def finish_step(gw, step_id, produced, checks, passed, failure=None, tokens=None, cost_estimate=None):
    """Complete a step's record, once."""
    if gw.get("steps", step_id).ended_at is not None:
        raise ValueError(f"step {step_id} has already finished")
    return gw.update("steps", {"id": step_id}, {
        "produced": produced, "checks": checks, "passed": bool(passed), "failure": failure,
        "tokens": tokens, "cost_estimate": cost_estimate, "ended_at": now()})[0]


# ---- events ----

def event(gw, run_id, kind, summary, payload=None, step_id=None):
    """Record one thing that happened, as it happens."""
    return gw.insert("events", {"run_id": run_id, "step_id": step_id, "at": now(), "kind": kind,
                                "summary": summary, "payload": payload or {}})


def events_after(gw, run_id, last_seen=0, limit=500):
    """The one query for following a run: live view and history are the same query."""
    return gw.query("events", [{"run_id": run_id}, gt("id", last_seen)], limit=limit)


# ---- questions ----

def ask(gw, run_id, step, asked_by, question, round=None, measure=False):
    """Put a question on record as it is asked: in a dialogue, with its round, and whether it asks for a measurement."""
    with gw.transaction():
        asked = gw.insert("questions", {"run_id": run_id, "step": step, "asked_by": asked_by, "question": question,
                                        "asked_at": now(), "round": round, "measure": measure})
        event(gw, run_id, "question", f"{asked_by} asks: {question}", {"question_id": asked.id, "step": step})
    return asked


def pending_question(gw, run_id):
    """The question still waiting for an answer, if there is one."""
    waiting = gw.query("questions", [{"run_id": run_id}, is_null("answer")])
    return waiting[-1] if waiting else None


def answer(gw, question_id, text, answered_by):
    """Record the answer to a question, and who gave it."""
    with gw.transaction():
        answered = gw.update("questions", {"id": question_id},
                             {"answer": text, "answered_by": answered_by, "answered_at": now()})[0]
        event(gw, answered.run_id, "answer", f"{answered_by} answers: {text}", {"question_id": question_id})
    return answered
