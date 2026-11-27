"""Control: the tables. Which steps a run goes through, in what order, for each kind of run.

Each table is data: a list of step entries, whose shape and rules are in workflow.py. To
change what the factory does, change a table. Nothing here reads or writes anything.
"""
from dataclasses import replace

from factory.workflow import (DEFECTIVE_TESTS, EFFORTS, END_ACCEPTED, END_AS_FOUND, FOUND, GRADES, End, Replan, Rework,
                              Step, WAIT)

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
         inputs=("request", "plan", "built_on", "test_paths", "limits", "failure"),
         envelope={"summary": "text", "test_files": "list", "edge_cases": "list"}),

    Step("red", "code", on_pass="build", checks=("tests_fail_first",), on_fail=Rework("write_tests"),
         commit_after=True),

    # The builder may not touch a test. One it finds no build can pass goes to the test writer (FR-097): once for
    # each test no earlier report named, and twice in a run at most (FR-150). A report naming only tests reported
    # before is not chased: the tests are run and the failure takes its usual course.
    Step("build", "agent", persona="code_writer", capabilities="read+edit", may_change="not_tests",
         on_pass="test", routes={"test_defect": Rework("mend_tests", at_most=2, then="test", once_per_test=True)},
         smells=("lines_within_length", "readable"), on_fail=Rework("build"),
         inputs=("request", "plan", "built_on", "constitution", "ideals", "test_files", "limits", "failure"),
         envelope={"summary": "text", "files_changed": "list", "verdict": "verdict", "reasons": "list",
                   DEFECTIVE_TESTS: "list"}),

    # Not on the usual path: reached only from the build. It goes on to `test`, not `red`: the build is there,
    # so a mended test is expected to pass.
    Step("mend_tests", "agent", persona="test_writer", capabilities="read+edit", may_change="tests",
         on_pass="test", smells=("tests_within_budget", "lines_within_length"), on_fail=Rework("mend_tests"),
         inputs=("request", "plan", "test_paths", "limits", "failure", "defective_tests", "failing_tests"),
         envelope={"summary": "text", "mended": "list"}),

    Step("test", "code", on_pass="architecture_review", checks=("tests_pass",), smells=("coverage_holds",),
         on_fail=Rework("build"),
         commit_after=True),

    # Advice, not a gate: what the architect finds goes to a backlog, and the run carries on. It judges the functions
    # the readability smell flagged (FR-149).
    Step("architecture_review", "agent", persona="architect", capabilities="read+edit", may_change="docs",
         on_pass="document", commit_after=True, advisory=True, model="standard",
         inputs=("request", "plan", "constitution", "ideals", "diff", "docs_paths", "red_output", "backlog_file",
                 "backlog_done_file", "run_name", "readability"),
         envelope={"summary": "text", "suggestions": "list", "warnings": "list"}),

    # Documented before it is reviewed, so the reviewer judges the whole change.
    # Given what the factory measured, so it claims nothing about tests, budget or coverage it was not (FR-136).
    # The backlog is the architect's alone: it sees what the change answered and closes it (FR-144).
    Step("document", "agent", persona="documenter", capabilities="read+edit", may_change="docs_but_backlog",
         on_pass="review", commit_after=True, model="light",
         inputs=("request", "plan", "diff", "docs_paths", "measured", "backlog_file", "backlog_done_file"),
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

# Not part of any table either: after a round, questions from different agents that ask the same thing are merged,
# so the asker answers each once (FR-132). Advice: if it fails, the batches go to the asker as they were asked.
# The middle grade: telling one decision asked three ways from two that only look alike is judgment (FR-151).
MERGE = Step("merge_questions", "agent", persona="facilitator", on_pass="", may_ask=False, model="middle",
             advisory=True, inputs=("to_merge",), envelope={"merged": "list"})


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
         inputs=("request", "run_facts", "measured", "friction", "operator_feedback", "asked", "findings",
                 "docs_paths", "run_name", "constitution", "ideals"),
         envelope={"summary": "text", "worked": "list", "did_not": "list", "refinement": "list",
                   "opportunities": "list", "threats": "list"}),

    _plain["finish"],
]


_converge = next(entry for entry in SPEC_KIT_STEPS if entry.name == "converge")
_retro = next(entry for entry in SPEC_KIT_STEPS if entry.name == "retro")


# ---- a planning dialogue: from an ask to an agreed plan, with the asker (FR-119 to FR-126) ----
# Each round every speaker speaks, in this order, each with its own batch for the asker: questions, measurements,
# and (the architect and the plan check) points for the planner, on its plan of this round: blocking, which holds
# alignment open, and notes, which never do (FR-130). The round's end is the one wait: for the asker's answers, or
# for agreement to the plan the planner proposed aligned; then approval.

# Each question goes with why no ruling in the standing documents settles it, which the asker sees (FR-156).
_SPEAKS = {"questions": "list", "measure": "list", "rulings_checked": "list"}
_POINTS = {"blocking": "list", "notes": "list"}
_HEARS = ("request", "run_kind", "round", "dialogue", "standing", "built_on", "constitution", "ideals",
          "failure")


def _speaker(name, persona, on_pass, inputs=(), envelope=None, checks=(), **entry) -> Step:
    return Step(name, "agent", persona=persona, on_pass=on_pass, dialogue=True, may_ask=False, on_fail=Rework(name),
                inputs=(*_HEARS, *inputs), checks=(*checks, "rulings_checked"), **entry,
                envelope={**_SPEAKS, **(_POINTS if envelope is None else envelope)})


DIALOGUE = [
    _speaker("dialogue_analyst", "analyst", "dialogue_planner", envelope={}),
    # It proposes aligned with the plan and an estimate, or asks something: its own check holds it to one (FR-122).
    _speaker("dialogue_planner", "planner", "dialogue_architect", checks=("dialogue_moves",),
             smells=("plan_lines_within_length",),
             inputs=("draft", "similar_runs", "test_paths", "docs_paths"),
             envelope={"aligned": ("yes", "no"), "how_much": "text", "plan": "text", "estimate": "text",
                       "declined": "list", "ideals_addressed": "list", "conflicts": "list"}),
    _speaker("dialogue_architect", "architect", "dialogue_check", inputs=("draft", "docs_paths")),
    _speaker("dialogue_check", "reviewer", WAIT, inputs=("draft", "test_paths", "docs_paths"),
             on_approve="baseline", on_moved="recheck_plan", revise_from="dialogue_analyst"),
    # Approved after the codebase moved: the plan is read against it as it is now; stale, back to the dialogue.
    Step("recheck_plan", "agent", persona="reviewer", on_pass="baseline", on_fail=Rework("recheck_plan"),
         routes={"stale": Replan("dialogue_analyst")},
         inputs=("request", "plan", "codebase_moved", "constitution", "ideals", "test_paths", "docs_paths",
                 "failure"),
         envelope={"verdict": "verdict", "findings": "list"}),
]


# ---- the sprint: a dialogue from the codebase's standing documents, one approval, then to the end (FR-093) ----

SPRINT_STEPS: list[Step] = [
    *DIALOGUE,
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

def _tidy(step: Step, planning=(_plain["plan"],)) -> list[Step]:
    return [*planning, replace(_plain["baseline"], on_pass=step.name), step,
            replace(_plain["test"], on_pass="review", on_fail=Rework(step.name)),
            replace(_plain["review"], routes={"reject": Rework(step.name)}),    # a rejection guides another try
            _plain["finish"]]


_tidy_tests = Step("tidy_tests", "agent", persona="test_writer", capabilities="read+edit", may_change="tests",
                   on_pass="test", smells=("lines_within_length",),
                   inputs=("request", "plan", "test_paths", "limits", "failure"),
                   envelope={"summary": "text", "removed": "list", "kept": "list"})
_tidy_code = Step("tidy_code", "agent", persona="code_writer", capabilities="read+edit", may_change="not_tests",
                  on_pass="test", smells=("lines_within_length", "readable"),
                  inputs=("request", "plan", "constitution", "ideals", "limits", "failure"),
                  envelope={"summary": "text", "files_changed": "list"})
TIDY_TESTS, TIDY_CODE = _tidy(_tidy_tests), _tidy(_tidy_code)
# On a sprint codebase a tidy is planned in the dialogue too; the agents say how little it needs (FR-126).
SPRINT_TIDY_TESTS, SPRINT_TIDY_CODE = _tidy(_tidy_tests, DIALOGUE), _tidy(_tidy_code, DIALOGUE)


# ---- a spike: a run whose product is an answer, not a change (FR-113 to FR-118) ----
# No wait for approval: the orchestrator shows the operator the question before it starts. None of the change
# cycle's gates: no test that fails first, no test budget or line length, no architect, no documenter. The probe
# is on the spike's own branch, which is never merged; the run ends answered or inconclusive, as its findings say.

SPIKE = "spike"

SPIKE_STEPS: list[Step] = [
    Step("spike_plan", "agent", persona="spike", on_pass="probe",
         inputs=("request", "run_kind", "constitution", "ideals", "failure", "test_paths", "probe_command"),
         envelope={"plan": "text", "question": "text", "guess": "text", "yes": "text", "no": "text",
                   "cannot_tell": "text"}),

    # Committed as soon as it is written, so the probe is on the branch whatever happens to it next.
    Step("probe", "agent", persona="spike", capabilities="read+edit", may_change="checkout", on_pass="run_probe",
         commit_after=True,
         inputs=("request", "plan", "test_paths", "probe_command", "failure"),
         envelope={"summary": "text", "probe_file": "text", "files_changed": "list"}),

    # The factory runs the probe; no agent runs anything (FR-114). One that cannot run is mended once.
    Step("run_probe", "code", on_pass="write_findings", checks=("probe_ran",),
         on_fail=Rework("probe", at_most=2, then=End("inconclusive", "the probe could not be run, mended once"))),

    # The note is checked to quote only what is on the branch and what the probe printed (FR-115).
    Step("write_findings", "agent", persona="spike", capabilities="read+edit", may_change="docs", on_pass="spike_retro",
         checks=("findings_quoted",), commit_after=True,
         on_fail=Rework("write_findings", at_most=2, then=End("inconclusive", "the findings note was sent back twice")),
         inputs=("request", "plan", "diff", "probe_output", "failure", "docs_paths", "run_name", "branch"),
         envelope={"summary": "text", "outcome": FOUND, "reason": "text"}),

    # Advice, never a gate: was the question answered for what it cost (FR-118).
    Step("spike_retro", "agent", persona="facilitator", capabilities="read+edit", may_change="docs",
         on_pass="finish", commit_after=True, advisory=True, model="light",
         inputs=("request", "run_facts", "spike_answer", "friction", "operator_feedback", "docs_paths", "run_name"),
         envelope={"summary": "text"}),

    Step("finish", "code", on_pass=END_AS_FOUND),
]


# ---- the kinds of run: each one's table, without spec kit and with it ----
# What the planner and reviewer are told about each kind is in prompts/run_kinds/<kind>.md.

RUN_KINDS = {
    "change": (STEPS, SPEC_KIT_STEPS),
    "tidy-tests": (TIDY_TESTS, TIDY_TESTS),
    "tidy-code": (TIDY_CODE, TIDY_CODE),
    SPIKE: (SPIKE_STEPS, SPIKE_STEPS),
}
SPRINT = {"change": SPRINT_STEPS, "tidy-tests": SPRINT_TIDY_TESTS, "tidy-code": SPRINT_TIDY_CODE}    # FR-119
TABLES = [STEPS, SPEC_KIT_STEPS, SPRINT_STEPS, TIDY_TESTS, TIDY_CODE, SPIKE_STEPS, SPRINT_TIDY_TESTS, SPRINT_TIDY_CODE]
CYCLES = ("auto", "sprint")


# ---- for showing a run's progress: which part of the cycle each step is in (FR-145) ----
# The operator's waits are the fourth group, "waiting"; they are stages, not steps, so they are not listed here.

STAGE_GROUPS = {
    "planning": ("plan", "specify", "clarify", "tasks", "analyze", "dialogue_analyst", "dialogue_planner",
                 "dialogue_architect", "dialogue_check", "recheck_plan", "spike_plan"),
    "building": ("baseline", "write_tests", "red", "build", "mend_tests", "test", "tidy_tests", "tidy_code", "probe",
                 "run_probe"),
    "reviewing": ("architecture_review", "document", "review", "converge", "retro", "write_findings", "spike_retro",
                  "finish"),
}


def group_of(name) -> str:
    """The group a step's stage is shown in (FR-145)."""
    return next(group for group, names in STAGE_GROUPS.items() if name in names)


# What a project's [steps.<name>] may set (FR-112). Nothing here changes what passing means: not the checks, the
# persona, the prompt, the inputs, where a step may write, its capabilities or where it leads.
OVERRIDABLE = ("model", "effort", "timeout", "smells", "rework_at_most")


def overridden(table, overrides) -> list[Step]:
    """`table` with a project's per-step overrides applied (FR-112). Refuses, naming it, a step not in the table, a
    field not overridable, or a value of the wrong kind; a smell that is not registered is refused by `validate`."""
    names = {step.name for step in table}
    problems = [f"[steps.{name}]: there is no step {name} in this run's table ({', '.join(sorted(names))})"
                for name in overrides if name not in names]
    result = []
    for step in table:
        given = overrides.get(step.name) or {}
        problems += [f"[steps.{step.name}]: {key} cannot be set; a project may set {', '.join(OVERRIDABLE)}"
                     for key in given if key not in OVERRIDABLE]
        changes = {}
        if "model" in given:
            if given["model"] not in GRADES or step.kind != "agent":
                problems.append(f"[steps.{step.name}]: model must be one of {', '.join(GRADES)}, on an agent step")
            else:
                changes["model"] = given["model"]
        if "effort" in given:
            if given["effort"] not in EFFORTS or step.kind != "agent":
                problems.append(f"[steps.{step.name}]: effort must be one of {', '.join(EFFORTS)}, on an agent step")
            else:
                changes["effort"] = given["effort"]
        if "timeout" in given:
            if not isinstance(given["timeout"], int) or isinstance(given["timeout"], bool) or given["timeout"] < 1:
                problems.append(f"[steps.{step.name}]: timeout must be a whole number of seconds")
            else:
                changes["timeout"] = given["timeout"]
        if "smells" in given:
            if not isinstance(given["smells"], list) or not all(isinstance(s, str) for s in given["smells"]):
                problems.append(f"[steps.{step.name}]: smells must be a list of check names")
            else:
                changes["smells"] = tuple(dict.fromkeys([*step.smells, *given["smells"]]))     # added, never removed
        if "rework_at_most" in given:
            capped = {verdict: route for verdict, route in step.routes.items()
                      if isinstance(route, Rework) and route.at_most is not None}
            value = given["rework_at_most"]
            if not capped:
                problems.append(f"[steps.{step.name}]: rework_at_most needs a capped rework route; it has none")
            elif not isinstance(value, int) or isinstance(value, bool) or value < 1:
                problems.append(f"[steps.{step.name}]: rework_at_most must be a whole number, at least 1")
            else:
                changes["routes"] = {**step.routes, **{v: replace(r, at_most=value) for v, r in capped.items()}}
        result.append(replace(step, **changes) if changes else step)
    if problems:
        raise ValueError("this codebase's .factory.toml: " + "; ".join(problems))
    return result


def table_for(spec_kit, run_kind, cycle="auto") -> list[Step]:
    """The steps a run goes through: chosen by its kind, its codebase's cycle, and whether it uses spec kit.
    A sprint codebase plans a change or a tidy in a dialogue (FR-119); a spike is the same whatever it says."""
    if run_kind not in RUN_KINDS:
        raise ValueError(f"a run is one of: {', '.join(RUN_KINDS)}; not {run_kind!r}")
    if cycle not in CYCLES:
        raise ValueError(f"a codebase's cycle is one of: {', '.join(CYCLES)}; not {cycle!r}")
    if cycle == "sprint" and run_kind in SPRINT:
        return SPRINT[run_kind]
    return RUN_KINDS[run_kind][bool(spec_kit)]
