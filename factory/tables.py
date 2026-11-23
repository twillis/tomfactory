"""Control: the tables. Which steps a run goes through, in what order, for each kind of run.

Each table is data: a list of step entries, whose shape and rules are in workflow.py. To
change what the factory does, change a table. Nothing here reads or writes anything.
"""
from dataclasses import replace

from factory.workflow import END_ACCEPTED, End, Rework, Step, WAIT

# ---- the plain table: a change, test first ----

STEPS: list[Step] = [
    # "spec" allows spec kit's documents where the target uses spec kit, and nothing elsewhere:
    # so in this plain cycle the planner changes no file.
    Step("plan", "agent", persona="planner", capabilities="read+edit", may_change="spec", on_pass=WAIT,
         on_approve="baseline", commit_after=True, smells=("plan_lines_within_length",), on_fail=Rework("plan"),
         inputs=("request", "run_kind", "constitution", "ideals", "previous_plan", "comment", "failure",
                 "test_paths", "docs_paths"),
         envelope={"plan": "text", "ideals_addressed": "list", "conflicts": "list"}),

    Step("baseline", "code", on_pass="write_tests", checks=("baseline",)),

    Step("write_tests", "agent", persona="test_writer", capabilities="read+edit", may_change="tests",
         on_pass="red", checks=("tests_added", "edge_cases_stated"), smells=("tests_within_budget", "lines_within_length"),
         on_fail=Rework("write_tests"),
         inputs=("request", "plan", "test_paths", "failure"),
         envelope={"summary": "text", "test_files": "list", "edge_cases": "list"}),

    Step("red", "code", on_pass="build", checks=("tests_fail_first",), on_fail=Rework("write_tests"),
         commit_after=True),

    # The builder may not touch a test. One it finds no build can pass goes to the test writer, once (FR-097);
    # reported again, the tests are run and the failure takes its usual course.
    Step("build", "agent", persona="code_writer", capabilities="read+edit", may_change="not_tests",
         on_pass="test", routes={"test_defect": Rework("mend_tests", at_most=1, then="test")},
         smells=("lines_within_length",), on_fail=Rework("build"),
         inputs=("request", "plan", "constitution", "ideals", "test_files", "failure"),
         envelope={"summary": "text", "files_changed": "list", "verdict": "verdict", "reasons": "list"}),

    # Not on the usual path: reached only from the build. It goes on to `test`, not `red`: the build is there,
    # so a mended test is expected to pass.
    Step("mend_tests", "agent", persona="test_writer", capabilities="read+edit", may_change="tests",
         on_pass="test", smells=("tests_within_budget", "lines_within_length"), on_fail=Rework("mend_tests"),
         inputs=("request", "plan", "test_paths", "failure"),
         envelope={"summary": "text", "mended": "list"}),

    Step("test", "code", on_pass="architecture_review", checks=("tests_pass",), smells=("coverage_holds",),
         on_fail=Rework("build"),
         commit_after=True),

    # Advice, not a gate: what the architect finds goes to a backlog, and the run carries on.
    Step("architecture_review", "agent", persona="architect", capabilities="read+edit", may_change="docs",
         on_pass="document", commit_after=True, advisory=True, model="standard",
         inputs=("request", "plan", "constitution", "ideals", "diff", "docs_paths", "red_output"),
         envelope={"summary": "text", "suggestions": "list", "warnings": "list"}),

    # Documented before it is reviewed, so the reviewer judges the whole change.
    Step("document", "agent", persona="documenter", capabilities="read+edit", may_change="docs",
         on_pass="review", commit_after=True, model="light",
         inputs=("request", "plan", "diff", "docs_paths"),
         envelope={"summary": "text", "files_changed": "list"}),

    # A reply that contradicts itself (accept, with broken ideals) is asked for again.
    Step("review", "agent", persona="reviewer", on_pass="finish", on_fail=Rework("review"),
         routes={"reject": End("rejected")}, model="standard",
         inputs=("request", "run_kind", "plan", "constitution", "ideals", "diff", "test_output"),
         envelope={"verdict": "verdict", "reasons": "list", "ideals_broken": "list"}),

    Step("finish", "code", on_pass=END_ACCEPTED),
]

_plain = {entry.name: entry for entry in STEPS}


# Not part of any table: the lead is called on whenever a step asks a question.
LEAD = Step("answer_question", "agent", persona="lead", on_pass="", may_ask=False, model="light",
            inputs=("request", "constitution", "ideals", "plan", "question"),
            envelope={"answer": "text", "confident": ("yes", "no")})


# ---- the table for a codebase that uses spec kit: a persona for each of spec kit's stages ----

SPEC_KIT_STEPS: list[Step] = [
    Step("specify", "agent", persona="analyst", capabilities="read+edit", may_change="spec", on_pass="clarify",
         commit_after=True, speckit=("specify",),
         inputs=("request", "constitution", "ideals", "comment", "failure"),
         envelope={"summary": "text", "assumptions": "list"}),

    Step("clarify", "agent", persona="analyst", capabilities="read+edit", may_change="spec", on_pass="plan",
         commit_after=True, speckit=("clarify",),
         inputs=("request", "constitution", "ideals", "failure"),
         envelope={"plan": "text", "clarified": "list"}),

    replace(_plain["plan"], on_pass="tasks", on_approve=None, speckit=("plan",)),

    Step("tasks", "agent", persona="planner", capabilities="read+edit", may_change="spec", on_pass="analyze",
         commit_after=True, speckit=("tasks",),
         inputs=("request", "constitution", "ideals", "failure"),
         envelope={"summary": "text"}),

    Step("analyze", "agent", persona="reviewer", on_pass=WAIT, on_approve="baseline", revise_from="plan",
         speckit=("analyze", "checklist"),          # the one approval: spec, plan and tasks, findings as notes
         inputs=("request", "constitution", "ideals", "failure"),
         envelope={"plan": "text", "findings": "list"}),

    _plain["baseline"],
    replace(_plain["write_tests"], speckit=("implement",)),
    _plain["red"],
    replace(_plain["build"], speckit=("implement",)),
    _plain["mend_tests"],
    _plain["test"],
    _plain["architecture_review"],
    replace(_plain["document"], on_pass="converge"),

    # The scope assessment: is what was built what was approved? (FR-058, FR-059, FR-090)
    # After approval nothing returns to planning: unbuilt work goes back to the build once, and
    # everything else is recorded for the sprint review the run ends with.
    Step("converge", "agent", persona="reviewer", on_pass="retro", on_fail=Rework("converge"),
         speckit=("converge",), model="standard", ideals_stop=False,
         routes={"rework": Rework("build", at_most=2, then="retro")},      # found twice: left for the review
         inputs=("request", "plan", "constitution", "ideals", "diff", "test_output", "red_output",
                 "planning_answers"),
         envelope={"verdict": "verdict", "unbuilt": "list", "details": "list", "requirement_changes": "list",
                   "reasons": "list", "ideals_broken": "list"}),

    # Advice, like the architect's: the team's retro, about the factory, never a gate (FR-091).
    Step("retro", "agent", persona="facilitator", capabilities="read+edit", may_change="docs",
         on_pass="finish", commit_after=True, advisory=True, model="light",
         inputs=("request", "run_facts", "friction", "operator_feedback", "findings", "docs_paths", "run_name",
                 "constitution", "ideals"),
         envelope={"summary": "text", "worked": "list", "did_not": "list", "opportunities": "list",
                   "threats": "list"}),

    _plain["finish"],
]


_converge = next(entry for entry in SPEC_KIT_STEPS if entry.name == "converge")
_retro = next(entry for entry in SPEC_KIT_STEPS if entry.name == "retro")


# ---- the sprint: one plan from the codebase's standing documents, one approval, then to the end (FR-093) ----

SPRINT_STEPS: list[Step] = [
    replace(_plain["plan"], on_pass="check_plan", on_approve=None),
    # Read before the one approval: notes for the operator, never a gate (FR-095).
    # What it finds goes to the planner, who amends the plan once before the operator sees it (FR-104).
    Step("check_plan", "agent", persona="reviewer", on_pass=WAIT, on_approve="baseline", revise_from="plan",
         routes={"amend": Rework("amend_plan")},
         inputs=("request", "plan", "constitution", "ideals", "failure", "test_paths", "docs_paths",
                 "planning_answers"),
         envelope={"verdict": "verdict", "findings": "list"}),
    Step("amend_plan", "agent", persona="planner", on_pass=WAIT, on_approve="baseline", revise_from="plan",
         smells=("plan_lines_within_length",), on_fail=Rework("amend_plan"),
         inputs=("request", "plan", "plan_findings", "constitution", "ideals", "failure", "test_paths",
                 "docs_paths", "planning_answers"),
         envelope={"plan": "text", "taken": "list", "declined": "list", "ideals_addressed": "list",
                   "conflicts": "list"}),
    _plain["baseline"], _plain["write_tests"], _plain["red"], _plain["build"], _plain["mend_tests"],
    _plain["test"], _plain["architecture_review"],
    replace(_plain["document"], on_pass="converge"),
    replace(_converge, speckit=()),                    # no spec kit stage, whatever is set up
    _retro,
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
                        may_change="tests", on_pass="test", smells=("lines_within_length",),
                        inputs=("request", "plan", "test_paths", "failure"),
                        envelope={"summary": "text", "removed": "list", "kept": "list"}))

TIDY_CODE = _tidy(Step("tidy_code", "agent", persona="code_writer", capabilities="read+edit",
                       may_change="not_tests", on_pass="test", smells=("lines_within_length",),
                       inputs=("request", "plan", "constitution", "ideals", "failure"),
                       envelope={"summary": "text", "files_changed": "list"}))


# ---- the kinds of run: each one's table, without spec kit and with it ----
# What the planner and reviewer are told about each kind is in prompts/run_kinds/<kind>.md.

RUN_KINDS = {
    "change": (STEPS, SPEC_KIT_STEPS),
    "tidy-tests": (TIDY_TESTS, TIDY_TESTS),
    "tidy-code": (TIDY_CODE, TIDY_CODE),
}
TABLES = [STEPS, SPEC_KIT_STEPS, SPRINT_STEPS, TIDY_TESTS, TIDY_CODE]
CYCLES = ("auto", "sprint")


def table_for(spec_kit, run_kind, cycle="auto") -> list[Step]:
    """The steps a run goes through: chosen by its kind, its codebase's cycle, and whether it uses spec kit."""
    if run_kind not in RUN_KINDS:
        raise ValueError(f"a run is one of: {', '.join(RUN_KINDS)}; not {run_kind!r}")
    if cycle not in CYCLES:
        raise ValueError(f"a codebase's cycle is one of: {', '.join(CYCLES)}; not {cycle!r}")
    if cycle == "sprint" and run_kind == "change":
        return SPRINT_STEPS
    return RUN_KINDS[run_kind][bool(spec_kit)]
