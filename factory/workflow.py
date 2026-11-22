"""Control: the rules. What a step is, and what happens after each one.

This is the only place those rules live (FR-038): the vocabularies, the shape of a step
entry, and the small pure functions that read entries. The tables of steps themselves are
in tables.py. Nothing here reads or writes anything: no files, no database, no processes.

The specification for this file is specs/001-near-loop-factory/contracts/workflow.md.
"""
from dataclasses import dataclass, field, replace
from pathlib import PurePath

# ---- the vocabularies: each list of names is written here and nowhere else ----

KINDS = ("agent", "code")                               # of step
CAPABILITIES = ("read", "read+edit")
SCOPES = ("nothing", "tests", "not_tests", "docs", "spec")      # what a step may change in the checkout
GRADES = ("standard", "strongest")      # how strong a model an agent step is given (FR-088)
OUTCOMES = ("accepted", "rejected", "needs-me")
FAILURES = ("timeout", "error", "guard", "malformed", "check", "question")     # how a step can fail
ACCEPT = "accept"               # the verdict that passes a judging step; every other verdict is a route
WAIT = "WAIT"                   # as an on_pass: stop and wait for the operator
END_ACCEPTED = "END_ACCEPTED"   # as an on_pass: the run is finished and accepted


# ---- what a step's execution produced, and where the run goes next ----

@dataclass
class CheckResult:
    """What one check found. A check's name is stamped on by the registry that ran it."""
    passed: bool
    note: str = ""                  # why it failed, or a short remark
    output: str = ""                # what a command it ran printed, if it ran one
    timed_out: bool = False         # the command it ran hit the time limit
    contained: dict | None = None   # it ran the target's code, contained: {"network": bool}
    name: str = ""


@dataclass
class StepResult:
    """How one execution of a step went."""
    passed: bool
    failure: str | None = None              # one of FAILURES
    failed_check: CheckResult | None = None
    message: str = ""                       # the agent program's message, for "error"
    verdict: str | None = None              # what a judging step decided

    def __post_init__(self):
        if self.failure is not None and self.failure not in FAILURES:
            raise ValueError(f"a step fails in one of these ways: {', '.join(FAILURES)}; not {self.failure!r}")


@dataclass(frozen=True)
class Rework:
    """Run a step again (an earlier one, or the same one), telling it what failed.

    With `at_most`, once `step` has run that many times this route goes on to the step named
    `then` instead: the finding is recorded, not chased.
    """
    step: str
    at_most: int | None = None
    then: str | None = None


@dataclass(frozen=True)
class Replan:
    """Go back to the planning stage at this step. What was built is set aside first."""
    step: str


@dataclass(frozen=True)
class End:
    """End the run."""
    outcome: str        # one of OUTCOMES
    reason: str = ""

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise ValueError(f"a run ends {', '.join(OUTCOMES)}; not {self.outcome!r}")


@dataclass(frozen=True)
class Run:
    """Carry on with this step."""
    step: str


@dataclass(frozen=True)
class Ask:
    """A step asked a question instead of finishing. The lead answers, or the operator does."""
    question: str


@dataclass(frozen=True)
class Wait:
    """Stop and wait for the operator's decision."""


# ---- a step entry ----

@dataclass(frozen=True)
class Step:
    """One entry in a table. Defaults are closed: an entry that says nothing may do nothing."""
    name: str
    kind: str                           # one of KINDS
    on_pass: str                        # the next step's name, or WAIT, or END_ACCEPTED
    persona: str | None = None          # agent steps: a file in personas/
    capabilities: str = "read"          # agent steps: one of CAPABILITIES
    may_change: str = "nothing"         # one of SCOPES
    inputs: tuple = ()                  # agent steps: the names its prompt's {{placeholders}} may use
    envelope: dict = field(default_factory=dict)   # agent steps: required key -> text | list | verdict | (values)
    checks: tuple = ()                  # names of the step's own checks, run in order
    on_fail: Rework | End = End("needs-me")        # what a failed check of its own leads to
    routes: dict = field(default_factory=dict)     # a step that gives a verdict: verdict -> Rework | Replan | End.
                                                   # A judging step's; and the build's one, for a test no build can pass
    on_approve: str | None = None       # a waiting step: where approval leads
    revise_from: str | None = None      # a waiting step: where "send it back" returns to; None means itself
    commit_after: bool = False          # commit the checkout when the step passes
    advisory: bool = False              # its failure is recorded but does not stop the run
    may_ask: bool = True                # an agent step may ask a question instead of finishing
    speckit: tuple = ()                 # spec kit commands this step follows, where the target uses spec kit
    timeout: int | None = None          # seconds; None means the target's step_timeout_seconds
    ideals_stop: bool = True            # a judging step: a broken ideal stops the run; False reports it only
    model: str = "standard"             # agent steps: one of GRADES; which model that is, only agent.py knows

    def __post_init__(self):
        def wrong(problem):
            raise ValueError(f"step {self.name}: {problem}")
        if self.kind not in KINDS:
            wrong(f"kind must be one of {KINDS}")
        if (self.kind == "agent") != bool(self.persona):
            wrong("an agent step names a persona, and a code step does not")
        if self.capabilities not in CAPABILITIES:
            wrong(f"capabilities must be one of {CAPABILITIES}")
        if self.may_change not in SCOPES:
            wrong(f"may_change must be one of {SCOPES}")
        if self.model not in GRADES:
            wrong(f"model must be one of {GRADES}")
        if (self.on_pass == WAIT) != bool(self.on_approve):
            wrong("a waiting step, and only a waiting step, says where approval leads (on_approve)")
        if bool(self.routes) != ("verdict" in self.envelope.values()):
            wrong("a judging step, or any step that gives a verdict, has routes, and its envelope has a verdict;"
                  " other steps have neither")


def verdicts(step) -> tuple:
    """The verdicts a judging step may give: accept, or one of its routes."""
    return (ACCEPT, *step.routes)


def checks_for(step) -> list[str]:
    """The checks a step gets, in order: its reply's shape, its verdict, then its own."""
    return ((["envelope_valid"] if step.kind == "agent" else []) + (["verdict"] if step.routes else [])
            + list(step.checks))


def failed(check, outcome, timeout) -> StepResult:
    """What kind of failure a failed check is."""
    if outcome.timed_out:
        return StepResult(False, "timeout", outcome, message=f"{timeout:g} seconds")
    return StepResult(False, "malformed" if check == "envelope_valid" else "check", outcome)


def reply_failure(reply, checkout, timeout) -> StepResult:
    """How the agent program's reply went, before anything it did is checked."""
    blocked = [d["path"] for d in reply.denials if _within(d.get("path") or "/", checkout)]
    if reply.timed_out:
        return StepResult(False, "timeout", message=f"{timeout:g} seconds")
    if not reply.ok:
        return StepResult(False, "error", message=reply.error or "no message")
    if blocked:         # trying again cannot help: the program will refuse again
        return StepResult(False, "error", message="it refused to let the agent work inside the run's own"
                                                  f" checkout: {', '.join(blocked)}")
    return StepResult(True)


def _within(path, folder) -> bool:
    return PurePath(path).is_relative_to(folder)


def question_in(step, envelope) -> str | None:
    """The question a step asked instead of finishing: its whole reply is {"question": ...}."""
    if step.may_ask and isinstance(envelope, dict) and set(envelope) == {"question"}:
        return str(envelope["question"])
    return None


def lead_answered(result, envelope) -> bool:
    """The lead has answered only if its step passed and it said it is confident."""
    return result.passed and (envelope or {}).get("confident") == "yes"


# ---- what happens next ----

def next_step(step, result, attempts, limit) -> Run | Wait | Ask | Replan | End:
    """Given how a step went, what the run does now. The whole decision logic, in order.

    `attempts` maps a step's name to how many times it has run in this run. An attempt is
    one execution of a step, whatever caused it; no step runs more than `limit` times.
    """
    note = result.failed_check.note if result.failed_check else ""
    if result.failure == "guard":
        return End("needs-me", f"the {step.name} step changed what it may not, and the change was undone: {note}")
    if step.advisory and result.failure:    # an advisory step's failure is on the record; the run goes on
        return Run(step.on_pass)
    if result.failure == "question":
        if attempts.get(step.name, 0) >= limit:
            return End("needs-me", f"the {step.name} step has run {limit} times and is still asking: {note}")
        return Ask(note)
    if result.failure == "timeout":
        return End("needs-me", f"the {step.name} step was stopped at its time limit of {result.message}")
    if result.failure == "error":
        return End("needs-me", f"the agent program failed during the {step.name} step: {result.message}")
    if result.failure == "malformed":
        return _rework(step.name, step, note, attempts, limit)
    if result.failure == "check":
        route = step.routes.get(result.verdict) or step.on_fail     # a judging step's verdict says where
        if isinstance(route, Rework):
            if route.at_most and attempts.get(route.step, 0) >= route.at_most:
                return Run(route.then)
            return _rework(route.step, step, note, attempts, limit)
        if isinstance(route, Replan):
            if attempts.get(route.step, 0) >= limit:
                return End("needs-me", f"planning has already restarted at {route.step} {limit} times;"
                                       f" the last reason, from {step.name}: {note}")
            return route
        if route.outcome == "rejected":
            return End("rejected", note)
        return End(route.outcome, f"the {step.name} step failed: {note}")
    if step.on_pass == WAIT:
        return Wait()
    if step.on_pass == END_ACCEPTED:
        return End("accepted", "the tests pass and the review found the result matches the request,"
                               " the plan and the ideals")
    return Run(step.on_pass)


def _rework(target, step, note, attempts, limit) -> Run | End:
    """Run `target` again, unless it has already had every attempt it is allowed."""
    if attempts.get(target, 0) >= limit:
        return End("needs-me", f"the {target} step has run {limit} times without success;"
                               f" the last failure, in {step.name}: {note}")
    return Run(target)


def after_wait(decision, step) -> Run | End:
    """What the operator's decision on a waiting step leads to."""
    if decision == "approve":
        return Run(step.on_approve)
    if decision == "revise":
        return Run(step.revise_from or step.name)       # back to the start of the stage that is waiting
    if decision == "abandon":
        return End("rejected", "abandoned by operator")
    raise ValueError(f"a waiting run can be approved, revised or abandoned; not {decision!r}")


def get(name, steps) -> Step:
    """The entry with this name, in this table."""
    for entry in steps:
        if entry.name == name:
            return entry
    raise LookupError(f"there is no step named {name}")


def is_planning(name, steps) -> bool:
    """Is this step at or before the last point where the run waits for the operator?"""
    names = [entry.name for entry in steps]
    last_wait = max((i for i, entry in enumerate(steps) if entry.on_pass == WAIT), default=-1)
    return names.index(name) <= last_wait
