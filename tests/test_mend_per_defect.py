"""A mend for each defect the builder finds in the tests (FR-150), and not one for a report it has made before.

The rule is tested as a pure function over next_step; the whole run, through the fake agent, with a real test
report, shows a second, different defect mended and the test writer told what the report named as failing.
"""
import pytest

from factory import tables, workflow
from factory.workflow import CheckResult, Rework, Run, StepResult, next_step
from tests.conftest import BUILD, CODE, TEST, WRITE_TESTS, names, record, script
from tests.test_who_answered import REPORTED

LIMIT = 3
GREETS = "tests/test_hello.py::test_greets"
EMPTY = "tests/test_hello.py::test_empty_name_still_greets"


def defect(*named):
    """The build's reply: the verdict test_defect, naming these tests."""
    return StepResult(False, "check", CheckResult(False, "a test no build can pass", name="verdict"),
                      verdict="test_defect", named=named)


@pytest.mark.fr("FR-150")
def test_the_builds_route_mends_once_per_test_and_at_most_twice():
    for table in tables.TABLES:
        for build in (s for s in table if s.name == "build"):
            assert build.routes == {"test_defect": Rework("mend_tests", at_most=2, then="test", once_per_test=True)}
            assert build.envelope[workflow.DEFECTIVE_TESTS] == "list"
            mend = workflow.get("mend_tests", table)
            assert {"failure", "defective_tests", "failing_tests"} <= set(mend.inputs)


@pytest.mark.fr("FR-150")
@pytest.mark.parametrize("named, reports, mends, expected", [
    ((GREETS,), [], {}, Run("mend_tests")),                                  # the first report
    ((EMPTY,), [(GREETS,)], {"mend_tests": 1}, Run("mend_tests")),           # a different defect: a mend of its own
    ((GREETS, EMPTY), [(GREETS,)], {"mend_tests": 1}, Run("mend_tests")),    # one of them new
    ((GREETS,), [(GREETS,)], {"mend_tests": 1}, Run("test")),                # the same again: not chased
    (("tests.test_hello::test_greets",), [(GREETS,)], {"mend_tests": 1}, Run("test")),    # in the report's spelling
    ((EMPTY,), [(GREETS,), (GREETS, EMPTY)], {"mend_tests": 1}, Run("test")),
    (("tests/test_hello.py::test_x",), [(GREETS,), (EMPTY,)], {"mend_tests": 2}, Run("test")),    # the cap: two
    ((), [], {}, Run("mend_tests")),                                         # naming none: mended if it is the first
    ((), [(GREETS,)], {"mend_tests": 1}, Run("test")),
])
def test_a_report_naming_a_test_not_reported_before_gets_a_mend(named, reports, mends, expected):
    assert next_step(workflow.get("build", tables.STEPS), defect(*named), {"build": 1, **mends}, LIMIT,
                     reports=reports) == expected


@pytest.mark.fr("FR-150")
@pytest.mark.parametrize("one, other, same", [
    ("tests/test_x.py::TestY::test_z", "tests.test_x.TestY::test_z", True),        # a runner's id, a JUnit report's
    ("tests/test_x.py::test_z[SQL, DMY]", "tests.test_x::test_z[SQL, DMY]", True),  # a case's own id kept whole
    (" tests/test_x.py::test_z ", "tests/test_x.py::test_z", True),
    ("tests/test_x.py::test_z[a.b]", "tests/test_x.py::test_z[a]", False),
    ("tests/test_x.py::test_z", "tests/test_y.py::test_z", False),
])
def test_two_names_for_the_same_test_are_read_as_one(one, other, same):
    assert (workflow.comparable_name(one) == workflow.comparable_name(other)) is same


# ---- a whole run: two different defects, each mended ----

BOTH_WRONG = dict(WRITE_TESTS, files={"tests/test_hello.py": TEST.replace("'hello'", "'hullo'")})
FIRST_MENDED = TEST.replace("greet('') == 'hello'", "greet('') == 'hullo'")


def reports(*named, files=None):
    said = dict(BUILD["envelope"], verdict="test_defect", reasons=[f"{name} expects 'hullo'; the plan says hello"
                                                                   for name in named], defective_tests=list(named))
    return dict(BUILD, envelope=said, files={"hello.py": CODE} if files is None else files)


def mends(text):
    return {"envelope": {"summary": "the expected greeting was misspelled", "mended": ["tests/test_hello.py"]},
            "files": {"tests/test_hello.py": text}}


@pytest.mark.fr("FR-150")
def test_a_second_different_defect_is_mended_and_the_test_writer_is_told_what_the_report_named(cycle):
    second = "tests.test_hello::test_empty_name_still_greets"
    run, fake, store, _ = cycle(script(write_tests=BOTH_WRONG, build=[reports(GREETS), mends(FIRST_MENDED),
                                                                      reports(second, files={}), mends(TEST)]),
                                files=REPORTED)
    assert run.outcome == "accepted"
    assert names(store, run)[4:] == ["build", "mend_tests", "test", "build", "mend_tests", "test",
                                     "architecture_review", "document", "review", "finish"]
    mend = [c["prompt"] for c in fake.calls if c["prompt"].startswith("# Task: mend a test")][-1]
    assert second in mend and "earlier" in mend and GREETS in mend          # this report's test, and the one before
    failing = mend[mend.index("## What the tests last reported"):]
    assert f"{second} (" in failing and "hullo" in failing                  # the report's id and its message
    assert record(store, run, "test", 1).passed


@pytest.mark.fr("FR-150")
def test_without_a_test_report_the_test_writer_is_told_there_was_none(cycle):
    run, fake, _, _ = cycle(script(write_tests=BOTH_WRONG, build=[reports(GREETS, EMPTY), mends(TEST)]))
    assert run.outcome == "accepted"
    mend = next(c["prompt"] for c in fake.calls if c["prompt"].startswith("# Task: mend a test"))
    assert "no test report" in mend[mend.index("## What the tests last reported"):]
