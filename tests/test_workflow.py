"""The rules, as pure functions: the step table, next_step and after_wait.

Nothing here runs an agent, a process or a database. If these pass, the decision logic
in contracts/workflow.md is what factory/workflow.py does.
"""
import ast
import pathlib

import pytest

from factory import workflow
from factory.checks import CheckResult
from factory.workflow import END_ACCEPTED, WAIT, End, Rework, Run, Step, StepResult, Wait, after_wait, next_step

PASSED = StepResult(passed=True)
LIMIT = 3


def step(name):
    return workflow.get(name)


def failed(check, note="it failed"):
    return StepResult(False, "check", CheckResult(check, False, note))


# name, kind, persona, capabilities, may_change, checks, on_pass, on_fail, commit_after
TABLE = [
    ("plan", "agent", "planner", "read+edit", "spec", (), WAIT, End("needs-me"), True),
    ("baseline", "code", None, "read", "nothing", ("baseline",), "write_tests", End("needs-me"), False),
    ("write_tests", "agent", "test_writer", "read+edit", "tests",
     ("tests_added", "tests_within_budget", "edge_cases_stated"), "red", Rework("write_tests"), False),
    ("red", "code", None, "read", "nothing", ("tests_fail_first",), "build", Rework("write_tests"), True),
    ("build", "agent", "code_writer", "read+edit", "not_tests", (), "test", End("needs-me"), False),
    ("test", "code", None, "read", "nothing", ("tests_pass",), "architecture_review", Rework("build"), True),
    ("architecture_review", "agent", "architect", "read+edit", "docs", (), "document", End("needs-me"), True),
    ("document", "agent", "documenter", "read+edit", "docs", (), "review", End("needs-me"), True),
    ("review", "agent", "reviewer", "read", "nothing", ("verdict_accept",), "finish", End("rejected"), False),
    ("finish", "code", None, "read", "nothing", (), END_ACCEPTED, End("needs-me"), False),
]


@pytest.mark.fr("FR-002")
@pytest.mark.fr("FR-006")
def test_the_step_table_matches_the_contract_row_for_row():
    actual = [(s.name, s.kind, s.persona, s.capabilities, s.may_change, s.checks, s.on_pass, s.on_fail,
               s.commit_after) for s in workflow.STEPS]
    assert actual == TABLE


@pytest.mark.fr("FR-006")
def test_inputs_and_envelopes_match_the_contract():
    assert {s.name: s.inputs for s in workflow.STEPS if s.kind == "agent"} == {
        "plan": ("request", "constitution", "ideals", "previous_plan", "comment", "failure",
                 "speckit_instructions", "speckit_context"),
        "write_tests": ("request", "plan", "test_paths", "failure", "speckit_instructions", "speckit_context"),
        "build": ("request", "plan", "constitution", "ideals", "test_files", "failure", "speckit_instructions",
                  "speckit_context"),
        "review": ("request", "plan", "constitution", "ideals", "diff", "test_output"),
        "architecture_review": ("request", "plan", "constitution", "ideals", "diff", "docs_paths"),
        "document": ("request", "plan", "diff", "docs_paths"),
    }
    assert {s.name: s.envelope for s in workflow.STEPS if s.kind == "agent"} == {
        "plan": {"plan": "text", "ideals_addressed": "list", "conflicts": "list"},
        "write_tests": {"summary": "text", "test_files": "list", "edge_cases": "list"},
        "build": {"summary": "text", "files_changed": "list"},
        "review": {"verdict": "verdict", "reasons": "list", "ideals_broken": "list"},
        "architecture_review": {"summary": "text", "suggestions": "list", "warnings": "list"},
        "document": {"summary": "text", "files_changed": "list"},
    }
    assert all(s.inputs == () and s.envelope == {} for s in workflow.STEPS if s.kind == "code")
    with pytest.raises(LookupError, match="no_such_step"):
        workflow.get("no_such_step")


@pytest.mark.fr("FR-043")
@pytest.mark.fr("FR-044")
def test_tests_code_and_review_are_done_by_different_personas():
    assert step("write_tests").persona != step("build").persona
    assert step("review").persona != step("build").persona
    assert step("review").capabilities == "read" and step("review").may_change == "nothing"


@pytest.mark.fr("FR-002")
def test_a_passing_plan_waits_for_the_operator():
    assert next_step(step("plan"), PASSED, {"plan": 1}, LIMIT) == Wait()


@pytest.mark.fr("FR-003")
def test_the_operators_three_decisions():
    assert after_wait("approve", step("plan")) == Run("baseline")
    assert after_wait("revise", step("plan")) == Run("plan")
    assert after_wait("abandon", step("plan")) == End("rejected", "abandoned by operator")
    with pytest.raises(ValueError):
        after_wait("postpone", step("plan"))


@pytest.mark.fr("FR-015")
@pytest.mark.parametrize("name, expected", [
    ("baseline", Run("write_tests")), ("write_tests", Run("red")), ("red", Run("build")),
    ("build", Run("test")), ("test", Run("architecture_review")), ("architecture_review", Run("document")),
    ("document", Run("review")),
    ("review", Run("finish")),
])
def test_a_passing_step_leads_to_its_on_pass(name, expected):
    assert next_step(step(name), PASSED, {name: 1}, LIMIT) == expected


@pytest.mark.fr("FR-015")
def test_a_passing_finish_ends_the_run_accepted():
    result = next_step(step("finish"), PASSED, {}, LIMIT)
    assert isinstance(result, End) and result.outcome == "accepted" and result.reason


@pytest.mark.fr("FR-016")
def test_a_failing_baseline_ends_needs_me():
    result = next_step(step("baseline"), failed("baseline", "2 failed"), {"baseline": 1}, LIMIT)
    assert result.outcome == "needs-me" and "baseline" in result.reason and "2 failed" in result.reason


@pytest.mark.fr("FR-045")
@pytest.mark.parametrize("check", ["tests_added", "edge_cases_stated"])
def test_tests_without_edge_cases_or_without_test_files_go_round_again(check):
    assert next_step(step("write_tests"), failed(check), {"write_tests": 1}, LIMIT) == Run("write_tests")


@pytest.mark.fr("FR-007")
def test_tests_that_do_not_fail_first_send_the_test_writer_round_again():
    assert next_step(step("red"), failed("tests_fail_first"), {"write_tests": 1, "red": 1}, LIMIT) == Run("write_tests")


@pytest.mark.fr("FR-010")
def test_failing_tests_send_the_failure_back_to_build():
    assert next_step(step("test"), failed("tests_pass"), {"build": 2, "test": 2}, LIMIT) == Run("build")


@pytest.mark.fr("FR-012")
def test_a_rejecting_review_ends_the_run_rejected_with_its_reasons():
    result = next_step(step("review"), failed("verdict_accept", "the page has no heading"), {"review": 1}, LIMIT)
    assert result == End("rejected", "the page has no heading")


@pytest.mark.fr("FR-011")
@pytest.mark.parametrize("name, check, target", [
    ("test", "tests_pass", "build"), ("red", "tests_fail_first", "write_tests"),
    ("write_tests", "edge_cases_stated", "write_tests"),
])
def test_a_rework_at_the_attempt_limit_ends_needs_me(name, check, target):
    result = next_step(step(name), failed(check, "1 failed: test_hello"), {target: LIMIT, name: LIMIT}, LIMIT)
    assert result.outcome == "needs-me"
    assert target in result.reason and "3" in result.reason and "test_hello" in result.reason
    under = next_step(step(name), failed(check), {target: LIMIT - 1}, LIMIT)
    assert under == Run(target)


@pytest.mark.fr("FR-011")
def test_a_malformed_envelope_reworks_the_same_step_until_the_limit():
    malformed = StepResult(False, "malformed", CheckResult("envelope_valid", False, "the envelope has no `plan`"))
    for name in ("plan", "build", "review"):
        assert next_step(step(name), malformed, {name: 1}, LIMIT) == Run(name)
        ended = next_step(step(name), malformed, {name: LIMIT}, LIMIT)
        assert ended.outcome == "needs-me" and name in ended.reason and "no `plan`" in ended.reason


@pytest.mark.fr("FR-014")
def test_a_timeout_ends_needs_me_naming_the_step_and_the_limit():
    result = next_step(step("build"), StepResult(False, "timeout", message="900 seconds"), {"build": 1}, LIMIT)
    assert result.outcome == "needs-me" and "build" in result.reason and "900 seconds" in result.reason


@pytest.mark.fr("FR-016")
def test_an_agent_error_ends_needs_me_carrying_the_message():
    result = next_step(step("build"), StepResult(False, "error", message="usage limit reached"), {"build": 1}, LIMIT)
    assert result.outcome == "needs-me" and "usage limit reached" in result.reason


@pytest.mark.fr("FR-032")
def test_a_guard_failure_ends_needs_me_naming_the_files():
    guard = StepResult(False, "guard", CheckResult("changes_allowed", False, "it changed: tests/test_x.py"))
    result = next_step(step("build"), guard, {"build": 1}, LIMIT)
    assert result.outcome == "needs-me" and "tests/test_x.py" in result.reason and "build" in result.reason


@pytest.mark.fr("FR-037")
def test_the_functions_read_whatever_table_they_are_given():
    extra = [Step("a", "code", on_pass="b", checks=("x",), on_fail=Rework("a")),
             Step("b", "agent", persona="p", on_pass=WAIT),
             Step("c", "code", on_pass=END_ACCEPTED)]
    assert workflow.get("b", extra).persona == "p"
    assert next_step(extra[0], PASSED, {}, 2) == Run("b")
    assert next_step(extra[0], failed("x"), {"a": 1}, 2) == Run("a")
    assert next_step(extra[0], failed("x"), {"a": 2}, 2).outcome == "needs-me"
    assert next_step(extra[1], PASSED, {}, 2) == Wait()
    assert after_wait("approve", extra[1], extra) == Run("c")
    assert next_step(extra[2], PASSED, {}, 2).outcome == "accepted"


@pytest.mark.fr("FR-038")
def test_the_rules_live_in_one_place_and_do_no_input_or_output():
    package = pathlib.Path(workflow.__file__).parent
    for file in package.glob("*.py"):
        defined = {node.name for node in ast.walk(ast.parse(file.read_text()))
                   if isinstance(node, ast.FunctionDef)}
        if file.name != "workflow.py":
            assert not defined & {"next_step", "after_wait"}, f"{file.name} defines a rule function"
    tree = ast.parse((package / "workflow.py").read_text())
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)
                for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) and node.module}
    assert imported <= {"dataclasses"}, f"workflow.py must import nothing that does input or output: {imported}"


@pytest.mark.fr("FR-050")
def test_the_architecture_review_is_advisory_and_no_other_step_is():
    assert [s.name for s in workflow.STEPS if s.advisory] == ["architecture_review"]
    assert Step("x", "code", on_pass="y").advisory is False


@pytest.mark.fr("FR-050")
@pytest.mark.fr("FR-049")
@pytest.mark.parametrize("result", [
    StepResult(False, "malformed", CheckResult("envelope_valid", False, "no JSON")),
    StepResult(False, "timeout", message="900 seconds"),
    StepResult(False, "error", message="usage limit reached"),
    StepResult(False, "check", CheckResult("some_check", False, "no")),
])
def test_a_failed_advisory_step_does_not_stop_the_run(result):
    architect = step("architecture_review")
    assert next_step(architect, result, {"architecture_review": 1}, LIMIT) == Run("document")
    assert next_step(architect, PASSED, {"architecture_review": 1}, LIMIT) == Run("document")


@pytest.mark.fr("FR-050")
@pytest.mark.fr("FR-032")
def test_an_advisory_step_that_changes_what_it_may_not_still_stops_the_run():
    guard = StepResult(False, "guard", CheckResult("changes_allowed", False, "it changed: viewer.py"))
    ended = next_step(step("architecture_review"), guard, {"architecture_review": 1}, LIMIT)
    assert ended.outcome == "needs-me" and "viewer.py" in ended.reason


@pytest.mark.fr("FR-051")
def test_the_plain_cycle_names_no_spec_kit_command():
    assert {s.name: s.speckit for s in workflow.STEPS if s.speckit} == {}       # the plain cycle uses none
    assert Step("x", "code", on_pass="y").speckit == ()


@pytest.mark.fr("FR-066")
def test_a_tidy_run_has_no_failing_tests_first_step_and_holds_one_side_still():
    tests, code = workflow.table_for(False, "tidy-tests"), workflow.table_for(False, "tidy-code")
    assert [s.name for s in tests] == ["plan", "baseline", "tidy_tests", "test", "review", "finish"]
    assert [s.name for s in code] == ["plan", "baseline", "tidy_code", "test", "review", "finish"]
    for table in (tests, code):
        assert "red" not in [s.name for s in table] and "write_tests" not in [s.name for s in table]
        assert workflow.get("plan", table).on_pass == WAIT                      # still approved first
        assert workflow.get("baseline", table).on_fail == End("needs-me")       # the tests must pass before
    tidy_tests, tidy_code = workflow.get("tidy_tests", tests), workflow.get("tidy_code", code)
    assert (tidy_tests.persona, tidy_tests.may_change) == ("test_writer", "tests")      # the code is held still
    assert (tidy_code.persona, tidy_code.may_change) == ("code_writer", "not_tests")    # the tests are held still
    assert workflow.get("test", tests).on_fail == Rework("tidy_tests")                  # and must pass after
    assert workflow.get("test", code).on_fail == Rework("tidy_code")
    assert workflow.table_for(True, "tidy-tests") is tests                              # the same on a spec kit codebase
    assert workflow.table_for(False) is workflow.STEPS and workflow.table_for(False, "change") is workflow.STEPS
    with pytest.raises(ValueError, match="tidy-tests"):
        workflow.table_for(False, "rewrite-everything")
