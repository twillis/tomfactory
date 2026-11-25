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
SCOPES = ("nothing", "tests", "not_tests", "docs", "docs_but_backlog", "spec", "checkout")   # what a step may change
GRADES = ("light", "middle", "standard", "strongest")    # how strong a model an agent step is given, weakest first (FR-088)
CLIMBS_TO = "standard"      # a retry climbs a grade at a time, never past this one unless the step starts above it (FR-109)
FOUND = ("answered", "inconclusive")       # how a spike ends, and only a spike (FR-116)
OUTCOMES = ("accepted", "rejected", "needs-me", *FOUND)
FAILURES = ("timeout", "error", "guard", "malformed", "check", "question")     # how a step can fail
ANSWERERS = ("operator", "orchestrator")   # who may answer through `factory answer`; the lead answers inside (FR-139)
ACCEPT = "accept"               # the verdict that passes a judging step; every other verdict is a route
DEFECTIVE_TESTS = "defective_tests"     # where a builder's reply names the tests no build can pass (FR-150)
WAIT = "WAIT"                   # as an on_pass: stop and wait for the operator
END_ACCEPTED = "END_ACCEPTED"   # as an on_pass: the run is finished and accepted
END_AS_FOUND = "END_AS_FOUND"   # as an on_pass: the run ends as its findings say, answered or inconclusive (FR-116)
# For showing a run's progress (FR-145): the state of each stage, the groups stages fall in, and the operator's waits
# as stages, after the step that waits: a planning dialogue's three, or a plain approval.
STAGE_STATES = ("done", "current", "to-come", "failed", "skipped")
GROUPS = ("planning", "waiting", "building", "reviewing")
WAITS = ("approval",)
DIALOGUE_WAITS = ("answers", "agreement", "approval")


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
    smell: bool = False             # run as a smell: what it found is reported and never fails the step (FR-107)
    measured: dict | None = None    # what a test run measured beside passing: {"coverage": %, "files": {name: %}}
    failing: dict | None = None     # what its test report names as failing (FR-141): {"count": n, "tests":
                                    # [{"test": id, "message": text}, ...]}, the first checks.FAILING_KEPT of them


@dataclass
class StepResult:
    """How one execution of a step went."""
    passed: bool
    failure: str | None = None              # one of FAILURES
    failed_check: CheckResult | None = None
    message: str = ""                       # the agent program's message, for "error"
    verdict: str | None = None              # what a judging step decided
    named: tuple = ()                       # the tests its verdict names, the builder's `defective_tests` (FR-150)

    def __post_init__(self):
        if self.failure is not None and self.failure not in FAILURES:
            raise ValueError(f"a step fails in one of these ways: {', '.join(FAILURES)}; not {self.failure!r}")


@dataclass(frozen=True)
class Rework:
    """Run a step again (an earlier one, or the same one), telling it what failed.

    With `at_most`, once `step` has run that many times this route goes on to `then` instead: the
    step it names, the finding recorded and not chased; or an End, the run boxed (FR-114).
    With `once_per_test`, it is taken only for a report that names a test no earlier report named (FR-150).
    """
    step: str
    at_most: int | None = None
    then: "str | End | None" = None
    once_per_test: bool = False


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
    """A step asked a question instead of finishing. The lead answers, or the operator does.

    With `measure`, it asked for a fact only a running system can give: the lead, who answers from
    documents, is not asked, and it goes straight to whoever drives the run (FR-100).
    """
    question: str
    measure: bool = False


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
    smells: tuple = ()                  # checks run after its own pass: what they find is reported, never a failure
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
    dialogue: bool = False              # agent steps: it speaks in a planning dialogue, its reply a batch (FR-120)
    on_moved: str | None = None         # a dialogue's waiting step: where approval leads when the codebase has
                                        # moved since the dialogue read it (FR-125)

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
        if self.on_moved and self.on_pass != WAIT:
            wrong("only a waiting step says where approval leads when the codebase has moved (on_moved)")
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
    """The question a step asked instead of finishing: its whole reply is {"question": ...}, or, for a fact
    only a running system can give, {"measure": ...}."""
    if not step.may_ask or not isinstance(envelope, dict):
        return None
    if set(envelope) == {"question"}:
        return str(envelope["question"])
    if asks_to_measure(envelope):
        return str(envelope["measure"])
    return None


def asks_to_measure(envelope) -> bool:
    """Is this reply a request for a measurement, and nothing else?"""
    return isinstance(envelope, dict) and set(envelope) == {"measure"}


def lead_answered(result, envelope) -> bool:
    """The lead has answered only if its step passed and it said it is confident."""
    return result.passed and (envelope or {}).get("confident") == "yes"


def grade_for(step, tries, climbs_to=CLIMBS_TO) -> str:
    """The grade this attempt of `step` runs on: its own, one higher for each earlier attempt whose work was found
    wanting (`records.attempts_climbed`, FR-109). A cheap model that fails is given a stronger one, never the strongest unless the step starts there:
    the cost the operator controls stays his (the strongest is his to choose)."""
    own = GRADES.index(step.model)
    ceiling = max(own, GRADES.index(climbs_to))
    return GRADES[min(own + tries, ceiling)]


# ---- what happens next ----

def next_step(step, result, attempts, limit, found=None, reports=()) -> Run | Wait | Ask | Replan | End:
    """Given how a step went, what the run does now. The whole decision logic, in order.

    `attempts` maps a step's name to how many times it has run in this run. An attempt is
    one execution of a step, whatever caused it; no step runs more than `limit` times.
    `found` is what a spike's findings said, its outcome and reason, for a step that ends the run as found.
    `reports` is the tests each earlier report of a defective test in the run named, oldest first (FR-150).
    """
    note = result.failed_check.note if result.failed_check else ""
    if result.failure == "guard":
        return End("needs-me", f"the {step.name} step changed what it may not, and the change was undone: {note}")
    if step.advisory and result.failure:    # an advisory step's failure is on the record; the run goes on
        return Run(step.on_pass)
    if result.failure == "question":
        if attempts.get(step.name, 0) >= limit:
            return End("needs-me", f"the {step.name} step has run {limit} times and is still asking: {note}")
        return Ask(note, measure=result.failed_check.name == "measure")
    if result.failure == "timeout":
        return End("needs-me", f"the {step.name} step was stopped at its time limit of {result.message}")
    if result.failure == "error":
        return End("needs-me", f"the agent program failed during the {step.name} step: {result.message}")
    if result.failure == "malformed":
        return _rework(step.name, step, note, attempts, limit)
    if result.failure == "check":
        route = step.routes.get(result.verdict) or step.on_fail     # a judging step's verdict says where
        if isinstance(route, Rework):
            if not _taken(route, result.named, attempts, reports):
                if isinstance(route.then, End):         # boxed: had its tries, the run ends saying why
                    return End(route.then.outcome, f"{route.then.reason}: {note}")
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
    if step.on_pass == END_AS_FOUND:
        return as_found(found)
    return Run(step.on_pass)


def _taken(route, named, attempts, reports) -> bool:
    """Is this rework route taken? Not once its step has run `at_most` times (FR-114). A route taken once per test
    is taken for a report naming a test no earlier report named; one naming none, only if it is the first (FR-150)."""
    if route.at_most and attempts.get(route.step, 0) >= route.at_most:
        return False
    if not route.once_per_test:
        return True
    if not named:
        return not reports
    reported = {comparable_name(test) for report in reports for test in report}
    return any(comparable_name(test) not in reported for test in named)


def comparable_name(name) -> tuple:
    """A test's name in a form two reports can compare (FR-150). A runner's `tests/test_x.py::TestY::test_z` and
    a JUnit report's `tests.test_x.TestY::test_z` are the same test; a parametrised case's id, in brackets, is kept
    whole."""
    where, bracket, case = str(name).strip().partition("[")
    where = where.replace(".py::", "::").removesuffix(".py").replace("::", ".").replace("/", ".")
    return (*where.split("."), bracket + case)


# ---- a spike: a run whose product is an answer (FR-113 to FR-117) ----

def ends_as_found(steps) -> bool:
    """Is this a spike's table: one whose run ends as its findings say, never accepted or rejected?"""
    return any(entry.on_pass == END_AS_FOUND for entry in steps)


def as_found(found) -> End:
    """How a spike ends: as its findings said, with their reason (FR-116)."""
    outcome = (found or {}).get("outcome")
    if outcome not in FOUND:
        return End("needs-me", "the spike came to its end with no findings that say answered or inconclusive")
    return End(outcome, str(found.get("reason") or "").strip() or f"the findings say {outcome}, and give no reason")


def over_budget(steps, step, spent, cap, done) -> End | None:
    """A spike is boxed by a budget (FR-117): before each of its agent steps, at or over the cap (0 for none) it
    ends inconclusive, saying what it had. `spent` is what the run's steps have cost; `done`, the steps that passed."""
    if not ends_as_found(steps) or step.kind != "agent" or not cap or spent < cap:
        return None
    had = ", ".join(dict.fromkeys(done)) or "nothing"
    return End("inconclusive", f"the spike reached its budget of ${cap:.2f}, with ${spent:.2f} spent, before the"
                               f" {step.name} step; it had done: {had}")


# ---- a planning dialogue: rounds, from an ask to an agreed plan (FR-119 to FR-126) ----

def round_outcome(said, points_in_a_row, limit) -> str:
    """How a round of the dialogue ends, from every speaker's batch in it (FR-120, FR-122).

    "questions": a speaker asked the asker something, or asked for a measurement; the run waits for the answers.
    "points": only blocking points for one another were raised (what would break the build or contradict a ruling),
    which the artifacts settle; the agents go round again at once. "stuck": the same, `limit` rounds in a row; the
    asker is shown them. "aligned": nothing blocking and nothing asked, so the planner proposed aligned (its own
    check makes it ask otherwise); the asker is asked to agree. A note never holds alignment open (FR-130).
    """
    if any(batch.get("questions") or batch.get("measure") for batch in said):
        return "questions"
    if any(batch.get("blocking") for batch in said):
        return "stuck" if points_in_a_row + 1 >= limit else "points"
    return "aligned"


def after_round(outcome, first) -> Run | Wait:
    """Where a round leads: round again at once, from its first speaker; or wait for the asker."""
    return Run(first) if outcome == "points" else Wait()


def dialogue_over_budget(spent, cap) -> bool:
    """Has the dialogue spent its budget since the asker last said to spend more (FR-124)? 0 is no budget."""
    return bool(cap) and spent >= cap


def spend_more(answer) -> bool | None:
    """The asker's answer to the budget question: yes, no, or neither (refused, so it is asked again) (FR-124)."""
    return {"yes": True, "y": True, "a": True, "no": False, "n": False, "b": False}.get(answer.strip().lower())


def _rework(target, step, note, attempts, limit) -> Run | End:
    """Run `target` again, unless it has already had every attempt it is allowed."""
    if attempts.get(target, 0) >= limit:
        return End("needs-me", f"the {target} step has run {limit} times without success;"
                               f" the last failure, in {step.name}: {note}")
    return Run(target)


def after_wait(decision, step, steps=(), moved=False) -> Run | End:
    """What the operator's decision on a waiting step, in this table, leads to. A spike abandoned is
    inconclusive: it is never rejected (FR-116). A plan agreed in a dialogue and approved after the codebase
    has moved is re-checked against it first (FR-125)."""
    if decision == "approve":
        return Run(step.on_moved if moved and step.on_moved else step.on_approve)
    if decision == "revise":
        return Run(step.revise_from or step.name)       # back to the start of the stage that is waiting
    if decision == "abandon":
        return End("inconclusive" if ends_as_found(steps) else "rejected", "abandoned by operator")
    raise ValueError(f"a waiting run can be approved, revised or abandoned; not {decision!r}")


def get(name, steps) -> Step:
    """The entry with this name, in this table."""
    for entry in steps:
        if entry.name == name:
            return entry
    raise LookupError(f"there is no step named {name}")


def main_path(steps) -> list[Step]:
    """The steps a run goes through when nothing is sent back: from the first, each one's on_pass, and past a wait
    to where approval leads, to the end (FR-145). A step reached only by a route, like mend_tests, is not on it."""
    path = [steps[0]]
    while True:
        last = path[-1]
        following = last.on_approve if last.on_pass == WAIT else last.on_pass
        if following in (END_ACCEPTED, END_AS_FOUND):
            return path
        path.append(get(following, steps))


def is_planning(name, steps) -> bool:
    """Is this step at or before the last point where the run waits for the operator?"""
    names = [entry.name for entry in steps]
    last_wait = max((i for i, entry in enumerate(steps) if entry.on_pass == WAIT), default=-1)
    return names.index(name) <= last_wait
