"""Control: execution. Carries one run forward, a step at a time, until it must wait or has ended.

The driver is general. It names no step and no persona, and decides nothing: it runs
whatever step the run is on, in the way that step's entry says, and asks workflow.py what
each result means and what happens next.

One execution of a step has three stages:

  prompt   for an agent step: the persona, the prompt with its inputs filled in, and how to ask
  execute  the agent program runs it, if it is an agent step
  verify   the always-applied checks, undoing a change the step was not allowed to make;
           then whether it asked a question; then the step's own checks

and then the step is committed if its entry says so, and its record completed.
"""
import functools
import json
import os
import pathlib
import re
import signal
import time
from dataclasses import asdict, dataclass, replace

from factory import agent, checks, config, notify, own_files, proc, records, run_record, sandbox, speckit, tables, workflow, workspace
from factory.config import under
from factory.workflow import Ask, CheckResult, End, Replan, StepResult, Wait
from factory.workspace import Workspace

NO_IDEALS = "No ideals have been stated."


class Stopped(BaseException):
    """Raised inside the driver when it is told to stop."""


def table_of(run) -> list:
    """The steps a run goes through. Decided here only: by its kind, and by its checkout's codebase."""
    cycle = config.read_target_config(run.target, run.base_commit).cycle
    return tables.table_for(speckit.available(run.workspace), run.run_kind, cycle)


def advance(store, run_id, adapter=None, personas_dir=None, prompts_dir=None) -> None:
    """Carry a run forward from its current step until it waits or ends."""
    adapter = adapter or agent.get_adapter()
    personas_dir = pathlib.Path(personas_dir or config.PERSONAS_DIR)
    prompts_dir = pathlib.Path(prompts_dir or config.PROMPTS_DIR)
    run = store.get("runs", run_id)
    checkout = Workspace.of(run)
    settings = config.read_target_config(run.target, run.base_commit)
    try:
        steps = table_of(run)
        validate(steps, personas_dir, prompts_dir)      # a wrong name is found now, before any paid step
        while True:
            run = store.get("runs", run_id)
            if run.state == "ended":        # ended from outside while we were working
                return
            step = workflow.get(run.current_step, steps)
            result, envelope = run_step(store, run, step, checkout, settings, adapter, personas_dir, prompts_dir)
            asked = None
            if result.failure == "question":    # on record the moment it is asked, whatever happens next
                asked = records.ask(store, run_id, step.name, step.persona, result.failed_check.note)
            attempts = {entry.name: records.attempts_counted(store, run_id, entry.name) for entry in steps}
            then = workflow.next_step(step, result, attempts, run.attempt_limit)
            if isinstance(then, End):
                end_run(store, run_id, then.outcome, then.reason)
                return
            if isinstance(then, Wait):
                wait_for_operator(store, run, step, envelope or {})
                return
            if isinstance(then, Replan):        # the requirement changed: back to planning, build set aside
                set_aside(store, run, checkout)
            if isinstance(then, Ask) and then.measure:      # the lead reads documents; it cannot measure (FR-100)
                records.await_operator(store, run_id)
                tell(store, run_id, f"Run {run_id}: a measurement is asked for", then.question)
                return
            if isinstance(then, Ask):           # the lead answers if it can; otherwise the operator is asked
                answered, said = run_step(store, run, tables.LEAD, checkout, settings, adapter,
                                          personas_dir, prompts_dir)
                if workflow.lead_answered(answered, said):
                    records.answer(store, asked.id, said["answer"], "lead")
                    continue                    # the step that asked runs again, with the answer
                records.await_operator(store, run_id)
                tell(store, run_id, f"Run {run_id}: a question for you", then.question)
                return
            records.move(store, run_id, current_step=then.step)
    except Stopped:
        end_run(store, run_id, "needs-me", "stopped by operator")
    except Exception as problem:            # a bug in the factory itself: record it, then let it show
        records.event(store, run_id, "error", f"{type(problem).__name__}: {problem}")
        end_run(store, run_id, "needs-me", f"the factory itself failed: {type(problem).__name__}: {problem}")
        raise


# ---- one execution of one step ----

@dataclass
class Doing:
    """One execution of one step: what it works on, and where what happens is recorded."""
    store: object
    run: object
    step: object
    checkout: Workspace
    settings: object
    timeout: float
    record: object = None
    errors: object = None

    def emit(self, kind, summary, payload=None):
        records.event(self.store, self.run.id, kind, summary, payload, step_id=self.record.id)

    def on_child(self, group):
        records.move(self.store, self.run.id, child_pgid=group)


def run_step(store, run, step, checkout, settings, adapter, personas_dir, prompts_dir):
    """Run one step once. Returns (how it went, the agent's envelope if there was one)."""
    paths = config.factory_paths()
    before, (head, dirty_before) = own_files.fingerprint(paths), counted_from(store, run, step, checkout)
    doing = Doing(store, run, step, checkout, settings, step.timeout or settings.step_timeout_seconds)
    asked = prompt(doing, prompts_dir) if step.kind == "agent" else ""
    doing.record = records.start_step(store, run.id, step.name, step.kind, step.persona, asked)
    doing.emit("step_start", step.name, {"attempt": doing.record.attempt, "persona": step.persona,
                                         "head": head, "dirty_before": dirty_before})
    with store.files.stderr_file(run.id, doing.record.id) as errors:
        doing.errors = errors
        reply = execute(doing, asked, adapter, personas_dir) if step.kind == "agent" else None
        result, done, changed = verify(doing, reply, before, dirty_before, paths)

    if step.advisory and result.failure not in (None, "guard"):
        checkout.discard(changed)       # a failed advisory step leaves nothing behind for the next to commit
    if result.passed and step.commit_after:
        commit = checkout.commit(run_record.step_message(store, run, step, reply.envelope if reply else None))
        if commit:
            doing.emit("commit", f"{step.name}: {commit[:10]}", {"commit": commit})

    records.finish_step(store, doing.record.id, produced(reply, done), [asdict(outcome) for outcome in done],
                        result.passed, result.failure, reply.tokens if reply else None,
                        reply.cost_estimate if reply else None)
    doing.emit("step_end", f"{step.name}: {'passed' if result.passed else result.failure}",
               {"passed": result.passed, "failure": result.failure})
    return result, reply.envelope if reply else None


def counted_from(store, run, step, checkout):
    """The checkout's head, and its files as they stood when the run came to this step (FR-108).

    A step's change is everything it changed over all its attempts in a row: work an attempt left before it asked
    a question, or before a check sent it back, is still the step's own when the next attempt keeps it as it is.
    Read afresh when the run comes to the step from another one, or when the head has moved since (a resume, or
    the operator's commit). The lead answering between two attempts does not break the row.
    """
    head = checkout.head()
    earlier = [s for s in store.query("steps", {"run_id": run.id}) if s.name != tables.LEAD.name]
    if earlier and earlier[-1].name == step.name and not earlier[-1].passed:
        started = store.query("events", {"run_id": run.id, "step_id": earlier[-1].id, "kind": "step_start"})
        payload = started[0].payload if started else {}
        if payload.get("head") == head and "dirty_before" in payload:
            return head, payload["dirty_before"]
    return head, checkout.dirty()


def prompt(doing, prompts_dir) -> str:
    """An agent step's prompt: its own file, then the shared parts that apply to it.

    The shared parts are the rules in order of precedence (for a step given the constitution
    and the ideals), spec kit's instructions (for a step that follows a spec kit command, where
    the codebase uses spec kit), how to ask a question, and the shape of the reply.
    """
    step, run = doing.step, doing.run
    sources = Sources(doing.store, run, doing.checkout, doing.settings, prompts_dir)
    inputs = {name: INPUTS[name](sources) for name in step.inputs}
    parts = [fill((prompts_dir / f"{step.name}.md").read_text(), inputs)]
    if {"constitution", "ideals"} <= set(step.inputs):
        parts.append(fill(_fragment(prompts_dir, "rules"), inputs))
    if step.speckit and speckit.available(doing.checkout.path):    # spec kit's scripts, run for the agent
        kit = speckit.prepare(step.speckit, doing.checkout, run.request)
        parts.append(fill(_fragment(prompts_dir, "speckit"), {"speckit_instructions": kit["instructions"],
                                                             "speckit_context": json.dumps(kit["context"], indent=2)}))
    if step.may_ask:            # every agent that may ask is told how, and what it was answered
        earlier = doing.store.query("questions", {"run_id": run.id, "step": step.name})
        answers = "\n\n".join(f"You asked: {q.question}\nThe {q.answered_by} answered: {q.answer}"
                              for q in earlier if q.answer is not None)
        parts.append(fill(_fragment(prompts_dir, "asking"), {"answers": answers}))
    parts.append(fill(_fragment(prompts_dir, "reply"), {"shape": reply_shape(step)}))
    return "\n".join(part.rstrip() + "\n" for part in parts)


def _fragment(prompts_dir, name) -> str:
    return (prompts_dir / "fragments" / f"{name}.md").read_text()


def reply_shape(step) -> str:
    """The JSON object a step must end its reply with, written out from its entry's envelope."""
    def shown(kind):
        if kind == "text":
            return '"…"'
        if kind == "list":
            return '["…"]'
        return '"' + " | ".join(workflow.verdicts(step) if kind == "verdict" else kind) + '"'
    return "{\n" + ",\n".join(f'  "{key}": {shown(kind)}' for key, kind in step.envelope.items()) + "\n}"


def execute(doing, asked, adapter, personas_dir):
    """The agent program runs the step. Every refusal it reports goes on the record."""
    reply = adapter(persona=(personas_dir / f"{doing.step.persona}.md").read_text(), prompt=asked,
                    cwd=doing.checkout.path, capabilities=doing.step.capabilities, timeout=doing.timeout,
                    on_event=doing.emit, raw_sink=doing.store.files.raw_sink(doing.run.id, doing.record.id),
                    stderr_file=doing.errors, on_child=doing.on_child, model=doing.step.model)
    for denial in reply.denials:
        doing.emit("denied", f"{denial.get('action')}: {denial.get('path')}", denial)
    return reply


def verify(doing, reply, before, dirty_before, paths):
    """Apply the checks. Returns (how the step went, every check's result, the files it changed)."""
    result = workflow.reply_failure(reply, doing.checkout.path, doing.timeout) if reply else StepResult(True)
    envelope = reply.envelope if reply else None
    context = checks.CheckContext(
        run=doing.run, step=doing.step, checkout=doing.checkout, target_config=doing.settings,
        changed=workspace.changed(dirty_before, doing.checkout.dirty()), envelope=envelope, before=before,
        factory_paths=paths, stderr_file=doing.errors, on_child=doing.on_child, timeout=doing.timeout)
    done = []

    def check(name):
        outcome = checks.get(name)(context)
        done.append(outcome)
        doing.emit("check", f"{name}: {'passed' if outcome.passed else 'failed'}", asdict(outcome))
        return outcome

    for outcome in [check(name) for name in checks.ALWAYS]:
        if not outcome.passed:
            UNDO[outcome.name](doing, outcome, paths)
            doing.emit("guard", f"undone: {outcome.note}", {"check": outcome.name, "files": sorted(context.changed)})
            if result.passed:
                result = StepResult(False, "guard", outcome)
    question = workflow.question_in(doing.step, envelope)
    if result.passed and question:      # it asked instead of finishing
        outcome = CheckResult(False, question, name="measure" if workflow.asks_to_measure(envelope) else "question")
        done.append(outcome)
        doing.emit("check", f"{outcome.name}: asked", asdict(outcome))
        result = StepResult(False, "question", outcome)
    if result.passed:
        try:
            for name in workflow.checks_for(doing.step):
                outcome = check(name)
                if not outcome.passed:
                    result = workflow.failed(name, outcome, doing.timeout)
                    break
        except sandbox.Unavailable as refused:      # not run at all, rather than run uncontained
            result = StepResult(False, "error", message=str(refused))
    if result.passed:       # a smell is measured on work that passed, and reported; it never fails the step (FR-107)
        for name in doing.step.smells:
            outcome = replace(checks.get(name)(context), smell=True)
            done.append(outcome)
            doing.emit("smell", f"{name}: {'none' if outcome.passed else 'found'}", asdict(outcome))
    if doing.step.routes and isinstance(envelope, dict):
        result.verdict = envelope.get("verdict")
    return result, done, context.changed


# How a guard's failure is put right: the step's change undone, or the factory's files put back.

def _undo_change(doing, outcome, paths):
    doing.checkout.undo()


def _restore_factory(doing, outcome, paths):
    """Put the factory's files back, keeping the changed versions in case the operator made them."""
    kept = doing.store.files.displaced_dir(doing.run.id)
    own_files.snapshot(paths, kept)
    own_files.restore(paths, doing.store.files.snapshot_dir(doing.run.id))
    outcome.note += f"; they were put back, and the changed versions are kept in {kept}"


UNDO = {"changes_allowed": _undo_change, "factory_untouched": _restore_factory}


def produced(reply, done) -> dict:
    """What a step produced, for its record: the agent's envelope, or what its command printed."""
    if reply is not None:
        if reply.envelope is not None:
            return reply.envelope
        return {"text": reply.text[:2000], **({"error": reply.error} if reply.error else {})}
    ran = next((outcome for outcome in reversed(done) if outcome.contained is not None), None)
    return {"output": ran.output or ran.note, "contained": ran.contained} if ran else {}


# ---- the inputs a prompt may use, by name ----

@dataclass
class Sources:
    """What an input is made from. Plans and finished steps are read once, when first needed."""
    store: object
    run: object
    checkout: Workspace
    settings: object
    prompts_dir: pathlib.Path

    @functools.cached_property
    def plans(self):
        return self.store.query("plans", {"run_id": self.run.id})

    @functools.cached_property
    def finished(self):
        return [record for record in self.store.query("steps", {"run_id": self.run.id}) if record.ended_at]


def _request(src):
    """The request, as the operator has amended it when sending plans back."""
    comments = [plan.comment for plan in src.plans if plan.decision == "revised" and plan.comment]
    if not comments:
        return src.run.request
    return (src.run.request + "\n\nThe operator added, when sending an earlier plan back:\n"
            + "\n".join(f"- {comment}" for comment in comments))


def _plan(src):
    """The plan last approved; or, before any approval, the latest one written.

    A step between the planner and the operator (the plan check) comes before any plan has
    been shown to him, so it reads the planner's own reply (FR-095).
    """
    approved = [plan for plan in src.plans if plan.decision == "approved"]
    if approved:
        return approved[-1].text
    written = [s.produced.get("plan") for s in src.finished if isinstance(s.produced, dict) and s.produced.get("plan")]
    return written[-1] if written else (src.plans[-1].text if src.plans else "")


def _sent_back(src):
    """The latest plan, if the operator sent it back."""
    return src.plans[-1] if src.plans and src.plans[-1].decision == "revised" else None


def _test_files(src):
    touched = set(src.checkout.files_changed_since_base()) | set(src.checkout.dirty())
    return "\n".join(sorted(name for name in touched if under(name, src.settings.test_paths)))


def _failure(src):
    """What went wrong last time, with what the command printed if one ran."""
    if not src.finished or src.finished[-1].passed or src.finished[-1].failure == "question":
        return ""       # an answered question is not a failure; the answer is given with the questions
    failed = next((c for c in src.finished[-1].checks or [] if not c["passed"]), None)
    if not failed:      # the agent program failed: say what it said, not only that it failed (FR-094)
        said = (src.finished[-1].produced or {}).get("error") if isinstance(src.finished[-1].produced, dict) else None
        return f"{src.finished[-1].failure}: {said}" if said else str(src.finished[-1].failure)
    return f"{failed['name']}: {failed['note']}" + (f"\n{failed['output']}" if failed.get("output") else "")


def _red_output(src):
    """What the new tests said before the build, from the step that saw them fail."""
    reds = [r for r in src.finished if (r.produced or {}).get("output")
            and any(c["name"] == "tests_fail_first" for c in r.checks or [])]
    return reds[-1].produced["output"] if reds else ""


def _test_output(src):
    outputs = [r.produced["output"] for r in src.finished if r.kind == "code" and (r.produced or {}).get("output")]
    return outputs[-1] if outputs else ""


def _friction(src):
    """What each agent said made its step harder, in its own words (FR-092)."""
    said = [f"- {s.name} (attempt {s.attempt}): {item}" for s in src.finished if isinstance(s.produced, dict)
            for item in s.produced.get("friction") or []]
    return "\n".join(said) or "No agent said anything made its step harder."


def _operator_feedback(src):
    """Everything the operator wrote during the run, verbatim: comments sent back with a plan, and answers."""
    said = [f"- Sent back with: {p.comment}" for p in src.plans if p.decision == "revised" and p.comment]
    said += [f"- Asked \"{q.question}\", the operator answered: {q.answer}"
             for q in src.store.query("questions", {"run_id": src.run.id}) if q.answered_by == "operator"]
    return "\n".join(said) or "The operator approved without comment."


def _findings(src):
    """The final review's and the architect's findings, as they recorded them."""
    keep = {"converge": ("unbuilt", "details", "requirement_changes", "ideals_broken", "reasons"),
            "review": ("reasons", "ideals_broken"), "architecture_review": ("warnings", "suggestions")}
    lines = []
    for s in src.finished:
        if s.name in keep and isinstance(s.produced, dict):
            for key in keep[s.name]:
                lines += [f"- {s.name}, {key}: {item}" for item in s.produced.get(key) or []]
    return "\n".join(lines) or "Nothing was recorded."


def _planning_answers(src):
    """Every question asked in this run that has its answer, whoever asked and whoever answered: a judge is
    shown what the planner was told, a measurement above all (FR-102)."""
    answered = [q for q in src.store.query("questions", {"run_id": src.run.id}) if q.answer is not None]
    return "\n\n".join(f"The {q.asked_by}, at {q.step}, asked: {q.question}\nThe {q.answered_by} answered: {q.answer}"
                       for q in answered)


def _checked(produced_by) -> dict:
    """What the plan check found most recently, as it recorded it: the last reply that holds findings."""
    checks = [s.produced for s in produced_by if isinstance(s.produced, dict) and "findings" in s.produced]
    return checks[-1] if checks else {}


def _plan_findings(src):
    return "\n".join(f"- {item}" for item in _checked(src.finished).get("findings") or [])


# The inputs a prompt may use, by name. A new input is one entry here.
INPUTS = {
    "request": _request,
    "run_kind": lambda src: (src.prompts_dir / "run_kinds" / f"{src.run.run_kind}.md").read_text(),
    "ideals": lambda src: src.run.ideals or NO_IDEALS,
    "constitution": lambda src: speckit.constitution(src.checkout.path) or "This codebase has no constitution of its own.",
    "plan": _plan,
    "previous_plan": lambda src: _sent_back(src).text if _sent_back(src) else "",
    "comment": lambda src: (_sent_back(src).comment or "") if _sent_back(src) else "",
    "test_paths": lambda src: ", ".join(src.settings.test_paths),
    "docs_paths": lambda src: ", ".join(src.settings.docs_paths),
    "test_files": _test_files,
    "failure": _failure,
    "question": lambda src: (records.pending_question(src.store, src.run.id) or {}).get("question", ""),
    # Without the run's own record: it holds the request and the plan, which a step given the diff already has.
    "diff": lambda src: src.checkout.diff_since_base(leaving_out=run_record.name(src.run)),
    "test_output": _test_output,
    "red_output": _red_output,
    "run_facts": lambda src: "\n".join(run_record.facts(src.store, src.run)),
    "friction": _friction,
    "operator_feedback": _operator_feedback,
    "findings": _findings,
    "planning_answers": _planning_answers,
    "plan_findings": _plan_findings,
    "run_name": lambda src: run_record.name(src.run).removeprefix("docs/runs/").removesuffix(".md"),
}


PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def fill(prompt_text, inputs) -> str:
    """Replace each {{name}} in a prompt with its input; "(none)" where there is nothing to give."""
    def replace(match):
        name = match.group(1)
        if name not in inputs:
            raise LookupError(f"the prompt uses {{{{{name}}}}}, which this step's entry does not list as an input")
        return inputs[name].strip() or "(none)"
    return PLACEHOLDER.sub(replace, prompt_text)


# ---- a table is checked before a run uses it ----

def validate(table, personas_dir=None, prompts_dir=None) -> None:
    """Refuse a table that names a step, check, input, persona or prompt that does not exist."""
    personas_dir = pathlib.Path(personas_dir or config.PERSONAS_DIR)
    prompts_dir = pathlib.Path(prompts_dir or config.PROMPTS_DIR)
    names = {step.name for step in table}
    problems = []
    for step in [*table, tables.LEAD]:
        leads = [step.on_pass, step.on_approve, step.revise_from, step.on_fail, *step.routes.values()]
        for target in leads:
            target = getattr(target, "step", target)
            if isinstance(target, str) and target and target not in (workflow.WAIT, workflow.END_ACCEPTED) \
                    and target not in names:
                problems.append(f"{step.name} leads to {target}, which is not in the table")
        problems += [f"{step.name} uses the check {name}, which is not registered"
                     for name in [*workflow.checks_for(step), *step.smells] if name not in checks.REGISTRY]
        if step.kind != "agent":
            continue
        problems += [f"{step.name} uses the input {name}, which is not defined"
                     for name in step.inputs if name not in INPUTS]
        if not (personas_dir / f"{step.persona}.md").is_file():
            problems.append(f"{step.name}'s persona {step.persona} has no file in {personas_dir}")
        prompt_file = prompts_dir / f"{step.name}.md"
        if not prompt_file.is_file():
            problems.append(f"{step.name} has no prompt file {prompt_file}")
            continue
        text = prompt_file.read_text()
        problems += [f"{step.name}'s prompt uses {{{{{name}}}}}, which its entry does not list"
                     for name in PLACEHOLDER.findall(text) if name not in step.inputs]
        problems += [f"{step.name}'s prompt does not say what `{key}` in its reply holds"
                     for key in step.envelope if f"`{key}`" not in text]
    if problems:
        raise ValueError("the step table is not sound: " + "; ".join(problems))


# ---- the run's state, outside any one step ----

def wait_for_operator(store, run, step, envelope) -> None:
    """Store what the operator must decide on, mark the run as waiting, and say so.

    A step that only checks a plan writes no plan of its own: the operator is shown the latest
    plan, with that step's findings beneath it (FR-095).
    """
    planned = envelope
    if not (envelope.get("plan") or envelope.get("summary")):
        earlier = [s.produced for s in store.query("steps", {"run_id": run.id})
                   if isinstance(s.produced, dict) and s.produced.get("plan")]
        planned = earlier[-1] if earlier else envelope
    text = planned.get("plan") or planned.get("summary") or json.dumps(planned)
    if "findings" in envelope:
        found = envelope["findings"] or ["nothing found"]
        text += "\n\n## Findings from the plan check\n\n" + "\n".join(f"- {item}" for item in found)
    if "taken" in envelope or "declined" in envelope:          # amended by the planner from the check (FR-104)
        found = _checked(store.query("steps", {"run_id": run.id})).get("findings") or []
        text += _listed("Findings from the plan check", found)
        text += _listed("Taken into the plan", envelope.get("taken"))
        text += _listed("Declined by the planner, with its reason", envelope.get("declined"))
    records.add_plan(store, run.id, text, planned.get("ideals_addressed") or [], planned.get("conflicts") or [])
    records.await_operator(store, run.id)
    tell(store, run.id, f"Run {run.id}: {step.name} ready — waiting for you", " ".join(run.request.split()[:12]))


def _listed(heading, items) -> str:
    return f"\n\n## {heading}\n\n" + "\n".join(f"- {item}" for item in (items or ["none"]))


def set_aside(store, run, checkout) -> None:
    """Keep what this run built on a side branch, and put its checkout back to what was last approved."""
    approvals = store.query("events", {"run_id": run.id, "kind": "approved"})
    back_to = approvals[-1].payload["commit"] if approvals else run.base_commit
    aside = checkout.set_aside(back_to)
    records.event(store, run.id, "set_aside", f"the build so far is kept on {aside}",
                  {"branch": aside, "back_to": back_to})


def end_run(store, run_id, outcome, reason):
    """The one way a run ends: outcome and reason set, nothing left running, the operator told."""
    run = store.get("runs", run_id)
    if run.state == "ended":
        return run
    proc.stop_group(run.child_pgid)
    ended = records.end(store, run_id, outcome, reason)
    tell(store, run_id, f"Run {run_id}: {outcome}", reason)
    if pathlib.Path(ended.workspace).is_dir():          # the record travels with the work, whatever the outcome
        try:
            run_record.write(store, ended, Workspace.of(ended), run_record.ended_message(store, ended))
        except Exception as problem:                    # the run has ended either way; say what went wrong
            records.event(store, run_id, "error", f"the run's record could not be written: {problem}")
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
