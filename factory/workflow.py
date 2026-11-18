"""Control: the rules. Which steps exist, in what order, and what happens after each.

This is the only place those rules live (FR-038). It is a table of step entries and two
small pure functions that read it. Nothing here reads or writes anything: no files, no
database, no processes. To change what the factory does, change the table.

The specification for this file is specs/001-near-loop-factory/contracts/workflow.md.
"""
from dataclasses import dataclass, field

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
class End:
    """End the run."""
    outcome: str        # accepted | rejected | needs-me
    reason: str = ""


@dataclass(frozen=True)
class Run:
    """Carry on with this step."""
    step: str


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
    failure: str | None = None      # timeout | error | guard | malformed | check
    failed_check: object = None     # the CheckResult that failed, if a check did
    message: str = ""               # the agent program's message, for "error"


# ---- the table: what the factory does, in order ----

STEPS: list[Step] = [
    # Where the target uses spec kit, the plan is spec kit's own documents, written under specs/.
    # Elsewhere "spec" allows nothing, so the planner changes no file.
    Step("plan", "agent", persona="planner", capabilities="read+edit", may_change="spec", on_pass=WAIT,
         commit_after=True, speckit=("specify", "plan"),
         inputs=("request", "ideals", "previous_plan", "comment", "failure", "speckit_instructions",
                 "speckit_context"),
         envelope={"plan": "text", "ideals_addressed": "list", "conflicts": "list"}),

    Step("baseline", "code", on_pass="write_tests", checks=("baseline",)),

    Step("write_tests", "agent", persona="test_writer", capabilities="read+edit", may_change="tests",
         on_pass="red", checks=("tests_added", "edge_cases_stated"), on_fail=Rework("write_tests"),
         inputs=("request", "plan", "test_paths", "failure"),
         envelope={"summary": "text", "test_files": "list", "edge_cases": "list"}),

    Step("red", "code", on_pass="build", checks=("tests_fail_first",), on_fail=Rework("write_tests"),
         commit_after=True),

    Step("build", "agent", persona="code_writer", capabilities="read+edit", may_change="not_tests",
         on_pass="test",
         inputs=("request", "plan", "ideals", "test_files", "failure"),
         envelope={"summary": "text", "files_changed": "list"}),

    Step("test", "code", on_pass="architecture_review", checks=("tests_pass",), on_fail=Rework("build"),
         commit_after=True),

    # Advice, not a gate: what the architect finds goes to a backlog, and the run carries on.
    Step("architecture_review", "agent", persona="architect", capabilities="read+edit", may_change="docs",
         on_pass="document", commit_after=True, advisory=True,
         inputs=("request", "plan", "ideals", "diff", "docs_paths"),
         envelope={"summary": "text", "suggestions": "list", "warnings": "list"}),

    # Documented before it is reviewed, so the reviewer judges the whole change.
    Step("document", "agent", persona="documenter", capabilities="read+edit", may_change="docs",
         on_pass="review", commit_after=True,
         inputs=("request", "plan", "diff", "docs_paths"),
         envelope={"summary": "text", "files_changed": "list"}),

    Step("review", "agent", persona="reviewer", on_pass="finish",
         checks=("verdict_accept",), on_fail=End("rejected"),
         inputs=("request", "plan", "ideals", "diff", "test_output"),
         envelope={"verdict": "verdict", "reasons": "list", "ideals_broken": "list"}),

    Step("finish", "code", on_pass=END_ACCEPTED),
]


def get(name, steps=None) -> Step:
    """The entry with this name."""
    for entry in steps or STEPS:
        if entry.name == name:
            return entry
    raise LookupError(f"there is no step named {name}")


# ---- what happens next ----

def next_step(step, result, attempts, limit) -> Run | Wait | End:
    """Given how a step went, what the run does now. The whole decision logic, in order.

    `attempts` maps a step's name to how many times it has run in this run. An attempt is
    one execution of a step, whatever caused it; no step runs more than `limit` times.
    """
    note = getattr(result.failed_check, "note", "")
    if result.failure == "guard":
        return End("needs-me", f"the {step.name} step changed what it may not, and the change was undone: {note}")
    if step.advisory and result.failure:    # an advisory step's failure is on the record; the run goes on
        return Run(step.on_pass)
    if result.failure == "timeout":
        return End("needs-me", f"the {step.name} step was stopped at its time limit of {result.message}")
    if result.failure == "error":
        return End("needs-me", f"the agent program failed during the {step.name} step: {result.message}")
    if result.failure == "malformed":
        return _rework(step.name, step, note, attempts, limit)
    if result.failure == "check":
        if isinstance(step.on_fail, Rework):
            return _rework(step.on_fail.step, step, note, attempts, limit)
        if step.on_fail.outcome == "rejected":
            return End("rejected", note)
        return End(step.on_fail.outcome, f"the {step.name} step failed: {note}")
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
        return Run(step.name)
    if decision == "abandon":
        return End("rejected", "abandoned by operator")
    raise ValueError(f"a waiting run can be approved, revised or abandoned; not {decision!r}")
