# Implementation Plan: Near-Loop Software Factory (Proof of Concept)

**Branch**: `001-near-loop-factory` (spec directory; no git branch created) | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-near-loop-factory/spec.md`

**Revision**: Third version. The first was written before a constitution existed; the second after the constitution was adopted and personas added; this one after an independent `/speckit-analyze` found 39 issues (research.md R18).

## Summary

The operator hands the factory a written request, approves a plan, and is notified when a test-first development cycle has finished unattended (spec stories 1 and 2). Every step is recorded as it happens (story 3), every run is held to the operator's stated ideals (story 4), and the first thing the factory builds is its own observability app (story 5). The whole thing must be small enough to read and extend (story 6).

The approach, in one paragraph: a plain Python script owns the order of steps and decides what happens next, by reading one table of step entries. Agents are used only to plan, write tests, build, review and document; each of those steps is carried out by its own persona, and none of them gets a shell. Everything that must be executed — the tests, git — is run by the script, and the script checks each agent's work before moving on. One small adapter is the only code that knows which agent program is used. Each run works in its own checkout of the target codebase, and every event is written to one SQLite file that the observability app reads.

The factory's own cycle does not use spec kit. Spec kit is the method being used to build the factory; the factory's nine steps run on its own personas and prompts. Using spec kit's steps as the cycle is on the spec's next-stage list.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: None at run time (standard library only). The official `claude` command (Claude Code 2.1.x) is the agent program, started as a child process. `git` and `notify-send` are used as external commands.

**Storage**: One SQLite file (`factory.db`, WAL mode) plus per-run files, all under the factory's home directory (`~/.tomfactory`, or `TOMFACTORY_HOME`). All of it goes through five repos in `store.py`.

**Testing**: `pytest`, run with `uv`. The workflow is tested end to end against a fake agent adapter, in-process and with a real detached driver, so the tests need no subscription usage. Tests marked `live` use the real agent program and desktop and run on request.

**Target Platform**: The operator's Linux desktop.

**Project Type**: Command-line tool, run as `uv run python -m factory …`.

**Performance Goals**: `factory status` answers in under 10 seconds (SC-005); in practice well under one. No throughput goals: one run at a time.

**Constraints**: The factory's own Python, excluding tests, personas and prompts, stays under 2,000 non-blank lines, enforced by a test (SC-007); tests, personas and prompts are not counted. No agent step has a shell. Every child process runs in its own process group with a time limit, and that group is recorded on the run so it can be stopped from outside. Only `factory/agent.py` may refer to the agent program or its tool names (FR-041). No Microsoft tools (constitution III).

**Scale/Scope**: One operator, one machine, one run at a time, tens of runs. Ten steps, six personas, eleven modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution is version 1.3.0: copied from `bttr_rs` (1.2.1) on 2026-11-18 at the operator's request, "for now", then amended the same day to add S8. Parts I and II apply. Part III (bttr principles) does not: this is not bttr work.

### Part I — Core Principles

| Rule | Result | Evidence |
|------|--------|----------|
| I. Serve, don't extract | Pass | A local tool for its owner. It captures nothing and reports nowhere. |
| II. Start from the problem and the person | Pass | The spec names the operator, Tom Willis, and what he can do afterwards that he cannot do now. Story 6 and SC-007/008 are measured by him, not by an invented reader. |
| III. No Microsoft tools | Pass | Python, git, SQLite, pytest, uv, `notify-send` and the `claude` command. If the observability app later wants browser tests, Playwright is excluded. |
| IV. Work leaves an artifact that shows its method | Pass, at completion | The final task writes a completion report to `../../artifacts/technical/` and extracts findings to `../../knowledge/technical/`. The method so far is in `docs/brainstorm-2026-11-18.md` and `research.md`. |

### Part II — Software Design

| Rule | Result | Evidence |
|------|--------|----------|
| S1. Three layers; only the differentiating logic is left to read | Pass | Every module has a named layer and responsibility; see "Layers" below. The control layer is divided into five named parts, not one place. Adding a step requires no change to the data or presentation layers, and a test asserts it. |
| S2. Discrete under fuzzy | Pass for writes; reads to be established | Agents are the fuzzy layer. They act only through two declared capabilities, `read` and `read+edit`, on the run's checkout. They have no shell and cannot write to the store, git, the test command or the factory. Whether the agent program can be stopped from *reading* outside its checkout is the spike's first question (T001 b). If it cannot, an agent can read the store file, and this row becomes a stated limit for the operator to rule on, recorded in research.md and the README. When an agent's outcome is unreliable, the remedy in this design is always a code check. |
| S3. Data access through a repo, matched by archetype or table | Pass | `store.py` exposes five repos: runs (an entity with a status), plans (versioned children of a run), steps (attempt records), events (an append-only log), and files (every per-run file). The runs repo is the status-history case: the caller sets a state and the repo writes the `run_state` event. No other module issues SQL or opens a file under the home directory; the adapter and the process runner are handed sinks and open files. |
| S4. The resource coordinates | Pass, with one limit the operator accepted | The Run is the resource. `operations.py` holds one function per operation on it; each reads top to bottom as resolve the run, check its state, perform the repo operations. Domain rules live there and in `workflow.py`, never in `store.py` or `cli.py`. **Limit**: S4 says a resource is resolved from a path; a command-line tool with one resource type resolves a run from its id. The operator was shown this limit and said to proceed (2026-11-18). The driver, which carries an operation forward after the command returns, performs repo operations too; it is part of the control layer and names them in line. |
| S5. Presentation is described, not bound to a medium | Pass | Every operation returns typed records — `Run`, `Plan`, `StepRecord`, `Event` — whose fields carry their types and allowed values. `cli.py` is one mediator that turns them into text or JSON; the observability app is a second, over the same schema. No function below `cli.py` returns formatted text. |
| S6. Any language the operator and robot can align on | Pass | Python, chosen by the operator for this stage. |
| S7. Always leave room to extend and specialise | Pass | Every derived behaviour names where it is overridden, and safety checks are applied by the driver whatever an entry says. See the table below. |
| S8. Every functional requirement has tests that fail first | Pass | Every test names the requirement it covers, and collection refuses an unmarked test. `scripts/traceability.py` fails while any requirement is named by no test. tasks.md places each requirement's tests, seen to fail, ahead of its code, including the live ones. See "How each requirement is tested". |

### Layers (S1)

| Layer | Module | Responsible for |
|-------|--------|-----------------|
| Presentation | `cli.py` | Parsing commands; rendering typed records as text or JSON |
| Control: operations | `operations.py` | What the operator can do to a run, and when it is refused |
| Control: rules | `workflow.py` | The step table, and what happens after each step |
| Control: execution | `driver.py` | Carrying one run forward; the single end-of-run routine |
| Control: verification | `checks.py` | The named checks applied to a step's result |
| Control: effects | `agent.py`, `workspace.py`, `notify.py`, `proc.py` | One discrete action each on the outside world — run an agent, change the checkout, notify, run a child process. They decide nothing. |
| Data | `store.py`, `config.py` | Everything kept (five repos); and reading the target's configuration and the ideals |

### S7: what is derived, where it is overridden, what cannot be dropped

| Derived behaviour | Default | Overridden in |
|-------------------|---------|---------------|
| An agent step's capabilities | `read` | The step's entry in `workflow.py` |
| What a step may change | `nothing` | The step's entry |
| What a failed check leads to | End, needs-me | The step's entry (`on_fail`) |
| A step's time limit | The target's `step_timeout_seconds` | The step's entry |
| The attempt limit | 3 | `factory request --attempts N`, stored on the run |
| The test command, test paths, documentation paths | Set by `factory init-target` | The target's committed `.factory.toml` |
| Who carries out an agent step | — (must be named) | The step's entry names a file in `personas/` |
| Which agent program | The `claude` command | `TOMFACTORY_AGENT` |
| The model an agent step uses | The agent program's default | The step's entry (next stage) |

Always applied by `driver.py` to every step, so a new entry cannot leave them out: the factory's code, personas, prompts and ideals are unchanged (`factory_untouched`); nothing changed outside the step's scope (`changes_allowed`); an agent's reply is a valid envelope (`envelope_valid`); the step ran in its own process group under a time limit.

### Workflow and Gates

| Rule | Result | Evidence |
|------|--------|----------|
| An unjudged idea SHOULD go through `/speckit-assess-*` first | Not followed | The assess skills are not installed in this repository. The brainstorm on 2026-11-18 served the same purpose and is recorded in `docs/brainstorm-2026-11-18.md`. This is a SHOULD. |
| Every API endpoint the client calls MUST have a round-trip contract test | Pass | The factory has no API endpoints. Its one contract with another program is the run store's schema; `tests/test_store.py` covers it round trip. |
| `/speckit-analyze` treats a conflict with any MUST as critical | Done | Run by an independent agent; eight critical findings, all addressed in this revision (research.md R18). |

**Result: pass**, with S2's read-confinement to be established by the first task and reported to the operator.

## Project Structure

### Documentation (this feature)

```text
specs/001-near-loop-factory/
├── plan.md              # This file
├── spec.md              # The feature specification
├── research.md          # Decisions, what was verified, and R18: changes after analysis
├── data-model.md        # Runs, plans, step records, events, target configuration
├── quickstart.md        # Seven scenarios that prove the feature works
├── contracts/
│   ├── cli.md           # The commands the operator types
│   ├── agent-adapter.md # The one seam to the agent program
│   ├── run-store.md     # The schema the observability app reads, and the repos' rules
│   └── workflow.md      # Step entries, checks, what happens next, inputs, envelopes, types
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # The task list
```

### Source Code (repository root)

```text
pyproject.toml           # Project metadata; pytest as the only dev dependency
README.md                # How a run flows, how to use it, how to add a step or a persona

factory/
├── __main__.py          # Lets "python -m factory" run the commands
├── cli.py               # Presentation
├── operations.py        # Control: what the operator can do to a run
├── workflow.py          # Control: the step table, next_step, after_wait
├── driver.py            # Control: carries one run forward; end_run
├── checks.py            # Control: the check registry and the checks
├── agent.py             # Effect: the adapter, the only code that knows the agent program
├── workspace.py         # Effect: git — the checkout, commits, undo, fingerprint, snapshot
├── notify.py            # Effect: desktop notification
├── proc.py              # Effect: run a child process; stop a process group; liveness
├── store.py             # Data: five repos and the typed records
└── config.py            # Data: home directory, target configuration, ideals

personas/                # Who carries out each agent step (three headings each)
├── planner.md
├── test_writer.md
├── code_writer.md
├── reviewer.md
└── documenter.md

prompts/                 # What each agent step is asked to do ({{placeholders}})
├── plan.md
├── write_tests.md
├── build.md
├── review.md
└── document.md

scripts/
└── traceability.py      # Gate: every FR in the spec is named by a test

tests/
├── conftest.py          # Fixtures; refuses to collect a test with no fr marker
├── fake_agent.py        # A scripted stand-in for the adapter
├── fixtures/streams/    # Real agent output saved by the spike
├── test_proc.py
├── test_store.py
├── test_config.py
├── test_workspace.py
├── test_agent.py
├── test_notify.py
├── test_step_shape.py   # Step defaults and the always-applied checks
├── test_workflow.py     # The step table and next_step, as pure functions
├── test_personas.py
├── test_checks.py       # The step-specific checks
├── test_operations.py
├── test_cycle.py        # Whole runs through the fake agent, in-process
├── test_detached.py     # The real detached driver: stop, interruption, nothing left running
├── test_ideals.py
├── test_cli.py
├── test_extending.py
├── test_docs.py
├── test_size.py
└── test_live.py         # Marked "live": the real agent program and the real desktop
```

**Structure Decision**: A single project. The factory is one small command-line tool, so it is one Python package beside its personas, prompts and tests. The observability app is deliberately not in this repository: it is a separate target codebase that the factory creates with `factory init-target` (research R12), so that an agent building it never has the factory's code in its working directory.

### How the modules depend on each other

```text
presentation   cli
                │
control        operations ──► driver ──► workflow
                │               │  └────► checks ──► proc, workspace, config
                │               ├──► agent ──► proc
                │               ├──► workspace ──► proc
                │               └──► notify ──► proc
data           store, config  ◄── operations, driver
```

- `cli` imports `operations` only, and renders what comes back. It holds no rules.
- `workflow` does no input or output: it is a table and two pure functions.
- `store` is reached only from `operations` and `driver`; effects are handed sinks and open files, never paths to choose.

## How a run flows

1. `factory request` calls `operations.request`, which records the run, creates its checkout, snapshots the factory's personas, prompts, code and ideals, and launches the driver in the background.
2. The driver runs the run's current step as `contracts/workflow.md` "How the driver uses this" lists: fingerprint, start a step record, call the adapter for an agent step, apply the checks, undo on a guard failure, commit if the entry says so, complete the record, ask `next_step`.
3. On `Wait` (after `plan`) it stores the plan version, sets `awaiting_approval`, notifies, and exits.
4. `factory approve` launches the driver again at the waiting step's successor. It carries on through `baseline`, `write_tests`, `red`, `build`, `test`, `architecture_review`, `document`, `review` and `finish`.
5. Every ending — accepted, rejected, needs-me, stopped, interrupted — goes through the one `end_run` routine, which sets the outcome and reason, stops any child still recorded, and notifies.

The complete rules are in [contracts/workflow.md](contracts/workflow.md).

## How each requirement is tested (constitution S8)

Every test carries `@pytest.mark.fr("FR-nnn")`; collection refuses a test without one. `scripts/traceability.py` lists the requirements no test names and must list none at the end. For every requirement the order is: write its tests, see them fail, write the code, see them pass, tidy. A test that would pass before its code exists is first seen to fail against a planted violation.

| Requirements | Tested in | Kind |
|--------------|-----------|------|
| FR-001 to FR-005 | `test_operations.py`, `test_workflow.py`, `test_cli.py`; `test_detached.py` for "not needed after approval" | functional |
| FR-006 to FR-013 | `test_workflow.py` (the table and every rule), `test_checks.py`, `test_cycle.py` | unit and functional |
| FR-014 | `test_proc.py`, `test_agent.py`, `test_detached.py` (stop and interruption leave nothing running) | unit, with real processes |
| FR-015 to FR-018 | `test_store.py`, `test_cycle.py` (every ending notifies), `test_notify.py`; `test_live.py` for the real desktop | unit and functional; live |
| FR-019 | `test_workspace.py`, `test_cycle.py` | unit and functional |
| FR-020 to FR-024 | `test_config.py`, `test_ideals.py`, `test_step_shape.py` (a broken ideal cannot be accepted) | unit and functional |
| FR-025 to FR-029 | `test_store.py`, `test_operations.py`, `test_detached.py` (interrupted, and a reused process id) | unit and functional |
| FR-030 to FR-033 | `test_step_shape.py` (scopes and fingerprint), `test_cycle.py` (undone and named; restored from snapshot), `test_agent.py` (denials), `test_store.py` and `test_operations.py` (second run refused) | unit and functional |
| FR-034, FR-035 | `test_operations.py` (`init_target`), `test_cycle.py` from an empty target; `test_live.py` for the real hello world | functional; live |
| FR-036 to FR-039 | `test_docs.py`, `test_extending.py`, `test_workflow.py` and `test_cli.py` (rules in one place), `test_size.py` | functional |
| FR-040 | `test_live.py`, written before the adapter; `test_cli.py` (`doctor`) | live; functional |
| FR-041 | `test_agent.py` (no other module names the agent program; adapter selection) and the whole suite passing on the fake | unit |
| FR-042 to FR-047 | `test_personas.py`, `test_step_shape.py`, `test_workflow.py`, `test_cycle.py`, `test_extending.py` | unit and functional |
| FR-048 to FR-050 | `test_personas.py`, `test_workflow.py` (the advisory rule), `test_cycle.py` (backlog written; failures carried past; a forbidden change still stops the run) | unit and functional |

## Requirements coverage

| Requirements | Where they are met |
|--------------|-------------------|
| FR-001 to FR-005 | `operations.py`; `WAIT` and `after_wait` in `workflow.py`; the detached launcher |
| FR-006 to FR-013 | The step table in `workflow.py`; `checks.py` |
| FR-014 | `proc.py`; the child process group recorded on the run; `end_run` |
| FR-015 to FR-018 | `driver.end_run`, `notify.py`, the runs repo |
| FR-019 | `workspace.py` (worktree and branch per run) |
| FR-020 to FR-024 | `config.py`, the `ideals` input in `driver.gather`, `envelope_valid`'s cross-field rule, the copy on the run |
| FR-025 to FR-029 | `store.py`; `operations.reconcile` |
| FR-030 to FR-033 | No shell; `changes_allowed`, `factory_untouched`; `workspace.undo`, snapshot and restore; the one-run rule in `operations.request` with a unique index behind it |
| FR-034, FR-035 | `operations.init_target`; the cycle |
| FR-036 to FR-039 | `README.md`; `workflow.py`; the check registry; `tests/test_size.py` |
| FR-040, FR-041 | `agent.py` only; `get_adapter` |
| FR-042 to FR-047 | `personas/`; the persona on each step entry; `edge_cases_stated`; the `persona` column |
| FR-048 to FR-050 | `personas/architect.md`; the `architecture_review` entry; the `advisory` field and its rule in `next_step` |

## Risks and how the plan handles them

| Risk | Handling |
|------|----------|
| The agent program cannot be confined as believed | The spike is the first task and tests edits and reads outside the checkout. The fingerprint and snapshot restore do not depend on the program's flags. If reads cannot be confined, that is reported to the operator, not worked around silently. |
| Agent-written tests run with the operator's permissions | Accepted for this stage, stated in the spec's Assumptions and the README. Sandboxing is next stage. |
| A code writer with no shell cannot see why its code fails | The failing test output is passed back on each attempt. The limit is settable per request. |
| A thorough test writer writes tests the code writer cannot satisfy | The run ends as needs-me. The record shows the edge cases considered, so the operator can tell an over-reaching test from a real defect. |
| The subscription's usage limit ends a run midway | The run ends as needs-me with the program's message; the record and partial work are kept. |
| A desktop notification from a background process does not appear | Tested live before the notifier is written; the outcome is always in `factory status` regardless. |
| The source grows past "one sitting" | The line-count test fails the build at 2,000 non-blank lines. As built it is about 1,760. |
| The copied constitution was written for another project | Part III is excluded by the Scope section. If Parts I and II prove a poor fit, the operator amends it with `/speckit-constitution`. |

## Complexity Tracking

| Item | Why it is needed | Simpler alternative rejected because |
|------|------------------|-------------------------------------|
| **Limit on constitution S4**: a run is resolved from its id, not from a path | A command-line tool with a single resource type and one level of containment has nothing to traverse | Path traversal for one resource would add a mechanism with no second user. Accepted by the operator on 2026-11-18. |
| The driver runs as a detached background process | The operator must not be needed between approval and notification, including if the terminal is closed | Running in the foreground dies with the terminal |
| Process-group id and driver start time recorded on the run | Without them a stopped or killed driver leaves an agent running and editing the checkout | Signalling only the driver was the first design, and the analysis showed it false |
| A `factory stop` command, not named in the spec | The spec's edge cases require that an operator can stop a run with nothing left running | Killing processes by hand leaves the run shown as in progress |
| Transitions as data on the step entry | Adding a step must not mean editing a decision function, and the driver must name no step | A hand-written function per step was the first design; it made FR-037 false |
| Five control parts instead of one | Constitution S1 forbids treating the control layer as one undivided place | A single engine module would mix rules, operations, execution, verification and effects |
| Typed records and a files repo | Constitution S5 and S3, read strictly | Bare dictionaries and files opened where convenient were the first design |
| The line limit raised from 1,000 to 1,500, then 2,000 | The four rows above add code, and so did reading and showing runs | The number is a stand-in for SC-007, which the operator measures by reading |
