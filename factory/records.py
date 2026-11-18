"""Control: record-keeping. The rules about what a run's record must say.

The data layer (store.py) will write anything it is given. These functions are where the
factory's own rules about its records live, each stated once:

  * a run's branch is named from its number and its request
  * changing a run's state writes that into its history
  * a run ends exactly once, with its outcome, reason and end time together
  * plans are numbered in order, and a decision is made on the current one
  * every execution of a step is an attempt, numbered within its run
  * a step finishes once

Everything here is done through the gateway's five plain operations.
"""
import re

from factory.store import gt, is_null, ne, now

MOVING = ("current_step", "driver_pid", "driver_started", "child_pgid")    # what changes as a run is carried on


def slug(request) -> str:
    """The readable part of a run's branch name: its first five words, made safe."""
    words = " ".join(request.split()[:5]).lower()
    return re.sub(r"[^a-z0-9]+", "-", words).strip("-")[:40].strip("-") or "run"


# ---- runs ----

def new_run(gw, request, target, base_commit, ideals="", attempt_limit=3, current_step=None):
    """Start a run's record: planning, on its own branch, with its own checkout path."""
    with gw.transaction():
        run = gw.insert("runs", {
            "request": request, "target": str(target), "base_commit": base_commit, "state": "planning",
            "current_step": current_step, "ideals": ideals, "attempt_limit": attempt_limit, "created_at": now()})
        run = gw.update("runs", {"id": run.id}, {
            "branch": f"factory/{run.id}-{slug(request)}",
            "workspace": str(gw.files.workspace_path(run.id))})[0]
        event(gw, run.id, "run_state", "planning", {"state": "planning"})
    return run


def open_run(gw):
    """The run that has not ended, if there is one. There is never more than one."""
    found = gw.query("runs", [ne("state", "ended")])
    return found[0] if found else None


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


def end(gw, run_id, outcome, reason):
    """End a run: outcome, reason and end time together, exactly once, with nothing left recorded as running."""
    with gw.transaction():
        if gw.get("runs", run_id).state == "ended":
            raise ValueError(f"run {run_id} has already ended")
        run = gw.update("runs", {"id": run_id}, {
            "state": "ended", "outcome": outcome, "reason": reason, "ended_at": now(),
            "driver_pid": None, "driver_started": None, "child_pgid": None})[0]
        event(gw, run_id, "run_state", f"ended: {outcome}",
              {"state": "ended", "outcome": outcome, "reason": reason})
    return run


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


# ---- steps ----

def attempts(gw, run_id, name) -> int:
    """How many times this step has run in this run. Every execution counts, whatever caused it."""
    return len(gw.query("steps", {"run_id": run_id, "name": name}))


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

def ask(gw, run_id, step, asked_by, question):
    """Put a question on record as it is asked."""
    with gw.transaction():
        asked = gw.insert("questions", {"run_id": run_id, "step": step, "asked_by": asked_by,
                                        "question": question, "asked_at": now()})
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
