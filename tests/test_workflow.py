"""The rules, as pure functions: the tables' properties, next_step and after_wait.

Nothing here runs an agent, a process or a database. The tables are not copied here: the
tests state what must be true of them, so a change to a table is made in one place.
"""
import ast
import pathlib

import pytest

from factory import driver, tables, workflow
from factory.workflow import (END_ACCEPTED, WAIT, CheckResult, End, Replan, Rework, Run, Step, StepResult, Wait,
                              after_wait, next_step)

LIMIT = 3
PASSED = StepResult(passed=True)


def failed(check="a_check", note="it failed", verdict=None):
    return StepResult(False, "check", CheckResult(False, note, name=check), verdict=verdict)


def step(name, table=tables.STEPS):
    return workflow.get(name, table)


def path_through(table):
    """The step names a run passes through when every step passes and every wait is approved."""
    names, at = [], table[0]
    while True:
        names.append(at.name)
        following = at.on_approve if at.on_pass == WAIT else at.on_pass
        if following == END_ACCEPTED:
            return names
        at = workflow.get(following, table)


# ---- what must be true of every table ----

@pytest.mark.fr("FR-006")
@pytest.mark.fr("FR-037")
@pytest.mark.parametrize("table", tables.TABLES, ids=["change", "spec-kit", "sprint", "tidy-tests", "tidy-code"])
def test_every_table_names_only_steps_checks_inputs_personas_and_prompts_that_exist(table):
    driver.validate(table)


@pytest.mark.fr("FR-002")
@pytest.mark.fr("FR-015")
@pytest.mark.parametrize("table, path", [
    (tables.STEPS, ["plan", "baseline", "write_tests", "red", "build", "test", "architecture_review",
                      "document", "review", "finish"]),
    (tables.TIDY_TESTS, ["plan", "baseline", "tidy_tests", "test", "review", "finish"]),
    (tables.TIDY_CODE, ["plan", "baseline", "tidy_code", "test", "review", "finish"]),
])
def test_a_run_that_passes_every_step_goes_this_way(table, path):
    assert path_through(table) == path


@pytest.mark.fr("FR-043")
@pytest.mark.fr("FR-044")
@pytest.mark.fr("FR-050")
@pytest.mark.fr("FR-051")
def test_the_roles_are_kept_apart():
    by_persona = {s.name: s.persona for s in tables.STEPS}
    assert len({by_persona["write_tests"], by_persona["build"], by_persona["review"]}) == 3
    for table in tables.TABLES:
        for judge in (s for s in table if s.routes):
            assert (judge.capabilities, judge.may_change) == ("read", "nothing")     # a judge changes nothing
    assert [s.name for s in tables.STEPS if s.advisory] == ["architecture_review"]
    assert not any(s.speckit for s in tables.STEPS)          # the plain cycle names no spec kit command
    assert all(s.inputs == () and s.envelope == {} for t in tables.TABLES for s in t if s.kind == "code")


@pytest.mark.fr("FR-066")
@pytest.mark.parametrize("table, tidy, scope", [(tables.TIDY_TESTS, "tidy_tests", "tests"),
                                                (tables.TIDY_CODE, "tidy_code", "not_tests")])
def test_a_tidy_needs_no_failing_test_and_holds_one_side_still(table, tidy, scope):
    assert step(tidy, table).may_change == scope
    assert step("test", table).on_fail == Rework(tidy)                       # the tests must pass after
    assert step("review", table).routes == {"reject": Rework(tidy)}          # a rejection guides another try
    assert tables.table_for(True, "tidy-tests") is tables.TIDY_TESTS     # the same on a spec kit codebase
    with pytest.raises(ValueError, match="tidy-tests"):
        tables.table_for(False, "rewrite-everything")


@pytest.mark.fr("FR-037")
@pytest.mark.parametrize("entry, problem", [
    (dict(name="a", kind="code", on_pass=WAIT), "approval leads"),
    (dict(name="a", kind="agent", persona="p", on_pass="b", routes={"no": End("rejected")}), "judging"),
    (dict(name="a", kind="agent", on_pass="b"), "persona"),
    (dict(name="a", kind="code", on_pass="b", may_change="everything"), "may_change"),
])
def test_an_unsound_entry_is_refused_when_it_is_written(entry, problem):
    with pytest.raises(ValueError, match=problem):
        Step(**entry)


@pytest.mark.fr("FR-037")
def test_a_table_naming_what_does_not_exist_is_refused_before_a_run_uses_it():
    broken = [Step("a", "code", on_pass="nowhere", checks=("no_such_check",)),
              Step("b", "agent", persona="nobody", on_pass="a", inputs=("no_such_input",))]
    with pytest.raises(ValueError) as refused:
        driver.validate(broken)
    for named in ("nowhere", "no_such_check", "no_such_input", "nobody", "no prompt file"):
        assert named in str(refused.value)


@pytest.mark.parametrize("make, problem", [(lambda: End("finished"), "accepted"),
                                           (lambda: StepResult(False, "oops"), "question")])
@pytest.mark.fr("FR-016")
def test_an_outcome_or_failure_outside_the_vocabulary_is_refused(make, problem):
    with pytest.raises(ValueError, match=problem):
        make()


# ---- what happens next: one table of cases over next_step ----

def ended(outcome, *words):
    return ("ended", outcome, words)


def follows(got, expected):
    """`got` is `expected`; or, for ended(...), an End with that outcome whose reason has those words."""
    if not isinstance(expected, tuple):
        return got == expected
    _, outcome, words = expected
    return isinstance(got, End) and got.outcome == outcome and bool(got.reason) and all(w in got.reason for w in words)


NEXT = [
    # (step, how it went, attempts so far, what follows)                                 requirement
    ("plan", PASSED, {}, Wait()),                                                         # FR-002
    ("build", PASSED, {}, Run("test")),                                                   # FR-015
    ("finish", PASSED, {}, ended("accepted")),                                            # FR-015
    ("baseline", failed("baseline", "already failing"), {}, ended("needs-me", "baseline", "already failing")),
    ("write_tests", failed("edge_cases_stated"), {"write_tests": 1}, Run("write_tests")),  # FR-045
    ("red", failed("tests_fail_first"), {"write_tests": 1}, Run("write_tests")),          # FR-007
    ("test", failed("tests_pass"), {"build": 1}, Run("build")),                           # FR-010
    ("test", failed("tests_pass", "test_hello"), {"build": LIMIT},                        # FR-011
     ended("needs-me", "build", "3", "test_hello")),
    ("review", failed("verdict", "no heading", verdict="reject"), {}, ended("rejected", "no heading")),   # FR-012
    ("review", failed("verdict", "accept, but broken", verdict="accept"), {"review": 1}, Run("review")),
    ("plan", StepResult(False, "malformed", CheckResult(False, "no `plan`")), {"plan": 1}, Run("plan")),
    ("plan", StepResult(False, "malformed", CheckResult(False, "no `plan`")), {"plan": LIMIT},
     ended("needs-me", "plan", "no `plan`")),
    ("build", StepResult(False, "timeout", message="900 seconds"), {}, ended("needs-me", "build", "900 seconds")),
    ("build", StepResult(False, "error", message="usage limit"), {}, ended("needs-me", "usage limit")),   # FR-016
    ("build", StepResult(False, "guard", CheckResult(False, "it changed: tests/x.py")), {},                # FR-032
     ended("needs-me", "build", "tests/x.py")),
    ("architecture_review", StepResult(False, "error", message="x"), {}, Run("document")),               # FR-049
    ("architecture_review", failed(), {}, Run("document")),                                             # FR-050
    ("architecture_review", StepResult(False, "guard", CheckResult(False, "it changed: viewer.py")), {},
     ended("needs-me", "viewer.py")),
]


@pytest.mark.fr("FR-002")
@pytest.mark.fr("FR-007")
@pytest.mark.fr("FR-010")
@pytest.mark.fr("FR-011")
@pytest.mark.fr("FR-012")
@pytest.mark.fr("FR-014")
@pytest.mark.fr("FR-015")
@pytest.mark.fr("FR-016")
@pytest.mark.fr("FR-032")
@pytest.mark.fr("FR-045")
@pytest.mark.fr("FR-049")
@pytest.mark.fr("FR-050")
@pytest.mark.parametrize("name, result, attempts, expected", NEXT)
def test_what_follows_a_step(name, result, attempts, expected):
    got = next_step(step(name), result, attempts, LIMIT)
    assert follows(got, expected), got


@pytest.mark.fr("FR-057")
@pytest.mark.fr("FR-059")
@pytest.mark.parametrize("verdict, attempts, expected", [
    ("rework", {}, Run("build")),
    ("rework", {"build": 2}, Run("retro")),                   # unbuilt work goes back once, then is a deviation
])
def test_a_judging_steps_verdict_chooses_its_route(verdict, attempts, expected):
    got = next_step(step("converge", tables.SPEC_KIT_STEPS), failed("verdict", "why", verdict), attempts, LIMIT)
    assert follows(got, expected), got


@pytest.mark.fr("FR-055")
def test_a_codebase_that_uses_spec_kit_gets_a_stage_for_each_spec_kit_command():
    assert tables.table_for(False, "change") is tables.STEPS
    assert tables.table_for(True, "change") is tables.SPEC_KIT_STEPS
    assert [s.name for s in tables.SPEC_KIT_STEPS][:5] == ["specify", "clarify", "plan", "tasks", "analyze"]


@pytest.mark.fr("FR-003")
def test_the_operators_three_decisions():
    plan = step("plan")
    assert after_wait("approve", plan) == Run("baseline")
    assert after_wait("revise", plan) == Run("plan")
    assert after_wait("abandon", plan) == End("rejected", "abandoned by operator")
    with pytest.raises(ValueError):
        after_wait("postpone", plan)


@pytest.mark.fr("FR-038")
def test_the_rules_live_in_one_place_and_do_no_input_or_output():
    package = pathlib.Path(workflow.__file__).parent
    for file in package.glob("*.py"):
        defined = {node.name for node in ast.walk(ast.parse(file.read_text())) if isinstance(node, ast.FunctionDef)}
        if file.name != "workflow.py":
            assert not defined & {"next_step", "after_wait"}, f"{file.name} defines a rule function"
    for file, allowed in (("workflow.py", {"dataclasses", "pathlib"}), ("tables.py", {"dataclasses", "factory.workflow"})):
        tree = ast.parse((package / file).read_text())
        imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imported |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert imported <= allowed, f"{file} must import nothing that does input or output: {imported - allowed}"


@pytest.mark.fr("FR-014")
@pytest.mark.fr("FR-016")
@pytest.mark.fr("FR-032")
@pytest.mark.parametrize("reply, failure, said", [
    (dict(timed_out=True), "timeout", "900 seconds"),
    (dict(ok=False, error="usage limit reached"), "error", "usage limit reached"),
    (dict(denials=[{"path": "/work/run/app.py"}]), "error", "/work/run/app.py"),   # retrying cannot help
    (dict(denials=[{"path": "/home/op/.ssh/id"}]), None, ""),     # outside the checkout: the guard working
    (dict(), None, ""),
])
def test_how_the_agent_programs_reply_went(reply, failure, said):
    from types import SimpleNamespace
    reply = SimpleNamespace(**{"timed_out": False, "ok": True, "error": None, "denials": [], **reply})
    result = workflow.reply_failure(reply, "/work/run", 900)
    assert result.failure == failure and said in result.message


@pytest.mark.fr("FR-066")
@pytest.mark.parametrize("run_kind, told", [("change", "fail before it is built"),
                                            ("tidy-tests", "The code is held still"),
                                            ("tidy-code", "The tests are held still")])
def test_the_planner_and_reviewer_are_told_what_kind_of_run_it_is(run_kind, told):
    from factory import config
    assert told in (config.PROMPTS_DIR / "run_kinds" / f"{run_kind}.md").read_text()
    for table in tables.RUN_KINDS[run_kind]:
        for step in (s for s in table if s.name in ("plan", "review")):
            assert "run_kind" in step.inputs, f"{run_kind}: {step.name} is not told"

