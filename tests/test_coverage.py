"""Coverage: measured by the test command at the baseline and after the build, reported in the run's record and its
last commit, and a smell when it falls below a floor or drops too far (FR-110)."""
import pytest

from factory import config
from tests.conftest import git, record, script

# A test command that runs the tests, then writes a coverage.py JSON report: 95% before the build, and after it
# (once hello.py exists) whatever after.txt says.
REPORTER = '''import json, pathlib, subprocess, sys
code = subprocess.call([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
pct = float(pathlib.Path("after.txt").read_text()) if pathlib.Path("hello.py").exists() else 95.0
report = {"totals": {"percent_covered": pct}, "files": {"lib.py": {"summary": {"percent_covered": pct}}}}
pathlib.Path("coverage.json").write_text(json.dumps(report))
sys.exit(code)
'''


def measured(after, floor=0, drop=0, report="coverage.json"):
    toml = (config.DEFAULT_FACTORY_TOML.replace('test_command = "python -m pytest -q -p no:cacheprovider"',
                                                'test_command = "python reporter.py"')
            .replace('coverage_report = ""', f'coverage_report = "{report}"')
            .replace("coverage_floor = 0.0", f"coverage_floor = {floor}")
            .replace("coverage_drop = 0.0", f"coverage_drop = {drop}"))
    return {".factory.toml": toml, ".gitignore": config.DEFAULT_GITIGNORE + "coverage.json\n",
            "reporter.py": REPORTER, "after.txt": str(after)}


def smell(store, run):
    return next(c for c in record(store, run, "test").checks if c["name"] == "coverage_holds")


def record_text(target, run):
    return git(target, "show", f"{run.branch}:docs/runs/{run.branch.removeprefix('factory/')}.md")


@pytest.mark.fr("FR-110")
def test_coverage_before_and_after_is_in_the_record_and_the_last_commit(cycle):
    run, _, store, target = cycle(script(), files=measured(96.2, floor=90, drop=1))
    assert run.outcome == "accepted", run.reason
    found = smell(store, run)
    assert found["passed"] and found["smell"] and found["note"] == "coverage 95.0% before, 96.2% after (+1.2)"
    assert "## Coverage\n\nCoverage: 95.0% before, 96.2% after (+1.2)." in record_text(target, run)
    assert "Coverage: 95.0% before, 96.2% after (+1.2)." in git(target, "log", "-1", "--format=%b", run.branch)


@pytest.mark.fr("FR-110")
@pytest.mark.parametrize("after, floor, drop, says", [
    (93.5, 90, 1, "it fell by more than 1 points; most: lib.py (-1.5)"),
    (89.0, 90, 0, "it is below this codebase's floor of 90%"),
    (88.0, 90, 1, "it fell by more than 1 points; most: lib.py (-7.0); it is below this codebase's floor of 90%"),
])
def test_coverage_that_drops_too_far_or_sits_below_the_floor_is_a_smell_and_the_run_goes_on(cycle, after, floor,
                                                                                               drop, says):
    run, _, store, target = cycle(script(), files=measured(after, floor=floor, drop=drop))
    assert run.outcome == "accepted", run.reason                    # a smell never sends work back
    found = smell(store, run)
    assert not found["passed"] and found["note"].endswith(says)
    assert "coverage_holds" in record_text(target, run)             # listed under Smells for the operator


@pytest.mark.fr("FR-110")
def test_a_small_drop_above_the_floor_is_no_smell(cycle):
    run, _, store, _ = cycle(script(), files=measured(94.5, floor=90, drop=1))
    assert smell(store, run)["passed"]


@pytest.mark.fr("FR-110")
def test_a_codebase_that_measures_no_coverage_is_told_so_and_its_record_has_no_coverage(cycle):
    run, _, store, target = cycle(script())
    assert smell(store, run)["note"] == "coverage is not measured on this codebase"
    assert "## Coverage" not in record_text(target, run)
