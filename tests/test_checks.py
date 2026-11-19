"""The step-specific checks, against real checkouts and real test commands."""
import pathlib

import pytest

from factory import checks, config, operations
from factory.checks import CheckContext
from factory.workflow import Step
from factory.workspace import Workspace
from tests.conftest import commit_files, git

PASSING = "def test_ok():\n    assert True\n"
FAILING = "def test_bad():\n    assert 1 == 2, 'one is not two'\n"


@pytest.fixture
def make(tmp_path):
    """Build a check context over a fresh checkout of a new target."""
    made = []

    def build(files=None, changed=(), envelope=None, timeout=60):
        made.append(1)      # a test may build several; each gets its own folders
        tmp = tmp_path / str(len(made))
        tmp.mkdir()
        target = commit_files(operations.init_target(tmp / "target"), files)
        checkout = Workspace.create(target, tmp / "ws", "factory/1-test", git(target, "rev-parse", "HEAD"))
        settings = config.read_target_config(target, checkout.base_commit)
        groups = []
        context = CheckContext(run=None, step=Step("x", "code", on_pass="y"), checkout=checkout,
                               target_config=settings, changed=set(changed), envelope=envelope, before="",
                               stderr_file=open(tmp / "stderr.txt", "w"), on_child=groups.append,
                               timeout=timeout)
        context.groups = groups
        return context
    return build


def run(name, context):
    result = checks.get(name)(context)
    assert result.name == name
    return result


NO_TESTS = {"tests/helper.py": "x = 1\n"}


@pytest.mark.fr("FR-007")
@pytest.mark.fr("FR-008")
@pytest.mark.parametrize("check, files, passes, note, output", [
    ("baseline", None, True, "no prior tests", ""),
    ("baseline", {"tests/test_ok.py": PASSING}, True, "", "1 passed"),
    ("baseline", {"tests/test_bad.py": FAILING}, False, "already failing", "one is not two"),
    ("tests_fail_first", {"tests/test_bad.py": FAILING}, True, "", "one is not two"),
    ("tests_fail_first", {"tests/test_ok.py": PASSING}, False, "pass before", ""),
    ("tests_fail_first", NO_TESTS, False, "no tests", ""),
    ("tests_pass", {"tests/test_ok.py": PASSING}, True, "", "1 passed"),
    ("tests_pass", {"tests/test_bad.py": FAILING}, False, "fail", "test_bad"),
])
def test_a_check_that_runs_the_tests_judges_by_its_exit_code_and_keeps_what_they_printed(
        make, check, files, passes, note, output):
    result = run(check, make(files))
    assert result.passed is passes and note in result.note and output in result.output
    assert result.contained == {"network": False}


@pytest.mark.fr("FR-006")
def test_tests_added_requires_a_changed_file_under_the_test_paths(make):
    assert not run("tests_added", make(changed=[])).passed
    assert not run("tests_added", make(changed=["hello.py"])).passed
    assert run("tests_added", make(changed=["tests/test_hello.py"])).passed


@pytest.mark.fr("FR-045")
def test_edge_cases_must_be_stated(make):
    assert not run("edge_cases_stated", make(envelope={"edge_cases": []})).passed
    assert not run("edge_cases_stated", make(envelope={})).passed
    result = run("edge_cases_stated", make(envelope={"edge_cases": ["empty name"]}))
    assert result.passed


@pytest.mark.fr("FR-009")
def test_the_test_command_is_the_committed_one_whatever_the_checkout_says(make):
    context = make({"tests/test_bad.py": FAILING})
    (context.checkout.path / ".factory.toml").write_text('test_command = "true"\n')   # an agent's edit
    assert not run("tests_pass", context).passed, "the edited command was used"


@pytest.mark.fr("FR-032")
def test_running_the_tests_never_looks_like_a_change(make):
    context = make({"tests/test_ok.py": PASSING, "hello.py": "x = 1\n",
                    "tests/test_import.py": "import hello\n\ndef test_x():\n    assert hello.x == 1\n"})
    assert run("tests_pass", context).passed
    assert context.checkout.dirty() == {}
    assert not list(pathlib.Path(context.checkout.path).rglob("__pycache__"))


@pytest.mark.fr("FR-014")
def test_a_hanging_test_command_is_stopped_and_reported_as_a_time_out(make):
    from factory import proc
    hang = "import time\n\ndef test_hang():\n    time.sleep(600)\n"
    context = make({"tests/test_hang.py": hang}, timeout=1.5)
    result = run("tests_pass", context)
    assert not result.passed and result.timed_out and "1.5 seconds" in result.note
    assert context.groups[0] and context.groups[-1] is None
    assert not proc._signal_group(context.groups[0], 0)


@pytest.mark.fr("FR-065")
def test_a_set_of_tests_larger_than_the_codebases_budget_is_refused(make):
    import dataclasses
    context = make({"tests/test_ok.py": PASSING}, changed=["tests/test_big.py"])
    (context.checkout.path / "tests" / "test_big.py").write_text("x = 1\n" * 40)
    context.target_config = dataclasses.replace(context.target_config, test_budget_lines=30)
    over = run("tests_within_budget", context)
    assert not over.passed and "40" in over.note and "30" in over.note and "proportionate" in over.note
    context.target_config = dataclasses.replace(context.target_config, test_budget_lines=40)
    assert run("tests_within_budget", context).passed
    context.target_config = dataclasses.replace(context.target_config, test_budget_lines=0)      # 0: no limit
    assert run("tests_within_budget", context).passed
