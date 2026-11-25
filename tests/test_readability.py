"""The readability smell (FR-148) and the architect's flags (FR-149): the functions a step changed whose cognitive
complexity is over the codebase's limit, measured by the codebase's own command and reported, never a gate."""
import pytest

from factory import checks, config, tables
from tests.conftest import BUILD, git, names, record, script

# A stand-in for complexipy, committed in the target: each function's score is how many `if` statements it holds.
SCORER = '''\
import ast, json, pathlib, sys

found = []
for path in sorted(pathlib.Path(".").glob("*.py")):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.FunctionDef):
            found.append({"path": str(path), "function_name": node.name, "line_start": node.lineno,
                          "line_end": node.end_lineno,
                          "complexity": sum(isinstance(inner, ast.If) for inner in ast.walk(node))})
pathlib.Path(sys.argv[1]).write_text(json.dumps(found))
'''

TANGLED = ("def greet(name=''):\n    if name:\n        if name == 'x':\n            if len(name) > 3:\n"
           "                return 'hello'\n    return 'hello'\n")
OLD_TANGLE = "def old(a):\n    if a:\n        if a > 1:\n            if a > 2:\n                return a\n    return 0\n"

MEASURED = '''readability_command = "python score.py readability.json"
readability_report = "readability.json"
readability_limit = 2
'''


def measured_files(scorer=SCORER):
    settings = config.DEFAULT_FACTORY_TOML.replace('readability_command = ""', "").replace(
        'readability_report = ""', "").replace("readability_limit = 15", "") + MEASURED
    return {".factory.toml": settings, "score.py": scorer, "old.py": OLD_TANGLE}


def readable(step):
    return next(c for c in step.checks if c["name"] == "readable")


@pytest.mark.fr("FR-148")
@pytest.mark.fr("FR-107")
def test_a_changed_function_over_the_limit_is_a_smell_and_sends_nothing_back(cycle):
    run, fake, store, _ = cycle(script(build=dict(BUILD, files={"hello.py": TANGLED})), files=measured_files())
    assert run.outcome == "accepted" and names(store, run).count("build") == 1
    found = readable(record(store, run, "build"))
    assert found["smell"] and not found["passed"]
    assert "hello.py:greet (3)" in found["note"] and "old.py:old" not in found["note"]   # unchanged code stays quiet
    documenter = fake.calls[4]["prompt"]
    assert "hello.py:greet (3)" in documenter                                    # in `measured` (FR-136)


@pytest.mark.fr("FR-148")
def test_the_report_is_not_left_in_the_checkout_to_be_committed(cycle):
    run, _, _, target = cycle(script(build=dict(BUILD, files={"hello.py": TANGLED})), files=measured_files())
    assert "readability.json" not in git(target, "ls-tree", "-r", "--name-only", run.branch).split()


@pytest.mark.fr("FR-148")
def test_a_changed_function_within_the_limit_is_not_reported(cycle):
    run, _, store, _ = cycle(script(), files=measured_files())
    found = readable(record(store, run, "build"))
    assert found["passed"] and "over 2" in found["note"]


@pytest.mark.fr("FR-148")
def test_a_codebase_that_names_no_readability_command_is_not_measured(cycle):
    run, _, store, _ = cycle(script(build=dict(BUILD, files={"hello.py": TANGLED})))
    found = readable(record(store, run, "build"))
    assert found["passed"] and "not measured" in found["note"]


@pytest.mark.fr("FR-148")
@pytest.mark.parametrize("scorer", [
    "import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('not json')\n",
    "import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('{\"a\": 1}')\n",
    "print('wrote nothing')\n",
], ids=["not-json", "not-a-list", "no-report"])
def test_a_report_the_factory_cannot_read_is_said_and_sends_nothing_back(cycle, scorer):
    run, _, store, _ = cycle(script(build=dict(BUILD, files={"hello.py": TANGLED})), files=measured_files(scorer))
    assert run.outcome == "accepted" and names(store, run).count("build") == 1
    found = readable(record(store, run, "build"))
    assert not found["passed"] and "no report the factory can read" in found["note"]


SCORES = [{"path": "a.py", "function_name": "first", "complexity": 20, "line_start": 1, "line_end": 10},
          {"path": "a.py", "function_name": "second", "complexity": 20, "line_start": 12, "line_end": 20},
          {"path": "a.py", "function_name": "simple", "complexity": 3, "line_start": 22, "line_end": 30},
          {"path": "b.py", "function_name": "other", "complexity": 40, "line_start": 1, "line_end": 50}]


@pytest.mark.fr("FR-148")
@pytest.mark.parametrize("added, reported", [
    ({"a.py": {5}}, ["first"]),                         # a line inside its body
    ({"a.py": {1}}, ["first"]),                         # its first line
    ({"a.py": {10, 12}}, ["first", "second"]),          # the last line of one, the first of the next
    ({"a.py": {11, 21}}, []),                           # only between functions
    ({"a.py": {25}}, []),                               # changed, but within the limit
    ({"c.py": {5}}, []),                                # a file the scores do not name
    ({}, []),
])
def test_only_functions_over_the_limit_that_hold_an_added_line_are_reported(added, reported):
    assert [s["function_name"] for s in checks.changed_over(SCORES, added, limit=15)] == reported


@pytest.mark.fr("FR-149")
def test_the_architect_is_given_the_flags_to_judge(cycle):
    _, fake, _, _ = cycle(script(build=dict(BUILD, files={"hello.py": TANGLED})), files=measured_files())
    architect = fake.calls[3]["prompt"]
    assert "hello.py:greet (3)" in architect and "old.py:old" not in architect
    assert "flat dispatch" in architect and "backlog" in architect


@pytest.mark.fr("FR-149")
def test_the_architect_is_told_when_nothing_scored_high(cycle):
    _, fake, _, _ = cycle(script())
    assert "No function this run changed scored over" in fake.calls[3]["prompt"]


@pytest.mark.fr("FR-148")
@pytest.mark.parametrize("step", [s for table in tables.TABLES for s in table if s.may_change == "not_tests"],
                         ids=lambda s: s.name)
def test_every_step_that_writes_code_measures_readability(step):
    assert "readable" in step.smells
