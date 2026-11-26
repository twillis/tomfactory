"""The adapter: the one seam to the agent program.

These tests put a stub on PATH under the agent program's name. The stub replays output
the real program printed during the spike (tests/fixtures/streams/).
"""
import json
import os
import pathlib
import stat
import sys
import time

import pytest

from factory import agent, proc

STREAMS = pathlib.Path(__file__).parent / "fixtures" / "streams"
PROGRAM = "claude"

STUB = f"""#!{sys.executable}
import json, os, sys, time
record = os.environ.get("STUB_RECORD")
if record:
    json.dump({{"argv": sys.argv[1:], "stdin": sys.stdin.read()}}, open(record, "w"))
stream = os.environ.get("STUB_STREAM")
lines = open(stream).read().splitlines() if stream else []
pause_after = int(os.environ.get("STUB_PAUSE_AFTER", "-1"))
for number, line in enumerate(lines):
    print(line, flush=True)
    if number == pause_after:
        time.sleep(0.6)
if os.environ.get("STUB_HANG"):
    time.sleep(600)
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
"""


@pytest.fixture
def stub(tmp_path, monkeypatch):
    """Install the stub and return a function that calls the adapter against it."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / PROGRAM
    script.write_text(STUB)
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("STUB_RECORD", str(tmp_path / "record.json"))
    work = tmp_path / "work"
    work.mkdir()

    def call(stream=None, capabilities="read", timeout=10.0, model=None, effort=None, **env):
        if stream:
            monkeypatch.setenv("STUB_STREAM", str(STREAMS / stream))
        for name, value in env.items():
            monkeypatch.setenv(name, str(value))
        events, raw, groups = [], [], []
        with open(tmp_path / "stderr.txt", "w") as err:
            result = agent.run_agent(
                persona="You are the planner.", prompt="Plan the change.", cwd=work,
                capabilities=capabilities, timeout=timeout,
                on_event=lambda kind, summary, payload: events.append((kind, summary, payload, time.monotonic())),
                raw_sink=lambda line: raw.append((line, time.monotonic())),
                stderr_file=err, on_child=groups.append, model=model, effort=effort)
        record = json.loads((tmp_path / "record.json").read_text())
        return result, events, raw, groups, record

    return call


@pytest.mark.fr("FR-025")
def test_events_and_raw_lines_arrive_while_the_agent_is_still_working(stub):
    result, events, raw, _, _ = stub("edits.jsonl", STUB_PAUSE_AFTER=3)
    assert result.ok
    assert len(raw) == len((STREAMS / "edits.jsonl").read_text().splitlines())
    assert raw[-1][1] - raw[0][1] > 0.4, "raw lines were batched until the end"
    assert events[-1][3] - events[0][3] > 0.4, "events were batched until the end"


@pytest.mark.fr("FR-026")
def test_one_tool_call_event_per_tool_use(stub):
    _, events, _, _, _ = stub("edits.jsonl")
    calls = [e for e in events if e[0] == "tool_call"]
    assert len(calls) == 3
    assert calls[0][1].startswith("write: ") and calls[0][1].endswith("inside.txt")
    assert [c[2]["ok"] for c in calls] == [True, False, False]
    assert calls[0][2]["action"] == "write" and "inside.txt" in calls[0][2]["arguments"]["file_path"]
    texts = [e for e in events if e[0] == "agent_text"]
    assert texts and texts[-1][2]["text"].startswith("Results of the three writes")
    assert "\n" not in texts[-1][1]  # the summary is one line


@pytest.mark.fr("FR-031")
def test_the_result_carries_text_usage_and_refusals(stub):
    result, _, _, _, _ = stub("edits.jsonl")
    assert result.ok and not result.timed_out and result.error is None
    assert result.text.startswith("Results of the three writes")
    assert result.tokens["output"] == 512 and result.tokens["input"] > 0
    assert result.cost_estimate == pytest.approx(0.0011381)
    assert result.duration_seconds > 0
    assert [d["action"] for d in result.denials] == ["write", "write"]
    assert result.denials[0]["path"].endswith("outside.txt")
    reads, _, _, _, _ = stub("reads.jsonl")
    assert [d["action"] for d in reads.denials] == ["read", "read"]


@pytest.mark.fr("FR-015")
@pytest.mark.parametrize("text, expected", [
    ('Here is my plan.\n```json\n{"plan": "do it", "conflicts": []}\n```\n', {"plan": "do it", "conflicts": []}),
    ('{"verdict": "accept", "reasons": ["fine"], "ideals_broken": []}', {"verdict": "accept", "reasons": ["fine"], "ideals_broken": []}),
    ('First {"draft": 1} then the real one: {"summary": "x", "nested": {"a": [1, 2]}} done.', {"summary": "x", "nested": {"a": [1, 2]}}),
    ("No JSON here at all.", None),
    ('Broken: {"plan": "unterminated', None),
    ("[1, 2, 3]", None),
])
def test_the_envelope_is_the_last_json_object_in_the_reply(text, expected):
    assert agent.extract_envelope(text) == expected


@pytest.mark.fr("FR-015")
def test_a_reply_without_an_envelope_is_still_a_finished_run(stub):
    result, _, _, _, _ = stub("edits.jsonl")
    assert result.ok and result.envelope is None
    structured, _, _, _, _ = stub("structured.jsonl")
    assert structured.envelope == {"verdict": "accept", "reasons": ["2 + 2 = 4 is a correct basic arithmetic fact."]}


@pytest.mark.fr("FR-014")
def test_a_hanging_agent_is_stopped_at_the_time_limit(stub):
    started = time.monotonic()
    result, _, _, groups, _ = stub("structured.jsonl", timeout=0.6, STUB_HANG=1)
    assert result.timed_out and not result.ok
    assert time.monotonic() - started < 8
    assert groups[0] and groups[-1] is None
    assert not proc._signal_group(groups[0], 0), "the agent's process group is still alive"


@pytest.mark.fr("FR-016")
def test_a_failed_agent_comes_back_as_a_result_not_an_exception(stub):
    result, _, _, _, _ = stub("error.jsonl", STUB_EXIT=1)
    assert not result.ok and not result.timed_out
    assert "issue with the selected model" in result.error
    bare, _, _, _, _ = stub(None, STUB_EXIT=3, STUB_STREAM="")
    assert not bare.ok and "3" in bare.error


@pytest.mark.fr("FR-042")
@pytest.mark.fr("FR-031")
def test_persona_prompt_and_capabilities_reach_the_program(stub):
    _, _, _, _, record = stub("structured.jsonl", capabilities="read")
    argv = record["argv"]
    assert record["stdin"] == "Plan the change."                       # the task, on standard input
    assert argv[argv.index("--append-system-prompt") + 1] == "You are the planner."
    assert argv[argv.index("--tools") + 1] == "Read,Glob,Grep"
    assert "--permission-mode" not in argv and "Bash" not in " ".join(argv)
    assert argv[argv.index("--setting-sources") + 1] == "" and "--strict-mcp-config" in argv
    assert "--model" not in argv and "--effort" not in argv          # the program's own effort unless a step sets one


@pytest.mark.fr("FR-041")
@pytest.mark.fr("FR-088")
def test_a_steps_grade_becomes_a_model_here_and_nowhere_else(stub):
    from factory import workflow
    assert set(agent.MODELS) == set(workflow.GRADES) and len(set(agent.MODELS.values())) == len(workflow.GRADES)
    for grade in workflow.GRADES:
        argv = stub("structured.jsonl", model=grade)[4]["argv"]
        assert argv[argv.index("--model") + 1] == agent.MODELS[grade]
    named = pathlib.Path(agent.__file__).parent
    others = [f.name for f in named.glob("*.py") if f.name != "agent.py"
              and any(model in f.read_text() for model in agent.MODELS.values())]
    assert others == []                                                 # no other module names a model

    _, _, _, _, record = stub("structured.jsonl", capabilities="read+edit")
    argv = record["argv"]
    assert argv[argv.index("--tools") + 1] == "Read,Glob,Grep,Edit,Write"
    assert argv[argv.index("--permission-mode") + 1] == "acceptEdits"
    assert "Bash" not in " ".join(argv)
    with pytest.raises(ValueError):
        stub("structured.jsonl", capabilities="read+shell")


@pytest.mark.fr("FR-041")
def test_the_adapter_can_be_swapped_by_configuration(monkeypatch):
    monkeypatch.delenv("TOMFACTORY_AGENT", raising=False)
    assert agent.get_adapter() is agent.run_agent
    monkeypatch.setenv("TOMFACTORY_AGENT", "tests.fake_agent:run_agent")
    from tests import fake_agent
    assert agent.get_adapter() is fake_agent.run_agent


@pytest.mark.fr("FR-041")
def test_no_other_module_names_the_agent_program():
    package = pathlib.Path(agent.__file__).parent
    offenders = [f.name for f in package.glob("*.py")
                 if f.name != "agent.py" and PROGRAM in f.read_text().lower()]
    assert offenders == [], f"only agent.py may name the agent program; found in {offenders}"


def stream_with_limit_status(tmp_path, status):
    """The spike's structured-reply stream, with its rate-limit line given another status."""
    lines = []
    for line in (STREAMS / "structured.jsonl").read_text().splitlines():
        item = json.loads(line)
        if item.get("type") == "rate_limit_event":
            item["rate_limit_info"]["status"] = status
        lines.append(json.dumps(item))
    path = tmp_path / f"{status}.jsonl"
    path.write_text("\n".join(lines) + "\n")
    return str(path)


@pytest.mark.fr("FR-016")
@pytest.mark.fr("FR-040")
def test_a_usage_warning_is_not_a_refusal(stub, tmp_path):
    """Found on a real run: at 90% of the usage window the program says 'allowed_warning' and carries on."""
    assert "rate_limit_event" in (STREAMS / "structured.jsonl").read_text()
    warned, _, _, _, _ = stub(stream_with_limit_status(tmp_path, "allowed_warning"))
    assert warned.ok and warned.error is None and warned.envelope["verdict"] == "accept"
    refused, _, _, _, _ = stub(stream_with_limit_status(tmp_path, "rejected"))
    assert not refused.ok and "usage limit" in refused.error and "rejected" in refused.error


@pytest.mark.fr("FR-158")
def test_a_steps_effort_is_passed_to_the_agent_program(stub):
    from factory import workflow
    for effort in workflow.EFFORTS:
        argv = stub("structured.jsonl", model="standard", effort=effort)[4]["argv"]
        assert argv[argv.index("--effort") + 1] == effort
