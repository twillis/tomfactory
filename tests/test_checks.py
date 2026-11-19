"""The step-specific checks, against real checkouts and real test commands."""
import pathlib

import pytest

from factory import checks, config, operations
from factory.checks import CheckContext
from factory.workflow import Step
from factory.workspace import Workspace
from tests.conftest import git

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
        target = operations.init_target(tmp / "target")
        for name, text in (files or {}).items():
            (target / name).parent.mkdir(parents=True, exist_ok=True)
            (target / name).write_text(text)
        if files:
            git(target, "add", "-A")
            git(target, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "files")
        checkout = Workspace.create(target, tmp / "ws", "factory/1-test")
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


@pytest.mark.fr("FR-008")
def test_baseline_passes_on_green_and_on_no_tests_and_fails_otherwise(make, tmp_path):
    none = run("baseline", make())
    assert none.passed and "no prior tests" in none.note
    assert run("baseline", make({"tests/test_ok.py": PASSING})).passed
    broken = run("baseline", make({"tests/test_bad.py": FAILING}))
    assert not broken.passed and "already failing" in broken.note and "one is not two" in broken.note


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


@pytest.mark.fr("FR-007")
def test_tests_fail_first_needs_a_real_failure_not_an_empty_run(make):
    red = run("tests_fail_first", make({"tests/test_bad.py": FAILING}))
    assert red.passed and "one is not two" in red.note
    green = run("tests_fail_first", make({"tests/test_ok.py": PASSING}))
    assert not green.passed and "pass before" in green.note
    empty = run("tests_fail_first", make({"tests/helper.py": "x = 1\n"}))
    assert not empty.passed and "no tests" in empty.note


@pytest.mark.fr("FR-008")
def test_tests_pass_only_on_a_clean_run_and_carries_the_output(make):
    good = run("tests_pass", make({"tests/test_ok.py": PASSING}))
    assert good.passed and "1 passed" in good.note
    bad = run("tests_pass", make({"tests/test_bad.py": FAILING}))
    assert not bad.passed and "one is not two" in bad.note and "test_bad" in bad.note


@pytest.mark.fr("FR-012")
def test_verdict_accept_passes_only_for_accept_and_carries_the_reasons(make):
    assert run("verdict_accept", make(envelope={"verdict": "accept", "reasons": ["fine"], "ideals_broken": []})).passed
    rejected = run("verdict_accept", make(envelope={"verdict": "reject", "reasons": ["no heading", "wrong file"],
                                                    "ideals_broken": ["layers are mixed"]}))
    assert not rejected.passed
    assert "no heading" in rejected.note and "wrong file" in rejected.note and "layers are mixed" in rejected.note


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
    assert not over.passed and "40" in over.note and "30" in over.note and "once" in over.note
    context.target_config = dataclasses.replace(context.target_config, test_budget_lines=40)
    assert run("tests_within_budget", context).passed
    context.target_config = dataclasses.replace(context.target_config, test_budget_lines=0)      # 0: no limit
    assert run("tests_within_budget", context).passed
