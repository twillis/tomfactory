# Contract: Agent Adapter

`factory/agent.py` is the only module that knows which agent program is used, what its tools are called, how it is paid for, or which models exist (FR-041). Everything else calls one function.

## The call

```text
run_agent(
    persona:       who is doing the work: standing instructions for this step
    prompt:        the task: the full text to send
    cwd:           the directory the agent works in
    capabilities:  "read" or "read+edit"
    timeout:       seconds before the step is stopped
    on_event:      called with each event as it arrives
    raw_sink:      called with each raw line the agent program prints, unchanged
    stderr_file:   an open file the agent program's standard error is written to
    on_child:      called with the child's process-group id when it starts, and with None when it ends
    model:         optional; None means the agent program's default
) -> AgentResult
```

`capabilities` is a neutral name. The adapter alone maps it to the agent program's tools and permission settings:

| Capability | The agent can |
|------------|---------------|
| `read` | read and search files inside `cwd`; change nothing |
| `read+edit` | also create and edit files inside `cwd` |

No capability includes a shell.

`raw_sink` and `stderr_file` are supplied by the store's `files` repo, so the adapter never chooses a path or opens a file under the home directory (constitution S3). `on_child` is how the driver records which process group to stop if the run is stopped or the driver dies.

## What comes back

| Field | Meaning |
|-------|---------|
| ok | The agent finished without an error and within the time limit |
| text | The agent's final reply |
| envelope | The JSON object from the end of the reply, parsed, or None if absent or unparseable |
| timed_out | The time limit was reached and the agent was stopped |
| denials | Actions the agent tried that were refused |
| duration_seconds | Wall-clock time |
| tokens | Input and output token counts, if reported |
| cost_estimate | The agent program's own cost estimate, if reported |
| error | A readable message when `ok` is false and `timed_out` is false |

`ok` is false with an `error` when the agent program exits non-zero, reports an error in its final result, or reports that a usage limit was reached. The driver turns that into the `error` failure, which ends the run as needs-me carrying the message.

## Events passed to `on_event`

The adapter translates whatever the agent program emits into the factory's own event kinds, so no other module sees the program's format.

| Kind | Summary line | Payload |
|------|--------------|---------|
| `agent_text` | The first line of the text | The full text |
| `tool_call` | `<action>: <main argument>`, for example `edit: tests/test_hello.py` | The action, its arguments, whether it succeeded, a short result excerpt |

One `tool_call` event is produced per real tool use, however many raw lines the program prints for it.

## Guarantees

1. **Nothing is left running.** When `run_agent` returns — normally, on time-out, on an exception, or because the driver was told to stop — every process it started has ended (FR-014).
2. **Events arrive as they happen.** `on_event` and `raw_sink` are called while the agent is still working, not in a batch at the end (FR-025).
3. **It never raises for agent failures.** A failed, timed-out or unparseable run comes back as a result with `ok` false. Exceptions are reserved for bugs in the factory.
4. **It decides nothing.** The adapter does not validate the envelope's shape, count attempts, or choose what happens next. That belongs to the workflow.
5. **It is isolated from the operator's own setup.** The operator's personal agent settings, hooks, memory and connected tools are not loaded into factory runs.
6. **It confines the agent to `cwd`** for both reading and editing, as far as the agent program allows. What the spike (task T001) establishes about this is recorded in research.md; where the program cannot confine reads, that is stated in the README.

## Today's implementation

The `claude` command, run non-interactively with line-by-line JSON output, on the operator's subscription login. The exact flags and the shapes of the lines it prints are recorded in [research.md](../research.md), R2, R4 and the spike results. Sample streams saved by the spike live in `tests/fixtures/streams/`.

## Choosing an adapter

The driver obtains the adapter from `factory.agent.get_adapter()`, which returns `run_agent` unless the environment variable `TOMFACTORY_AGENT` names another callable as `module:function`. Tests use this to run a real detached driver against the fake. It is also where a second agent program would be selected later.

## The fake adapter

`tests/fake_agent.py` implements the same call. It is driven by a script: a list of entries, one per expected call, each giving the events to emit, files to write or change under `cwd`, the envelope to return, and optionally `timed_out`, `error`, or `block` (wait until the process is told to stop). It records every call it receives. So that a detached driver can use it, a script can also be loaded from a JSON file named by `TOMFACTORY_FAKE_SCRIPT`, with calls recorded to a file beside it.

The factory's whole workflow is tested against it. This is both the test double and the proof that the seam is real.

## Later, without changing callers

- An API key: the adapter passes a different credential to the same program.
- A model per step: the workflow already passes `model`; today it is always None.
- Another agent program: a second implementation of the same call, selected with `TOMFACTORY_AGENT`.
