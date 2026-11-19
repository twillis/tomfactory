"""The command line: it parses, calls one operation, and prints what comes back. No rules."""
import ast
import json
import pathlib

import pytest

from factory import cli, operations, records
from tests.conftest import PLAN, in_process
from tests.fake_agent import FakeAgent


@pytest.fixture
def fake(monkeypatch, home, fake_notify):
    """Make the command line's operations carry runs forward in-process with a fake agent."""
    agent = FakeAgent([{"envelope": PLAN}, {"envelope": dict(PLAN, plan="Second plan.", conflicts=["clashes with layering"])}])
    monkeypatch.setattr(operations, "launch", in_process(agent))
    return agent


def run_cli(capsys, *argv):
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out + captured.err


@pytest.mark.fr("FR-001")
@pytest.mark.fr("FR-003")
def test_the_story_one_commands_call_their_operations(capsys, tmp_path, fake):
    target = tmp_path / "viewer"
    code, out = run_cli(capsys, "init-target", str(target))
    assert code == 0 and str(target) in out and (target / ".factory.toml").exists()

    code, out = run_cli(capsys, "request", "Create a hello page", "--target", str(target), "--attempts", "2")
    assert code == 0 and "Run 1" in out
    assert operations.get_run(1).attempt_limit == 2

    code, out = run_cli(capsys, "plan")
    assert code == 0 and PLAN["plan"] in out and "keeps the layers apart" in out and "version 1" in out

    code, out = run_cli(capsys, "revise", "Make it shorter.")
    assert code == 0 and "Run 1" in out
    code, out = run_cli(capsys, "plan", "1")
    assert "Second plan." in out and "clashes with layering" in out and "version 2" in out

    code, out = run_cli(capsys, "abandon", "1")
    assert code == 0 and "rejected" in out and "abandoned by operator" in out


@pytest.mark.fr("FR-003")
def test_approve_reports_that_the_run_is_now_unattended(capsys, tmp_path, fake, monkeypatch):
    target = tmp_path / "viewer"
    run_cli(capsys, "init-target", str(target))
    run_cli(capsys, "request", "Create a hello page", "--target", str(target))
    monkeypatch.setattr(operations, "launch", lambda store, run, state, step: records.set_state(store, run.id, state, current_step=step))
    code, out = run_cli(capsys, "approve")
    assert code == 0 and "Run 1" in out and "notified" in out


@pytest.mark.fr("FR-001")
def test_refusals_print_the_reason_and_bad_arguments_are_distinguished(capsys, tmp_path, fake):
    code, out = run_cli(capsys, "request", "Do it", "--target", str(tmp_path / "nowhere"))
    assert code == 1 and "not a git repository" in out
    code, out = run_cli(capsys, "plan")
    assert code == 1 and "no runs" in out
    code, out = run_cli(capsys, "request")
    assert code == 2
    code, out = run_cli(capsys, "no-such-command")
    assert code == 2
    code, out = run_cli(capsys, "approve", "not-a-number")
    assert code == 2


@pytest.mark.fr("FR-021")
def test_plan_json_carries_the_same_fields(capsys, tmp_path, fake):
    target = tmp_path / "viewer"
    run_cli(capsys, "init-target", str(target))
    run_cli(capsys, "request", "Create a hello page", "--target", str(target))
    code, out = run_cli(capsys, "plan", "--json")
    data = json.loads(out)
    assert code == 0 and data["text"] == PLAN["plan"]
    assert data["ideals_addressed"] == PLAN["ideals_addressed"] and data["conflicts"] == []
    assert data["version"] == 1 and data["decision"] == "pending"


@pytest.mark.fr("FR-038")
def test_the_command_line_reaches_nothing_but_operations():
    tree = ast.parse(pathlib.Path(cli.__file__).read_text())
    modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    modules |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    ours = {m for m in modules if m.startswith("factory")}
    assert ours == {"factory"} or ours == {"factory.operations"}, ours
    names = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == "factory"
             for alias in node.names}
    assert names <= {"operations"}, f"cli.py may import only operations from the factory; got {names}"


@pytest.mark.fr("FR-014")
def test_stop_is_refused_when_nothing_is_running(capsys, tmp_path, fake):
    target = tmp_path / "viewer"
    run_cli(capsys, "init-target", str(target))
    run_cli(capsys, "request", "Create a hello page", "--target", str(target))
    code, out = run_cli(capsys, "stop")
    assert code == 1 and "not running" in out


@pytest.mark.fr("FR-066")
def test_a_tidy_request_is_made_with_a_flag(capsys, tmp_path, fake):
    target = tmp_path / "viewer"
    run_cli(capsys, "init-target", str(target))
    code, out = run_cli(capsys, "request", "Trim the tests", "--target", str(target), "--tidy", "tests")
    assert code == 0 and operations.get_run().workflow == "tidy-tests"
    assert run_cli(capsys, "request", "x", "--target", str(target), "--tidy", "everything")[0] == 2


# ---- Story 3 ----

@pytest.fixture
def done(capsys, tmp_path, monkeypatch, home, fake_notify):
    """A finished run, made through the command line with the fake agent."""
    from tests.test_cycle import script
    monkeypatch.setattr(operations, "launch", in_process(FakeAgent(script())))
    target = tmp_path / "viewer"
    run_cli(capsys, "init-target", str(target))
    run_cli(capsys, "request", "Add a greeting to the page please", "--target", str(target))
    run_cli(capsys, "approve")
    return operations.get_run()


@pytest.mark.fr("FR-027")
def test_status_prints_one_line_per_run(capsys, done):
    code, out = run_cli(capsys, "status")
    lines = [line for line in out.splitlines() if line.strip()]
    assert code == 0 and len(lines) == 1
    assert "1" in lines[0] and "accepted" in lines[0] and "Add a greeting to the page" in lines[0]


@pytest.mark.fr("FR-027")
def test_status_answers_quickly_with_many_runs(capsys, home):
    import time
    from factory.store import open_store
    store = open_store(home)
    for number in range(50):
        run = records.new_run(store, f"request {number}", "/tmp/t", "abc")
        records.end(store, run.id, "accepted", "fine")
    started = time.monotonic()
    code, out = run_cli(capsys, "status")
    assert code == 0 and time.monotonic() - started < 1.0
    assert len([line for line in out.splitlines() if line.strip()]) == 10      # the most recent ten


@pytest.mark.fr("FR-028")
@pytest.mark.fr("FR-047")
def test_show_prints_every_step_with_its_persona_and_checks(capsys, done):
    code, out = run_cli(capsys, "show")
    assert code == 0
    for expected in ("Add a greeting to the page please", "accepted", "attempt limit: 3", "plan version 1",
                     "planner", "test_writer", "code_writer", "architect", "reviewer", "documenter",
                     "tests_fail_first", "tests_pass", "factory/1-add-a-greeting-to-the"):
        assert expected in out, f"{expected!r} is missing from the listing"
    import re
    rows = re.findall(r"^ +\d+  (\w+) ", out, re.M)       # the step rows, in the order printed
    assert rows == ["plan", "baseline", "write_tests", "red", "build", "test", "architecture_review",
                    "document", "review", "finish"]

    build = [s for s in operations.show(done.id).steps if s.name == "build"][0]
    code, out = run_cli(capsys, "show", "--step", str(build.id))
    assert code == 0 and "Task: build the change" in out and "added greet" in out      # asked and produced
    assert "BUILDER-PRIVATE-THOUGHT" in out                                             # its events


@pytest.mark.fr("FR-025")
def test_watch_prints_events_until_the_run_ends(capsys, done):
    code, out = run_cli(capsys, "watch")
    assert code == 0
    assert "step_start" in out and "tests_pass: passed" in out and "accepted" in out
    assert out.strip().splitlines()[-1].startswith("Run 1 ended: accepted")


@pytest.mark.fr("FR-026")
def test_json_output_carries_the_same_fields(capsys, done):
    code, out = run_cli(capsys, "status", "--json")
    data = json.loads(out)
    assert code == 0 and data[0]["run"]["outcome"] == "accepted" and data[0]["steps"][-1]["name"] == "finish"
    code, out = run_cli(capsys, "show", "--json")
    data = json.loads(out)
    assert data["run"]["request"] == "Add a greeting to the page please"
    assert [s["name"] for s in data["steps"]][:2] == ["plan", "baseline"] and data["plans"][0]["version"] == 1


# ---- doctor ----

def healthy_agent(persona, prompt, cwd, capabilities, timeout, on_event, raw_sink, stderr_file,
                  on_child=None, model=None):
    from factory.agent import AgentResult
    return AgentResult(True, "ready", None, False, [], 0.1, None, None, None)


def broken_agent(*args, **kwargs):
    from factory.agent import AgentResult
    return AgentResult(False, "", None, False, [], 0.1, None, None, "you are not signed in")


@pytest.mark.fr("FR-040")
def test_doctor_reports_each_thing_the_factory_needs(capsys, home, monkeypatch):
    monkeypatch.setenv("TOMFACTORY_AGENT", "tests.test_cli:healthy_agent")
    code, out = run_cli(capsys, "doctor")
    lines = [line for line in out.splitlines() if line.strip()]
    assert code == 0 and len(lines) == 5
    for needed in ("git", "agent", "notification", str(home), "containment"):
        assert needed in out
    assert all(line.startswith("ok") for line in lines)

    monkeypatch.setenv("TOMFACTORY_AGENT", "tests.test_cli:broken_agent")
    code, out = run_cli(capsys, "doctor")
    assert code == 1 and "you are not signed in" in out
    assert [line[:2] for line in out.splitlines() if line.strip()].count("ok") == 4
