"""Control: execution. Carries one run forward, a step at a time, until it must wait or has ended.

The driver is general. It names no step and no persona: it runs whatever step the run is
on, in the way that step's entry in the workflow table says, and asks `workflow.next_step`
what to do with the result. What each step is, and what follows it, live in workflow.py.

For each step it does eight things, in order:

  1. takes a fingerprint of the factory's own files, and notes what git reports
  2. starts a step record, so the step is visible while it runs
  3. for an agent step: loads the persona and the prompt, fills in the inputs, calls the adapter
  4. runs the checks: the always-applied ones first, then the step's own
  5. if a guard check failed, undoes the change
  6. if the step passed and its entry says so, commits
  7. completes the step record
  8. asks next_step: carry on, wait for the operator, or end
"""
import json
import os
import pathlib
import re
import signal
import time
from dataclasses import asdict

from factory import agent, checks, config, notify, proc, records, speckit, workflow, workspace
from factory.workflow import End, StepResult, Wait
from factory.workspace import Workspace

NO_IDEALS = "No ideals have been stated."


class Stopped(BaseException):
    """Raised inside the driver when it is told to stop."""


def advance(store, run_id, adapter=None, steps=None, personas_dir=None, prompts_dir=None) -> None:
    """Carry a run forward from its current step until it waits or ends."""
    adapter = adapter or agent.get_adapter()
    steps = steps or workflow.STEPS
    personas_dir = pathlib.Path(personas_dir or config.PERSONAS_DIR)
    prompts_dir = pathlib.Path(prompts_dir or config.PROMPTS_DIR)
    run = store.get("runs", run_id)
    checkout = Workspace(run.workspace, run.target, run.branch, run.base_commit)
    settings = config.read_target_config(run.target, run.base_commit)
    try:
        while True:
            run = store.get("runs", run_id)
            if run.state == "ended":        # ended from outside while we were working
                return
            step = workflow.get(run.current_step, steps)
            result, envelope = run_step(store, run, step, checkout, settings, adapter, personas_dir, prompts_dir)
            attempts = {entry.name: records.attempts(store, run_id, entry.name) for entry in steps}
            then = workflow.next_step(step, result, attempts, run.attempt_limit)
            if isinstance(then, End):
                end_run(store, run_id, then.outcome, then.reason)
                return
            if isinstance(then, Wait):
                wait_for_operator(store, run, step, envelope or {})
                return
            records.move(store, run_id, current_step=then.step)
    except Stopped:
        end_run(store, run_id, "needs-me", "stopped by operator")
    except Exception as problem:            # a bug in the factory itself: record it, then let it show
        records.event(store, run_id, "error", f"{type(problem).__name__}: {problem}")
        end_run(store, run_id, "needs-me", f"the factory itself failed: {type(problem).__name__}: {problem}")
        raise


def run_step(store, run, step, checkout, settings, adapter, personas_dir, prompts_dir):
    """Run one step once. Returns (how it went, the agent's envelope if there was one)."""
    paths = config.factory_paths()
    before, dirty_before = workspace.fingerprint(paths), checkout.dirty()               # 1
    timeout = step.timeout or settings.step_timeout_seconds
    asked = ""
    if step.kind == "agent":
        kit = None      # where the target uses spec kit, run its scripts for the agent, who has no shell
        if step.speckit and speckit.available(checkout.path):
            kit = speckit.prepare(step.speckit, checkout, run.request)
        given = {"speckit_instructions": kit["instructions"] if kit else "",
                 "speckit_context": json.dumps(kit["context"], indent=2) if kit else ""}
        inputs = {name: given[name] if name in given else gather(name, store, run, checkout, settings)
                  for name in step.inputs}
        asked = fill((prompts_dir / f"{step.name}.md").read_text(), inputs)
    record = records.start_step(store, run.id, step.name, step.kind, step.persona, asked)       # 2

    def emit(kind, summary, payload=None):
        records.event(store, run.id, kind, summary, payload, step_id=record.id)

    def on_child(group):
        records.move(store, run.id, child_pgid=group)

    emit("step_start", step.name, {"attempt": record.attempt, "persona": step.persona})
    result, reply = StepResult(passed=True), None
    with store.files.stderr_file(run.id, record.id) as errors:
        if step.kind == "agent":                                                         # 3
            reply = adapter(
                persona=(personas_dir / f"{step.persona}.md").read_text(), prompt=asked,
                cwd=checkout.path, capabilities=step.capabilities, timeout=timeout, on_event=emit,
                raw_sink=store.files.raw_sink(run.id, record.id), stderr_file=errors,
                on_child=on_child, model=step.model)
            for denial in reply.denials:
                emit("denied", f"{denial.get('action')}: {denial.get('path')}", denial)
            blocked = [d["path"] for d in reply.denials
                       if pathlib.Path(d.get("path") or "/").is_relative_to(checkout.path)]
            if reply.timed_out:
                result = StepResult(False, "timeout", message=f"{timeout:g} seconds")
            elif not reply.ok:
                result = StepResult(False, "error", message=reply.error or "no message")
            elif blocked:       # trying again cannot help: the program will refuse again
                result = StepResult(False, "error", message="it refused to let the agent work inside the"
                                    f" run's own checkout: {', '.join(blocked)}")

        context = checks.CheckContext(
            run=run, step=step, checkout=checkout, target_config=settings,
            changed=workspace.changed(dirty_before, checkout.dirty()),
            envelope=reply.envelope if reply else None, before=before, factory_paths=paths,
            stderr_file=errors, on_child=on_child, timeout=timeout)
        done = []

        def check(name):
            outcome = checks.get(name)(context)
            done.append(outcome)
            emit("check", f"{name}: {'passed' if outcome.passed else 'failed'}", asdict(outcome))
            return outcome

        guards = [check(name) for name in checks.ALWAYS]                                 # 4
        for outcome in guards:
            if not outcome.passed:                                                       # 5
                if outcome.name == "changes_allowed":
                    checkout.undo()
                else:       # keep the changed versions, in case it was the operator who changed them
                    kept = store.files.displaced_dir(run.id)
                    workspace.snapshot(paths, kept)
                    workspace.restore(paths, store.files.snapshot_dir(run.id))
                    outcome.note += f"; they were put back, and the changed versions are kept in {kept}"
                emit("guard", f"undone: {outcome.note}", {"check": outcome.name, "files": sorted(context.changed)})
                if result.passed:
                    result = StepResult(False, "guard", outcome)
        if result.passed:
            own = (["envelope_valid"] if step.kind == "agent" else []) + list(step.checks)
            for name in own:
                outcome = check(name)
                if not outcome.passed:
                    if outcome.timed_out:
                        result = StepResult(False, "timeout", outcome, message=f"{timeout:g} seconds")
                    else:
                        result = StepResult(False, "malformed" if name == "envelope_valid" else "check", outcome)
                    break

    if step.advisory and result.failure not in (None, "guard"):
        checkout.discard(context.changed)   # a failed advisory step leaves nothing behind for the next to commit

    if result.passed and step.commit_after:                                              # 6
        commit = checkout.commit(f"factory: {step.name} (run {run.id})")
        if commit:
            emit("commit", f"{step.name}: {commit[:10]}", {"commit": commit})

    if reply is not None:
        produced = reply.envelope if reply.envelope is not None else {"text": reply.text[:2000]}
    else:
        produced = {"output": done[-1].note} if step.checks and done else {}
    records.finish_step(store, record.id, produced, [asdict(outcome) for outcome in done], result.passed,   # 7
                       result.failure, reply.tokens if reply else None,
                       reply.cost_estimate if reply else None)
    emit("step_end", f"{step.name}: {'passed' if result.passed else result.failure}",
         {"passed": result.passed, "failure": result.failure})
    return result, reply.envelope if reply else None


def gather(name, store, run, checkout, settings) -> str:
    """The text for one named input of a prompt. See contracts/workflow.md, "Inputs and prompts"."""
    plans = store.query("plans", {"run_id": run.id})
    finished = [record for record in store.query("steps", {"run_id": run.id}) if record.ended_at]
    if name == "request":       # the request as the operator has amended it when sending plans back
        comments = [plan.comment for plan in plans if plan.decision == "revised" and plan.comment]
        if not comments:
            return run.request
        return (run.request + "\n\nThe operator added, when sending an earlier plan back:\n"
                + "\n".join(f"- {comment}" for comment in comments))
    if name == "ideals":
        return run.ideals or NO_IDEALS
    if name == "plan":
        approved = [plan for plan in plans if plan.decision == "approved"]
        return (approved or plans)[-1].text if plans else ""
    if name in ("previous_plan", "comment"):
        if not plans or plans[-1].decision != "revised":
            return ""
        return plans[-1].text if name == "previous_plan" else (plans[-1].comment or "")
    if name == "test_paths":
        return ", ".join(settings.test_paths)
    if name == "docs_paths":
        return ", ".join(settings.docs_paths)
    if name == "test_files":
        touched = set(checkout.files_changed_since_base()) | set(checkout.dirty())
        return "\n".join(sorted(f for f in touched if checks.under(f, settings.test_paths)))
    if name == "failure":
        if not finished or finished[-1].passed:
            return ""
        failed = next((c for c in finished[-1].checks or [] if not c["passed"]), None)
        return f"{failed['name']}: {failed['note']}" if failed else str(finished[-1].failure)
    if name == "diff":
        return checkout.diff_since_base()
    if name == "test_output":
        outputs = [r.produced["output"] for r in finished if r.kind == "code" and (r.produced or {}).get("output")]
        return outputs[-1] if outputs else ""
    raise LookupError(f"there is no input named {name}")


def fill(prompt_text, inputs) -> str:
    """Replace each {{name}} in a prompt with its input; "(none)" where there is nothing to give."""
    def replace(match):
        name = match.group(1)
        if name not in inputs:
            raise LookupError(f"the prompt uses {{{{{name}}}}}, which this step's entry does not list as an input")
        return inputs[name].strip() or "(none)"
    return re.sub(r"\{\{(\w+)\}\}", replace, prompt_text)


def wait_for_operator(store, run, step, envelope) -> None:
    """Store what the operator must decide on, mark the run as waiting, and say so."""
    records.add_plan(store, run.id, envelope.get("plan") or json.dumps(envelope),
                    envelope.get("ideals_addressed") or [], envelope.get("conflicts") or [])
    records.set_state(store, run.id, "awaiting_approval", driver_pid=None, driver_started=None, child_pgid=None)
    tell(store, run.id, f"Run {run.id}: {step.name} ready — waiting for you", " ".join(run.request.split()[:12]))


def end_run(store, run_id, outcome, reason):
    """The one way a run ends: outcome and reason set, nothing left running, the operator told."""
    run = store.get("runs", run_id)
    if run.state == "ended":
        return run
    proc.stop_group(run.child_pgid)
    ended = records.end(store, run_id, outcome, reason)
    tell(store, run_id, f"Run {run_id}: {outcome}", reason)
    return ended


def tell(store, run_id, title, body) -> None:
    sent = notify.send(title, body)
    records.event(store, run_id, "notify", title, {"sent": sent, "body": body})


def drive(store, run_id) -> None:
    """What the detached driver process runs: take over the run, and carry it forward."""
    deadline = time.monotonic() + 10
    while store.get("runs", run_id).driver_pid != os.getpid():     # wait to be handed the run
        if time.monotonic() > deadline:
            raise RuntimeError(f"run {run_id} was never handed to this driver")
        time.sleep(0.02)

    def stop(signum, frame):
        raise Stopped()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    advance(store, run_id)
