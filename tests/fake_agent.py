"""A scripted stand-in for the agent adapter. A test helper: it contains no tests.

It has the same call as `factory.agent.run_agent` and is driven by a script: a list of
entries, one per expected call. Each entry is a dict (or a function taking the call and
returning one) with any of:

    envelope       the JSON object the "agent" ends its reply with
    text           the reply text, when it should not simply be the envelope
    events         [(kind, summary, payload), ...] passed to on_event
    files          {relative path: text}  written under cwd; a value of None deletes the file
    outside_files  {absolute path: text}  written anywhere (to test the factory's own guard)
    timed_out      True: report that the time limit was reached
    error          a message: report that the agent program failed
    block          True: run a real child process that waits until it is stopped
                   a path: wait until that file exists, then carry on
    cost           what the agent program reports the step cost, in dollars (0 unless given)

A detached driver cannot be handed a Python object, so a script can also be loaded from
the JSON file named by TOMFACTORY_FAKE_SCRIPT; calls are then recorded in a file beside it.
"""
import json
import os
import pathlib
import sys

from factory import proc
from factory.agent import AgentResult

WAIT = ("import os, sys, time\n"
        "path = sys.argv[1]\n"
        "while not (path and os.path.exists(path)):\n"
        "    time.sleep(0.05)\n")


class FakeAgent:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def __call__(self, persona, prompt, cwd, capabilities, timeout, on_event, raw_sink,
                 stderr_file, on_child=None, model=None):
        call = {"persona": persona, "prompt": prompt, "cwd": str(cwd), "capabilities": capabilities,
                "timeout": timeout, "model": model}
        self.calls.append(call)
        assert self.script, f"the fake agent was called more times than scripted: {call['prompt'][:80]}"
        entry = self.script.pop(0)
        if callable(entry):
            entry = entry(call)
        return play(entry, cwd, timeout, on_event, raw_sink, stderr_file, on_child)


def play(entry, cwd, timeout, on_event, raw_sink, stderr_file, on_child):
    for kind, summary, payload in entry.get("events", []):
        on_event(kind, summary, payload)
    for name, text in entry.get("files", {}).items():
        file = pathlib.Path(cwd) / name
        if text is None:
            file.unlink(missing_ok=True)
        else:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)
    for name, text in entry.get("outside_files", {}).items():
        pathlib.Path(name).write_text(text)
    timed_out, error = bool(entry.get("timed_out")), entry.get("error")
    if entry.get("block"):
        release = "" if entry["block"] is True else str(entry["block"])
        result = proc.run([sys.executable, "-c", WAIT, release], cwd, timeout, lambda line: None,
                          stderr_file, on_child=on_child)
        timed_out = timed_out or result.timed_out
        if result.exit_code != 0 and not timed_out:
            error = error or "the agent was stopped"
    envelope = entry.get("envelope")
    text = entry.get("text", json.dumps(envelope) if envelope is not None else "no envelope")
    raw_sink(json.dumps({"type": "result", "result": text}))
    return AgentResult(ok=not timed_out and not error, text=text, envelope=envelope, timed_out=timed_out,
                       denials=entry.get("denials", []), duration_seconds=0.01,
                       tokens={"input": 10, "output": 5}, cost_estimate=entry.get("cost", 0.0), error=error)


def run_agent(persona, prompt, cwd, capabilities, timeout, on_event, raw_sink, stderr_file,
              on_child=None, model=None):
    """The fake for a detached driver: the script and the record of calls live in files."""
    script_path = pathlib.Path(os.environ["TOMFACTORY_FAKE_SCRIPT"])
    calls_path = script_path.with_suffix(".calls.jsonl")
    done = len(calls_path.read_text().splitlines()) if calls_path.exists() else 0
    script = json.loads(script_path.read_text())
    with open(calls_path, "a") as calls:
        calls.write(json.dumps({"persona": persona, "prompt": prompt, "cwd": str(cwd),
                                "capabilities": capabilities}) + "\n")
    assert done < len(script), "the fake agent was called more times than scripted"
    return play(script[done], cwd, timeout, on_event, raw_sink, stderr_file, on_child)
