"""Effect: the adapter. The only module that knows which agent program is used.

Everything else in the factory asks for one thing: "run this persona on this task in this
folder with these capabilities, tell me what happens as it happens, and give me the result".
What program does it, what its tools are called, how it is paid for and which models exist
are all decided here and nowhere else (FR-041).

Today the program is the `claude` command, run non-interactively on the operator's
subscription login. What it prints, and the flags below, were established by a spike and
are recorded in specs/001-near-loop-factory/research.md, "Spike results".
"""
import importlib
import json
import os
import pathlib
import tempfile
from dataclasses import dataclass

from factory import proc

PROGRAM = "claude"
SPEC_KIT_INTEGRATION = "claude"         # the name spec kit knows this agent program by
COMMANDS_DIR = pathlib.Path(".claude") / "skills"    # where a codebase keeps this program's commands

# The factory speaks of capabilities; only this table knows the program's tool names.
# No capability includes a shell.
CAPABILITIES = {
    "read": ["--tools", "Read,Glob,Grep"],
    "read+edit": ["--tools", "Read,Glob,Grep,Edit,Write", "--permission-mode", "acceptEdits"],
}

# Keep the operator's own settings, hooks and connected tools out of factory runs.
ISOLATION = ["--setting-sources", "", "--strict-mcp-config", "--no-session-persistence"]


@dataclass
class AgentResult:
    ok: bool                    # finished without an error and within the time limit
    text: str                   # the final reply
    envelope: dict | None       # the JSON object at the end of the reply, if there was one
    timed_out: bool
    denials: list               # actions the agent tried that were refused
    duration_seconds: float
    tokens: dict | None         # {"input": n, "output": n}
    cost_estimate: float | None
    error: str | None           # a readable message when ok is False and it did not time out


def run_agent(persona, prompt, cwd, capabilities, timeout, on_event, raw_sink, stderr_file,
              on_child=None, model=None) -> AgentResult:
    """Run the agent program once and return when it, and everything it started, has ended.

    It never raises for an agent's failure, and it decides nothing about what happens next.
    """
    if capabilities not in CAPABILITIES:
        raise ValueError(f"capabilities must be one of {', '.join(CAPABILITIES)}; got {capabilities!r}")
    command = [PROGRAM, "-p", "--output-format", "stream-json", "--verbose", *ISOLATION,
               "--append-system-prompt", persona, *CAPABILITIES[capabilities]]
    if model:
        command += ["--model", model]

    reader = _Reader(cwd, on_event, raw_sink)
    with tempfile.TemporaryFile("w+") as task:
        task.write(prompt)  # on standard input: a prompt can be far larger than one argument may be
        task.seek(0)
        try:
            done = proc.run(command, cwd, timeout, reader.line, stderr_file, on_child=on_child, stdin=task)
        except OSError as problem:  # the program is not installed, or cannot be started
            return AgentResult(False, "", None, False, [], 0.0, None, None,
                               f"the agent program could not be started: {problem}")

    final = reader.final or {}
    text = final.get("result") or ""
    error = None
    if not done.timed_out:
        if done.exit_code != 0 or final.get("is_error"):
            error = text or f"the agent program exited with code {done.exit_code}"
        elif reader.limit:
            error = f"the agent program reported a usage limit: {reader.limit}"
        elif not reader.final:
            error = "the agent program ended without a result"
    usage = final.get("usage") or {}
    tokens = {"input": sum(usage.get(k) or 0 for k in
                           ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")),
              "output": usage.get("output_tokens") or 0} if usage else None
    return AgentResult(
        ok=not done.timed_out and error is None, text=text, envelope=extract_envelope(text),
        timed_out=done.timed_out, denials=reader.denials(final), duration_seconds=done.duration_seconds,
        tokens=tokens, cost_estimate=final.get("total_cost_usd"), error=error)


class _Reader:
    """Turns the lines the program prints into the factory's own events."""

    def __init__(self, cwd, on_event, raw_sink):
        self.cwd, self.on_event, self.raw_sink = pathlib.Path(cwd), on_event, raw_sink
        self.pending = {}   # tool uses waiting for their outcome, by id
        self.final = None   # the program's closing "result" line
        self.limit = None   # set if the program says a usage limit was hit

    def line(self, raw):
        self.raw_sink(raw)
        try:
            item = json.loads(raw)
        except ValueError:
            return
        kind = item.get("type") if isinstance(item, dict) else None
        if kind == "result":
            self.final = item
        elif kind == "rate_limit_event":
            status = (item.get("rate_limit_info") or {}).get("status")
            if status and not status.startswith("allowed"):     # "allowed_warning" is still allowed
                self.limit = status
        elif kind in ("assistant", "user"):
            content = (item.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                self._block(block)

    def _block(self, block):
        if block.get("type") == "text" and block.get("text", "").strip():
            text = block["text"]
            self.on_event("agent_text", text.strip().splitlines()[0][:120], {"text": text})
        elif block.get("type") == "tool_use":
            self.pending[block.get("id")] = block
        elif block.get("type") == "tool_result":
            use = self.pending.pop(block.get("tool_use_id"), None)
            if use is None:
                return
            action, arguments = str(use.get("name", "")).lower(), use.get("input") or {}
            result = block.get("content")
            self.on_event("tool_call", f"{action}: {self._main(arguments)}", {
                "action": action, "arguments": arguments, "ok": not block.get("is_error"),
                "result": (result if isinstance(result, str) else json.dumps(result))[:300]})

    def _main(self, arguments):
        """The one argument worth showing: the file, shown relative to the checkout if it is inside."""
        for name in ("file_path", "path", "pattern"):
            if name in arguments:
                value = str(arguments[name])
                try:
                    return str(pathlib.Path(value).relative_to(self.cwd))
                except ValueError:
                    return value
        return ""

    @staticmethod
    def denials(final):
        return [{"action": str(d.get("tool_name", "")).lower(),
                 "path": (d.get("tool_input") or {}).get("file_path", "")}
                for d in final.get("permission_denials") or []]


def extract_envelope(text) -> dict | None:
    """The last JSON object in a reply, or None. Its shape is checked elsewhere."""
    decoder, found, position = json.JSONDecoder(), None, 0
    while (start := text.find("{", position)) != -1:
        try:
            value, end = decoder.raw_decode(text, start)
        except ValueError:
            position = start + 1
            continue
        if isinstance(value, dict):
            found = value
        position = end
    return found


def get_adapter():
    """The adapter to use: `run_agent`, unless TOMFACTORY_AGENT names another as module:function."""
    named = os.environ.get("TOMFACTORY_AGENT")
    if not named:
        return run_agent
    module, function = named.split(":")
    return getattr(importlib.import_module(module), function)


def command_instructions(root, name) -> str:
    """The instruction text of one of a codebase's own commands for this agent program."""
    return without_front_matter((pathlib.Path(root) / COMMANDS_DIR / name / "SKILL.md").read_text()).strip()


def without_front_matter(text) -> str:
    """A document's text without the `---` header block some files start with."""
    return text.split("---", 2)[2] if text.startswith("---") else text
