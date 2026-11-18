"""Tests that use the real agent program and the real desktop.

Excluded from the default run. Run with:  uv run pytest -m live -q
They use the operator's subscription.
"""
import subprocess
import sys

import pytest

pytestmark = pytest.mark.live


@pytest.mark.fr("FR-017")
def test_a_notification_from_a_detached_process_succeeds():
    code = "import sys; from factory import notify; sys.exit(0 if notify.send('tomfactory test', 'sent from a detached process') else 1)"
    child = subprocess.Popen([sys.executable, "-c", code], start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert child.wait(timeout=30) == 0


@pytest.mark.fr("FR-040")
def test_the_real_agent_answers_on_the_subscription_with_no_api_key(tmp_path, monkeypatch):
    from factory import agent
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    events = []
    with open(tmp_path / "stderr.txt", "w") as err:
        result = agent.run_agent(
            persona="Your codename is ZEBRAFISH. When asked your codename, answer with it.",
            prompt='What is your codename? End your reply with the JSON object {"codename": "<it>"}.',
            cwd=tmp_path, capabilities="read", timeout=120,
            on_event=lambda *event: events.append(event), raw_sink=lambda line: None,
            stderr_file=err, model="haiku")
    assert result.ok, result.error
    assert result.envelope == {"codename": "ZEBRAFISH"}
    assert events and result.tokens["output"] > 0


@pytest.mark.fr("FR-034")
def test_a_real_hello_world_request_runs_to_accepted(tmp_path, monkeypatch):
    """The whole factory with real agents: about three minutes and a real, if small, cost."""
    import time

    from factory import operations
    from factory.store import open_store

    home = tmp_path / "home"
    monkeypatch.setenv("TOMFACTORY_HOME", str(home))
    monkeypatch.setattr("factory.notify.send", lambda title, body: True)
    target = operations.init_target(tmp_path / "hello")

    def wait(states, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            run = operations.get_run()
            if run.state in states:
                return run
            time.sleep(2)
        operations.stop()
        raise AssertionError(f"timed out waiting for {states}")

    run = operations.request(
        "Add a module hello.py with a function greet(name) that returns 'hello, <name>' and, for an "
        "empty or missing name, 'hello, world'. Document it in docs/hello.md.", target)
    run = wait(("awaiting_approval", "ended"), 300)
    assert run.state == "awaiting_approval", run.reason
    operations.approve(run.id)                 # the test plays the operator, once
    run = wait(("ended",), 900)

    steps = open_store(home).query("steps", {"run_id": run.id})
    assert run.outcome == "accepted", f"{run.outcome}: {run.reason}"
    assert [s.name for s in steps] == ["plan", "baseline", "write_tests", "red", "build", "test",
                                       "architecture_review", "document", "review", "finish"]
    assert [s.persona for s in steps if s.persona] == ["planner", "test_writer", "code_writer", "architect",
                                                       "documenter", "reviewer"]
    written = [s for s in steps if s.name == "write_tests"][0]
    assert written.produced["edge_cases"], "the test writer stated no edge cases"
