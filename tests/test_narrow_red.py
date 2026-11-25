"""The red step runs only the run's own test files where the codebase says how (FR-152), and the writers are told the
codebase's limits before they write (FR-153).

Red is run against real checkouts and a real pytest: a test file of the codebase's, committed before the run, passes,
and the run's test files are written into the checkout as the test writer leaves them, uncommitted.
"""
import dataclasses
import sys

import pytest

from factory import checks, config, driver, operations, tables
from factory.checks import CheckContext
from factory.workflow import Step
from factory.workspace import Workspace
from tests.conftest import commit_files, git

OLD = "def test_old_still_holds():\n    assert True\n"
NEW_FAILS = "def test_new_is_not_built():\n    assert 1 == 2, 'not built yet'\n"
NEW_PASSES = "def test_new_already_holds():\n    assert True\n"
NARROW = "python -m pytest -q -p no:cacheprovider --junitxml=red-report.xml {paths}"


@pytest.fixture
def red(tmp_path):
    """The red check over a fresh checkout: `committed` is the codebase as the run found it, `written` what the test
    writer left (None deletes a file), `settings` what its .factory.toml adds."""
    def run(written, committed=None, settings=None):
        codebase = {"tests/test_old.py": OLD, **(committed or {})}
        target = commit_files(operations.init_target(tmp_path / "target"), codebase)
        checkout = Workspace.create(target, tmp_path / "ws", "factory/1-red", git(target, "rev-parse", "HEAD"))
        for name, text in written.items():
            file = checkout.path / name
            if text is None:
                file.unlink()
            else:
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(text)
        target_config = dataclasses.replace(config.read_target_config(target, checkout.base_commit), **(settings or {}))
        context = CheckContext(run=None, step=Step("red", "code", on_pass="build"), checkout=checkout,
                               target_config=target_config, changed=set(), envelope=None, before="",
                               stderr_file=open(tmp_path / "stderr.txt", "w"), on_child=lambda group: None, timeout=60)
        return checks.get("tests_fail_first")(context)
    return run


NARROWED = {"red_command": NARROW, "test_report": "red-report.xml"}


# ---- the setting ----

@pytest.mark.fr("FR-152")
def test_red_command_puts_each_of_the_runs_test_files_where_it_says_paths():
    settings = config.TargetConfig(red_command="python -m pytest -q --junitxml=r.xml {paths} -x", test_report="r.xml")
    assert config.red_argv(settings, ["tests/test_a.py", "tests/a b.py"]) == [
        sys.executable, "-m", "pytest", "-q", "--junitxml=r.xml", "tests/test_a.py", "tests/a b.py", "-x"]


@pytest.mark.fr("FR-152")
@pytest.mark.parametrize("lines, refused", [
    ('red_command = "pytest -q"\ntest_report = "r.xml"\n', "{paths}"),          # nowhere to put the files
    ('red_command = "pytest -q {paths}"\n', "test_report"),                    # nothing to show a test failed
    ('red_command = "pytest -q {paths}"\ntest_report = "r.xml"\n', None),
    ('test_report = "r.xml"\n', None),                                          # no setting: the whole suite
])
def test_a_red_command_needs_paths_and_a_test_report(target, lines, refused):
    (target / ".factory.toml").write_text(lines)
    git(target, "commit", "-q", "-am", "settings")
    commit = git(target, "rev-parse", "HEAD")
    if refused:
        with pytest.raises(config.ConfigError, match=refused.replace("{", r"\{").replace("}", r"\}")):
            config.read_target_config(target, commit)
    else:
        assert config.read_target_config(target, commit).red_command == ("" if "red_command" not in lines
                                                                           else "pytest -q {paths}")


# ---- what red runs, and what it decides ----

@pytest.mark.fr("FR-152")
def test_new_tests_that_fail_settle_red_without_the_rest_of_the_suite(red):
    result = red({"tests/test_new.py": NEW_FAILS}, settings=NARROWED)
    assert result.passed and "tests/test_new.py" in result.note
    assert "1 failed" in result.output and "passed" not in result.output, "the codebase's own test ran too"
    assert result.failing["tests"][0]["test"].endswith("test_new_is_not_built")


@pytest.mark.fr("FR-152")
@pytest.mark.parametrize("written, committed, passes, says", [
    # The new tests pass: the whole suite is run, as before, and they still do not count as failing first.
    ({"tests/test_new.py": NEW_PASSES}, None, False, "pass before"),
    # They pass alone, but a helper they changed breaks a test of the codebase's: the whole suite fails, red holds.
    ({"tests/test_new.py": NEW_PASSES, "tests/helper.py": "VALUE = 2\n"},
     {"tests/helper.py": "VALUE = 1\n", "tests/test_uses.py": "import helper\n\ndef test_value():\n"
                                                              "    assert helper.VALUE == 1\n"}, True, ""),
    # A file the runner cannot collect makes it exit non-zero with no test failing: not taken as red.
    ({"tests/test_new.py": NEW_PASSES, "tests/fixtures/rows.json": "{}\n"}, None, False, "pass before"),
    # A new test that cannot be read as code is still sent back before anything runs (FR-089).
    ({"tests/test_new.py": "def test_x(:\n    pass\n"}, None, False, "cannot be read as code"),
    # The run only deleted a test file: nothing of its own to run, so the whole suite is, and it passes.
    ({"tests/test_old.py": None}, {"tests/test_other.py": OLD}, False, "pass before"),
])
def test_anything_but_a_new_test_failing_is_settled_by_the_whole_suite_as_before(red, written, committed, passes,
                                                                                 says):
    result = red(written, committed, settings=NARROWED)
    assert result.passed is passes and says in result.note


@pytest.mark.fr("FR-152")
def test_without_a_red_command_red_runs_the_whole_suite_as_before(red):
    result = red({"tests/test_new.py": NEW_FAILS})
    assert result.passed and "1 failed, 1 passed" in result.output


@pytest.mark.fr("FR-152")
def test_the_narrowed_run_is_given_only_the_files_under_the_test_paths_that_the_run_changed(red):
    result = red({"tests/test_new.py": NEW_FAILS, "hello.py": "x = 1\n", "tests/test_old.py": OLD + "\n"},
                 settings=NARROWED)
    assert result.passed and result.note.endswith(": tests/test_new.py, tests/test_old.py")
    assert "1 failed, 1 passed" in result.output        # the edited file's old case runs beside the new one


# ---- the limits, told up front (FR-153) ----

WRITERS = ("write_tests", "build", "mend_tests", "tidy_tests", "tidy_code")


def limits(**settings) -> str:
    sources = driver.Sources(None, None, None, config.TargetConfig(**settings), config.PROMPTS_DIR)
    return driver.INPUTS["limits"](sources)


@pytest.mark.fr("FR-153")
def test_every_writing_step_is_given_the_limits_in_its_prompt():
    for table in tables.TABLES:
        for step in (s for s in table if s.name in WRITERS):
            assert "limits" in step.inputs, f"{step.name} is not given the limits"
    for name in WRITERS:
        assert "{{limits}}" in (config.PROMPTS_DIR / f"{name}.md").read_text(), f"{name}'s prompt does not show them"


@pytest.mark.fr("FR-153")
def test_the_limits_say_the_codebases_numbers_and_that_they_are_measured_after_not_gates():
    told = limits(line_length=120, test_budget_lines=300)
    assert "120" in told and "300" in told and "never" in told
    unlimited = limits(line_length=0, test_budget_lines=0)
    assert "no longest line" in unlimited and "no budget" in unlimited


@pytest.mark.fr("FR-153")
def test_the_limits_stay_smells_measured_after_the_step():
    for table in tables.TABLES:
        for step in (s for s in table if s.name in WRITERS):
            assert "lines_within_length" in step.smells and "lines_within_length" not in step.checks
            assert "tests_within_budget" not in step.checks
