"""Control: the rules. Which steps exist, in what order, and what happens after each.

This is the only place those rules live (FR-038): the vocabularies, the step tables, and
the small pure functions that read them. Nothing here reads or writes anything: no files,
no database, no processes. To change what the factory does, change a table.

The specification for this file is specs/001-near-loop-factory/contracts/workflow.md.
"""
from dataclasses import dataclass, field, replace
from pathlib import PurePath

# ---- the vocabularies: each list of names is written here and nowhere else ----

KINDS = ("agent", "code")                               # of step
CAPABILITIES = ("read", "read+edit")
SCOPES = ("nothing", "tests", "not_tests", "docs", "spec")      # what a step may change in the checkout
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
    """Run a step again (an earlier one, or the same one), telling it what failed."""
    step: str


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
    routes: dict = field(default_factory=dict)     # a judging step: verdict -> Rework | Replan | End
    on_approve: str | None = None       # a waiting step: where approval leads
    revise_from: str | None = None      # a waiting step: where "send it back" returns to; None means itself
    commit_after: bool = False          # commit the checkout when the step passes
    advisory: bool = False              # its failure is recorded but does not stop the run
    may_ask: bool = True                # an agent step may ask a question instead of finishing
    speckit: tuple = ()                 # spec kit commands this step follows, where the target uses spec kit
    timeout: int | None = None          # seconds; None means the target's step_timeout_seconds
    model: str | None = None            # agent steps; unused in this stage

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
        if (self.on_pass == WAIT) != bool(self.on_approve):
            wrong("a waiting step, and only a waiting step, says where approval leads (on_approve)")
        if bool(self.routes) != ("verdict" in self.envelope.values()):
            wrong("a judging step has routes, and its envelope has a verdict; other steps have neither")


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


# ---- the plain table: a change, test first ----

KIT_INPUTS = ("speckit_instructions", "speckit_context")

STEPS: list[Step] = [
    # "spec" allows spec kit's documents where the target uses spec kit, and nothing elsewhere:
    # so in this plain cycle the planner changes no file.
    Step("plan", "agent", persona="planner", capabilities="read+edit", may_change="spec", on_pass=WAIT,
         on_approve="baseline", commit_after=True,
         inputs=("request", "run_kind", "constitution", "ideals", "previous_plan", "comment", "failure",
                 *KIT_INPUTS),
         envelope={"plan": "text", "ideals_addressed": "list", "conflicts": "list"}),

    Step("baseline", "code", on_pass="write_tests", checks=("baseline",)),

    Step("write_tests", "agent", persona="test_writer", capabilities="read+edit", may_change="tests",
         on_pass="red", checks=("tests_added", "tests_within_budget", "edge_cases_stated"),
         on_fail=Rework("write_tests"),
         inputs=("request", "plan", "test_paths", "failure", *KIT_INPUTS),
         envelope={"summary": "text", "test_files": "list", "edge_cases": "list"}),

    Step("red", "code", on_pass="build", checks=("tests_fail_first",), on_fail=Rework("write_tests"),
         commit_after=True),

    Step("build", "agent", persona="code_writer", capabilities="read+edit", may_change="not_tests",
         on_pass="test",
         inputs=("request", "plan", "constitution", "ideals", "test_files", "failure", *KIT_INPUTS),
         envelope={"summary": "text", "files_changed": "list"}),

    Step("test", "code", on_pass="architecture_review", checks=("tests_pass",), on_fail=Rework("build"),
         commit_after=True),

    # Advice, not a gate: what the architect finds goes to a backlog, and the run carries on.
    Step("architecture_review", "agent", persona="architect", capabilities="read+edit", may_change="docs",
         on_pass="document", commit_after=True, advisory=True,
         inputs=("request", "plan", "constitution", "ideals", "diff", "docs_paths"),
         envelope={"summary": "text", "suggestions": "list", "warnings": "list"}),

    # Documented before it is reviewed, so the reviewer judges the whole change.
    Step("document", "agent", persona="documenter", capabilities="read+edit", may_change="docs",
         on_pass="review", commit_after=True,
         inputs=("request", "plan", "diff", "docs_paths"),
         envelope={"summary": "text", "files_changed": "list"}),

    # A reply that contradicts itself (accept, with broken ideals) is asked for again.
    Step("review", "agent", persona="reviewer", on_pass="finish", on_fail=Rework("review"),
         routes={"reject": End("rejected")},
         inputs=("request", "run_kind", "plan", "constitution", "ideals", "diff", "test_output"),
         envelope={"verdict": "verdict", "reasons": "list", "ideals_broken": "list"}),

    Step("finish", "code", on_pass=END_ACCEPTED),
]

_plain = {entry.name: entry for entry in STEPS}


# Not part of any table: the lead is called on whenever a step asks a question.
LEAD = Step("answer_question", "agent", persona="lead", on_pass="", may_ask=False,
            inputs=("request", "constitution", "ideals", "plan", "question"),
            envelope={"answer": "text", "confident": ("yes", "no")})


# ---- the table for a codebase that uses spec kit: a persona for each of spec kit's stages ----

SPEC_KIT_STEPS: list[Step] = [
    Step("specify", "agent", persona="analyst", capabilities="read+edit", may_change="spec", on_pass="clarify",
         commit_after=True, speckit=("specify",),
         inputs=("request", "constitution", "ideals", "comment", "failure", *KIT_INPUTS),
         envelope={"summary": "text", "assumptions": "list"}),

    Step("clarify", "agent", persona="analyst", capabilities="read+edit", may_change="spec", on_pass=WAIT,
         on_approve="plan", revise_from="specify", commit_after=True, speckit=("clarify",),  # first approval
         inputs=("request", "constitution", "ideals", "failure", *KIT_INPUTS),
         envelope={"plan": "text", "clarified": "list"}),

    replace(_plain["plan"], on_pass="tasks", on_approve=None, speckit=("plan",)),

    Step("tasks", "agent", persona="planner", capabilities="read+edit", may_change="spec", on_pass="analyze",
         commit_after=True, speckit=("tasks",),
         inputs=("request", "constitution", "ideals", "failure", *KIT_INPUTS),
         envelope={"summary": "text"}),

    Step("analyze", "agent", persona="reviewer", on_pass=WAIT, on_approve="baseline", revise_from="plan",
         speckit=("analyze", "checklist"),                                    # second approval: plan and tasks
         inputs=("request", "constitution", "ideals", "failure", *KIT_INPUTS),
         envelope={"plan": "text", "findings": "list"}),

    _plain["baseline"],
    replace(_plain["write_tests"], speckit=("implement",)),
    _plain["red"],
    replace(_plain["build"], speckit=("implement",)),
    _plain["test"],
    _plain["architecture_review"],
    replace(_plain["document"], on_pass="converge"),

    # The scope assessment: is what was built what was approved? (FR-058, FR-059)
    Step("converge", "agent", persona="reviewer", on_pass="finish", on_fail=Rework("converge"),
         speckit=("converge",),
         routes={"rework": Rework("build"), "replan": Replan("specify"), "reject": End("rejected")},
         inputs=("request", "constitution", "ideals", "diff", "test_output", *KIT_INPUTS),
         envelope={"verdict": "verdict", "unbuilt": "list", "details": "list", "requirement_changes": "list",
                   "reasons": "list", "ideals_broken": "list"}),

    _plain["finish"],
]


# ---- tidying: a change that must not alter behaviour, so no failing test comes first (FR-066) ----
# The tests must pass before (baseline) and after (test). One side is held still: tidying the
# tests may not touch the code, and tidying the code may not touch the tests.

def _tidy(step: Step) -> list[Step]:
    return [_plain["plan"], replace(_plain["baseline"], on_pass=step.name), step,
            replace(_plain["test"], on_pass="review", on_fail=Rework(step.name)),
            replace(_plain["review"], routes={"reject": Rework(step.name)}),    # a rejection guides another try
            _plain["finish"]]


TIDY_TESTS = _tidy(Step("tidy_tests", "agent", persona="test_writer", capabilities="read+edit",
                        may_change="tests", on_pass="test",
                        inputs=("request", "plan", "test_paths", "failure"),
                        envelope={"summary": "text", "removed": "list", "kept": "list"}))

TIDY_CODE = _tidy(Step("tidy_code", "agent", persona="code_writer", capabilities="read+edit",
                       may_change="not_tests", on_pass="test",
                       inputs=("request", "plan", "constitution", "ideals", "failure"),
                       envelope={"summary": "text", "files_changed": "list"}))


# ---- the kinds of run: each one's table, without spec kit and with it ----
# What the planner and reviewer are told about each kind is in prompts/run_kinds/<kind>.md.

RUN_KINDS = {
    "change": (STEPS, SPEC_KIT_STEPS),
    "tidy-tests": (TIDY_TESTS, TIDY_TESTS),
    "tidy-code": (TIDY_CODE, TIDY_CODE),
}
TABLES = [STEPS, SPEC_KIT_STEPS, TIDY_TESTS, TIDY_CODE]


def table_for(spec_kit, run_kind) -> list[Step]:
    """The steps a run goes through: chosen by its kind, and by whether its codebase uses spec kit."""
    if run_kind not in RUN_KINDS:
        raise ValueError(f"a run is one of: {', '.join(RUN_KINDS)}; not {run_kind!r}")
    return RUN_KINDS[run_kind][bool(spec_kit)]
