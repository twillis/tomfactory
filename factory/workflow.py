"""Control: the rules. Which steps exist, in what order, and what happens after each.

This is the only place those rules live (FR-038). It is a table of step entries and two
small pure functions that read it. Nothing here reads or writes anything: no files, no
database, no processes. To change what the factory does, change the table.

The specification for this file is specs/001-near-loop-factory/contracts/workflow.md.
"""
from dataclasses import dataclass, field, replace

KINDS = ("agent", "code")
CAPABILITIES = ("read", "read+edit")
SCOPES = ("nothing", "tests", "not_tests", "docs", "spec")   # what a step may change in the checkout
WAIT = "WAIT"                   # as an on_pass: stop and wait for the operator
END_ACCEPTED = "END_ACCEPTED"   # as an on_pass: the run is finished and accepted


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
    outcome: str        # accepted | rejected | needs-me
    reason: str = ""


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


@dataclass(frozen=True)
class Step:
    """One entry in the table. Defaults are closed: an entry that says nothing may do nothing."""
    name: str
    kind: str                           # agent | code
    on_pass: str                        # the next step's name, or WAIT, or END_ACCEPTED
    persona: str | None = None          # agent steps: a file in personas/
    capabilities: str = "read"          # agent steps: read | read+edit
    may_change: str = "nothing"         # nothing | tests | not_tests | docs | spec
    inputs: tuple = ()                  # agent steps: the names its prompt's {{placeholders}} may use
    envelope: dict = field(default_factory=dict)   # agent steps: required key -> text | list | verdict
    checks: tuple = ()                  # names of the step's own checks, run in order
    on_fail: Rework | End = End("needs-me")        # what a failed check of its own leads to
    commit_after: bool = False          # commit the checkout when the step passes
    advisory: bool = False              # its failure is recorded but does not stop the run
    speckit: tuple = ()                 # spec kit commands this step follows, where the target uses spec kit
    routes: dict = field(default_factory=dict)     # verdict -> Rework | Replan | End, for a step that judges
    revise_from: str | None = None      # a waiting step: where "send it back" returns to; None means itself
    timeout: int | None = None          # seconds; None means the target's step_timeout_seconds
    model: str | None = None            # agent steps; unused in this stage

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"step {self.name}: kind must be one of {KINDS}")
        if self.kind == "agent" and not self.persona:
            raise ValueError(f"step {self.name}: an agent step must name a persona")
        if self.kind == "code" and self.persona:
            raise ValueError(f"step {self.name}: a code step has no persona")
        if self.capabilities not in CAPABILITIES:
            raise ValueError(f"step {self.name}: capabilities must be one of {CAPABILITIES}")
        if self.may_change not in SCOPES:
            raise ValueError(f"step {self.name}: may_change must be one of {SCOPES}")


@dataclass
class StepResult:
    """How one execution of a step went."""
    passed: bool
    failure: str | None = None      # timeout | error | guard | malformed | check | question
    failed_check: object = None     # the CheckResult that failed, if a check did
    message: str = ""               # the agent program's message, for "error"
    verdict: str | None = None      # what a judging step decided


# ---- the table: what the factory does, in order ----

STEPS: list[Step] = [
    # "spec" allows spec kit's documents under specs/ where the target uses spec kit, and nothing
    # elsewhere: so in this plain cycle the planner changes no file.
    Step("plan", "agent", persona="planner", capabilities="read+edit", may_change="spec", on_pass=WAIT,
         commit_after=True,
         inputs=("request", "constitution", "ideals", "previous_plan", "comment", "failure",
                 "speckit_instructions", "speckit_context"),
         envelope={"plan": "text", "ideals_addressed": "list", "conflicts": "list"}),

    Step("baseline", "code", on_pass="write_tests", checks=("baseline",)),

    Step("write_tests", "agent", persona="test_writer", capabilities="read+edit", may_change="tests",
         on_pass="red", checks=("tests_added", "edge_cases_stated"), on_fail=Rework("write_tests"),
         inputs=("request", "plan", "test_paths", "failure", "speckit_instructions", "speckit_context"),
         envelope={"summary": "text", "test_files": "list", "edge_cases": "list"}),

    Step("red", "code", on_pass="build", checks=("tests_fail_first",), on_fail=Rework("write_tests"),
         commit_after=True),

    Step("build", "agent", persona="code_writer", capabilities="read+edit", may_change="not_tests",
         on_pass="test",
         inputs=("request", "plan", "constitution", "ideals", "test_files", "failure", "speckit_instructions",
                 "speckit_context"),
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

    Step("review", "agent", persona="reviewer", on_pass="finish",
         checks=("verdict_accept",), on_fail=End("rejected"),
         inputs=("request", "plan", "constitution", "ideals", "diff", "test_output"),
         envelope={"verdict": "verdict", "reasons": "list", "ideals_broken": "list"}),

    Step("finish", "code", on_pass=END_ACCEPTED),
]


# Not part of any table: the lead is called on whenever a step asks a question.
LEAD = Step("answer_question", "agent", persona="lead", on_pass="",
            inputs=("request", "constitution", "ideals", "plan", "question"),
            envelope={"answer": "text", "confident": ("yes", "no")})


def get(name, steps=None) -> Step:
    """The entry with this name."""
    for entry in steps or STEPS:
        if entry.name == name:
            return entry
    raise LookupError(f"there is no step named {name}")


# ---- what happens next ----

def next_step(step, result, attempts, limit) -> Run | Wait | Ask | Replan | End:
    """Given how a step went, what the run does now. The whole decision logic, in order.

    `attempts` maps a step's name to how many times it has run in this run. An attempt is
    one execution of a step, whatever caused it; no step runs more than `limit` times.
    """
    note = getattr(result.failed_check, "note", "")
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
        judged = getattr(result.failed_check, "name", "") == "verdict"      # a judging step said where to go
        route = (step.routes.get(result.verdict) if judged else None) or step.on_fail
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


def after_wait(decision, step, steps=None) -> Run | End:
    """What the operator's decision on a waiting step leads to."""
    table = steps or STEPS
    if decision == "approve":
        return Run(table[table.index(step) + 1].name)   # the waiting step's successor
    if decision == "revise":
        return Run(step.revise_from or step.name)       # back to the start of the stage that is waiting
    if decision == "abandon":
        return End("rejected", "abandoned by operator")
    raise ValueError(f"a waiting run can be approved, revised or abandoned; not {decision!r}")


# ---- the table for a codebase that uses spec kit: a persona for each of spec kit's stages ----

KIT_INPUTS = ("speckit_instructions", "speckit_context")
VERDICTS = ("accept", "rework", "replan", "reject")
_plain = {entry.name: entry for entry in STEPS}

SPEC_KIT_STEPS: list[Step] = [
    Step("specify", "agent", persona="analyst", capabilities="read+edit", may_change="spec", on_pass="clarify",
         commit_after=True, speckit=("specify",),
         inputs=("request", "constitution", "ideals", "comment", "failure", *KIT_INPUTS),
         envelope={"summary": "text", "assumptions": "list"}),

    Step("clarify", "agent", persona="analyst", capabilities="read+edit", may_change="spec", on_pass=WAIT,
         commit_after=True, speckit=("clarify",), revise_from="specify",       # first approval: the specification
         inputs=("request", "constitution", "ideals", "failure", *KIT_INPUTS),
         envelope={"plan": "text", "clarified": "list"}),

    replace(_plain["plan"], on_pass="tasks", speckit=("plan",)),

    Step("tasks", "agent", persona="planner", capabilities="read+edit", may_change="spec", on_pass="analyze",
         commit_after=True, speckit=("tasks",),
         inputs=("request", "constitution", "ideals", "failure", *KIT_INPUTS),
         envelope={"summary": "text"}),

    Step("analyze", "agent", persona="reviewer", on_pass=WAIT, speckit=("analyze", "checklist"),
         revise_from="plan",                                                   # second approval: plan and tasks
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
    Step("converge", "agent", persona="reviewer", on_pass="finish", speckit=("converge",),
         inputs=("request", "constitution", "ideals", "diff", "test_output", *KIT_INPUTS),
         envelope={"verdict": VERDICTS, "unbuilt": "list", "details": "list", "requirement_changes": "list",
                   "reasons": "list", "ideals_broken": "list"},
         routes={"rework": Rework("build"), "replan": Replan("specify"), "reject": End("rejected")}),

    _plain["finish"],
]


def table_for(spec_kit) -> list[Step]:
    """The steps a run goes through: chosen by whether its codebase uses spec kit."""
    return SPEC_KIT_STEPS if spec_kit else STEPS


def is_planning(name, steps) -> bool:
    """Is this step at or before the last point where the run waits for the operator?"""
    names = [entry.name for entry in steps]
    last_wait = max((i for i, entry in enumerate(steps) if entry.on_pass == WAIT), default=-1)
    return names.index(name) <= last_wait
