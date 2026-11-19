# Data Model: Near-Loop Software Factory (Proof of Concept)

**Date**: 2026-11-18 | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

Everything the factory keeps lives in its home directory: one SQLite file, `factory.db`, and a folder of per-run files. Every read and write goes through one gateway in `factory/store.py`, which has five operations that take a table and no knowledge of any particular table. The rules about what a record must say live in `factory/records.py`. The exact table definitions are in [contracts/run-store.md](contracts/run-store.md); this document explains what each record means and the rules it obeys.

## Run

One attempt to carry out one request.

| Field | Meaning |
|-------|---------|
| id | Sequential number, never reused |
| request | The operator's written request, as given |
| target | Absolute path of the target codebase |
| base_commit | The target's commit the run started from |
| branch | The branch holding the run's changes: `factory/<id>-<slug>` |
| workspace | The run's own checkout of the target |
| state | See the state table below |
| current_step | The step being run, or the one to run next |
| outcome | `accepted`, `rejected` or `needs-me`; empty until the run ends |
| reason | One or two sentences the operator can read (FR-016) |
| ideals | The ideals text in effect for this run (FR-024); empty if none |
| attempt_limit | How many times any one step may run in this run (default 3; FR-010) |
| driver_pid, driver_started | The driver process and its start time, while a driver is running; empty otherwise |
| child_pgid | The process group of the step's child process, while one is running |
| created_at, ended_at | Timestamps |

**Rules**

- Only one run may be un-ended at a time (FR-033). `operations.request` refuses with a readable reason; a unique index is the backstop.
- `outcome`, `reason` and `ended_at` are set together, exactly once, by the single end-of-run routine (FR-015).
- Changing a run's state writes a `run_state` event. This is a rule of the control layer (`records.set_state`), not of the data layer.
- A run in `planning` or `working` has a live driver. The process fields are written in the same update that sets the state, and cleared in the same update that sets `awaiting_approval` or `ended`. A run whose state says a driver is running, but for which no process with that id and start time exists, is ended as `needs-me`, reason "interrupted", and its recorded child process group is stopped (FR-029).

### Run states

```text
planning ──► awaiting_approval ──► working ──► ended
   ▲                │
   └── revise ──────┤
                    └── abandon ──► ended (rejected)
```

| State | Meaning | A driver is running | Who moves it on |
|-------|---------|--------------------|-----------------|
| planning | The plan step is running | yes | the driver |
| awaiting_approval | A plan is ready; nothing in the target has changed | no | the operator: approve, revise, or abandon |
| working | The unattended cycle is running | yes | the driver |
| ended | Finished, with an outcome and reason | no | nobody |

Any state can move to `ended` with outcome `needs-me` when the factory cannot continue. `factory stop` applies to `planning` and `working`.

## Plan

One version of the written plan for a run. A run has one or more, in order.

| Field | Meaning |
|-------|---------|
| run_id, version | Which run; 1, 2, 3 … |
| text | The plan, as Markdown |
| ideals_addressed | How the plan follows each ideal that applies (FR-021) |
| conflicts | Places where the request conflicts with an ideal; empty if none |
| comment | The operator's comment that sent this version back; empty if not sent back |
| decision | `pending`, `approved`, `revised` or `abandoned` |

**Rules**

- At most one plan per run is `approved`.
- Earlier versions and their comments are never deleted (FR-004).

## Step record

One execution of one step. Every execution is an attempt and gets its own record (FR-028).

| Field | Meaning |
|-------|---------|
| id | Sequential across the store; `factory show --step <id>` takes this number |
| run_id | Which run |
| name | Step name from the workflow (for example `build`) |
| kind | `agent` or `code` |
| persona | For an agent step, the name of the persona that carried it out (FR-047); empty for code steps |
| attempt | 1, 2, 3 … for this step name within this run |
| asked | What the step was asked: the full prompt for an agent step, the command for a code step that runs one, empty otherwise |
| produced | What it produced: the envelope for an agent step, the output summary for a code step |
| checks | Every check that ran, in order, each with its name, whether it passed, and a note |
| passed | Yes, no, or empty while running. Yes means every check passed. |
| failure | Empty, or why the step failed: `timeout`, `error`, `guard`, `malformed`, `check` |
| started_at, ended_at | Timestamps; duration is the difference |
| tokens, cost_estimate | From the agent's result; empty for code steps |

**Rules**

- A step record is created when the step starts, not when it ends, so a run in progress shows its current step (FR-027).
- A step may have no checks of its own (`finish`); the always-applied checks still run and are listed.

## Event

One thing that happened, recorded as it happened (FR-025).

| Field | Meaning |
|-------|---------|
| id | Sequential across the whole store; the polling cursor |
| run_id, step_id | Where it belongs; `step_id` is empty for run-level events |
| at | Timestamp |
| kind | One of the kinds listed in [contracts/run-store.md](contracts/run-store.md) |
| summary | One line a person can read, for example `edit: tests/test_hello.py` |
| payload | The full detail |

## Checks

Not stored as their own table. A check is a named function in the factory; its result is written into the step record's `checks` and as a `check` event. The full list, what each requires, and which are applied to every step are in [contracts/workflow.md](contracts/workflow.md), "Checks".

## Target configuration

A small file, `.factory.toml`, committed in the target codebase. It is read from the run's starting commit, never from the checkout, so an agent cannot change what "passing" means.

| Key | Meaning | Default from `factory init-target` |
|-----|---------|-----------------------------------|
| test_command | The command that runs the tests | `python -m pytest -q -p no:cacheprovider` |
| no_tests_exit_code | Exit code meaning "no tests found" | `5` |
| test_paths | Where tests live | `["tests/"]` |
| docs_paths | Where the document step may write | `["docs/", "CHANGELOG.md"]` |
| step_timeout_seconds | Time limit per step (FR-014) | `900` |
| test_budget_lines | The most lines of tests one run may add; 0 means no limit (FR-065) | `300` |

**How the test command is run**: it is split into words the way a shell would split them (no shell is started), run with the checkout as the working directory, in its own process group, under the step's time limit, with the driver's environment plus `PYTHONDONTWRITEBYTECODE=1`. `python` therefore means the Python that is running the factory, which has `pytest` available. A target that needs its own environment is a next-stage concern.

`factory init-target` also writes a `.gitignore` covering `__pycache__/`, `.pytest_cache/`, `*.pyc` and `.venv/`, so that running tests never looks like a change to the checkout.

## Personas

A persona is a Markdown file in the factory's `personas/` folder with three headings: Expertise, Priorities, Must not. Its name is stored on each agent step record. It is not stored in the database: the file is the record, and the run's snapshot folder keeps the version in use.

## How the spec's entities map

| Spec entity | Here |
|-------------|------|
| Request | `Run.request` and `Run.target` |
| Run | Run |
| Plan | Plan |
| Step record | Step record, with Events for the detail |
| Check | The checks in contracts/workflow.md; results on the step record |
| Outcome | `Run.outcome` and `Run.reason` |
| Ideals | `ideals.md` in the factory's home; copied into `Run.ideals` |
| Target codebase | A git repository with a committed `.factory.toml` |
| Persona | A Markdown file in `personas/`; its name is stored on each agent step record |
