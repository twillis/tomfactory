# Tasks: Near-Loop Software Factory (Proof of Concept)

**Input**: Design documents from `/specs/001-near-loop-factory/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md, agent-adapter.md, run-store.md, workflow.md), quickstart.md

**Tests**: Required. Constitution S8: every functional requirement has at least one test, written first and seen to fail before the code that satisfies it (red, green, refactor), and every test names the requirement it covers.

**Organization**: Tasks are grouped by user story so each story can be built and tested on its own.

**Revision**: Rewritten 2026-11-18 after `/speckit-analyze`. The contracts are the authority for every name and shape used below; where a task and a contract disagree, the contract wins and the task is wrong.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: Which user story the task belongs to (US1 … US6)
- Paths are relative to the repository root, `src/tomfactory/`
- Commands are run as `uv run python -m factory …` and `uv run pytest …`

## How every test task is done (S8)

1. Write the tests named in the task. **Every test function carries `@pytest.mark.fr("FR-nnn")`** naming the requirement it covers or serves; several markers are allowed. A test that serves no requirement should not exist. `tests/conftest.py` refuses to collect an unmarked test.
2. Run them: `uv run pytest <file> -q`. **They must fail** (an import error for a module that does not exist yet counts). If a test passes before its code exists, the test is wrong or the code already exists: stop and resolve which before going on.
3. Only then start the implementation task that follows.
4. After the implementation task, run the same tests: they must pass. Then tidy the code and run them again.
5. A test is never weakened or deleted to make it pass.

`scripts/traceability.py` (T006) is a gate, not a test. It lists every FR in `spec.md` that no test names. It is run at each checkpoint, where its list should be shorter than at the last one, and it must list nothing at the end (T061).

Tests marked `live` use the real agent program or the real desktop and the operator's subscription. They are excluded from the default run and run with `uv run pytest -m live -q`.

---

## Phase 1: Setup

**Purpose**: Prove the unverified assumptions, then lay out the project.

- [X] T001 Adapter spike. Write `spikes/adapter_spike.py`, a throwaway script that runs the real `claude` command non-interactively in a temporary git repository placed under a temporary home directory (so there are files in parent directories to try to reach), and records what happens for each item below. Save every raw output stream it captures as a named file in `tests/fixtures/streams/` (these are kept; `spikes/` is not). Items: (a) **Confining edits**: find the flags under which an edit inside the working directory succeeds without asking and an edit to a file outside it is refused, trying `--permission-mode acceptEdits`, `--permission-mode dontAsk` with `--allowedTools` path rules, and a `--settings` JSON with permission rules; record whether the refusal appears in the result's `permission_denials`. Save streams `edits.jsonl` and `edits.jsonl`. (b) **Confining reads**: under the same candidates, can the agent read a file in a parent directory (for example a stand-in `factory.db` and `ideals.md`) and an absolute path such as `/etc/hostname`? Find flags that refuse both, if any exist. Save `reads.jsonl`. (c) **Isolation**: do `--setting-sources ""` and `--strict-mcp-config` keep the operator's hooks, memory files, skills and MCP servers out of the session? Compare the `init` event's `mcp_servers`, `memory_paths`, `skills`, `plugins` with and without. (d) **Envelopes**: does `--json-schema` enforce a reply shape, and in which field of the `result` event does the structured value appear? Save `structured.jsonl`. (e) **Persona**: does `--append-system-prompt` deliver persona text in non-interactive mode (ask the agent to repeat a marker word placed there)? (f) **Tool events**: from `edits.jsonl`, document the exact shape of the lines printed for one tool use and its result, enough to produce one `tool_call` event per use. (g) **Errors**: record what the stream and exit code look like for a failure that can be provoked cheaply (for example an invalid `--model` name); save `error.jsonl`. Append a section "Spike results (2026-11-…)" to `specs/001-near-loop-factory/research.md` stating, for each item, what was observed, the exact flags adopted, and whether a decision in R2, R4, R5 or R15 stands or its fallback is taken. If reads cannot be confined, say so plainly there: that fact goes in the README and the completion report. Do not start T016 or T017 before this is recorded.
- [X] T002 Create `pyproject.toml` at the repository root: project name `tomfactory`, `requires-python = ">=3.13"`, no run-time dependencies, a development dependency group containing only `pytest`, `[tool.uv] package = false` (the factory is run as `python -m factory`, so no build backend is needed), and pytest configuration: `testpaths = ["tests"]`, markers `fr(id): the functional requirement this test covers` and `live: uses the real agent program or desktop`, and `addopts = "-m 'not live'"`.
- [X] T003 [P] Create the package and folders from plan.md "Source Code": `factory/__init__.py`, `factory/__main__.py` (calls `factory.cli.main(sys.argv[1:])` and exits with its return value), and empty folders `personas/`, `prompts/`, `scripts/`, `tests/fixtures/streams/` and `tests/__init__.py`.
- [X] T004 [P] Create `.gitignore` at the repository root ignoring `__pycache__/`, `.venv/`, `.pytest_cache/`, `*.pyc` and `spikes/`.
- [X] T005 Create `tests/conftest.py` with: a collection hook that fails collection, naming the test, for any test function without an `fr` marker; and fixtures `home` (a temporary directory set as `TOMFACTORY_HOME`), `target` (a temporary git repository with a configured git user and one commit containing the `.factory.toml` defaults and the `.gitignore` from data-model.md "Target configuration"), and `fake_notify` (replaces the notification command with a recorder for the test). Run `uv sync` then `uv run pytest -q` and confirm pytest starts and collects nothing.
- [X] T006 Write `scripts/traceability.py`: reads every id on a requirement line (`- **FR-nnn**:`) in `specs/001-near-loop-factory/spec.md`, collects every id used in an `fr("…")` marker under `tests/`, prints the ids named by no test, and exits 1 if there are any. Run `uv run python scripts/traceability.py` and confirm it lists all 47 requirements.

---

## Phase 2: Foundational (blocks every story)

**Purpose**: The layers every story stands on: child processes, the store, configuration, the run's checkout, the adapter, notification, and the shape of a step.

**⚠️ No user story work starts until this phase is complete.**

### Child processes (`factory/proc.py`)

- [X] T007 Write `tests/test_proc.py`, using small real child processes written with `sys.executable -c`, every test marked `fr("FR-014")`: (1) each output line reaches the `on_line` callback while the child is still running, shown by a child that prints, sleeps, prints again; (2) a child that outlives its time limit is stopped and the result has `timed_out` true; (3) a child that starts a grandchild and then hangs leaves neither alive after the time limit; (4) a child that ignores the terminate signal is killed after the grace period; (5) a child writing more than 1 MB to standard output with no final newline does not stall; (6) when `on_line` raises, the child and its group are still stopped and the exception propagates; (7) `on_child` is called with the child's process-group id before the first line and with `None` after it ends; (8) `stop_group(pgid)` ends a running group started by another `run` call in a thread, and is harmless for a group that no longer exists; (9) `env` entries are visible to the child. Run and confirm they fail.
- [X] T008 Implement `factory/proc.py` per research.md R7: `run(cmd, cwd, timeout, on_line, stderr, env=None, on_child=None) -> ProcResult(exit_code, timed_out, duration_seconds)`, where `cmd` is a list of words and `stderr` is an open file. It starts the child with `start_new_session=True` and standard input closed, calls `on_child(pgid)`, reads standard output line by line in the calling thread, enforces the time limit with a timer that calls `stop_group`, and in a `finally` block calls `stop_group` and then `on_child(None)`. `stop_group(pgid, grace=5.0)` sends terminate to the group, waits up to `grace` seconds, then sends kill; it ignores a group that is already gone. Also `is_alive(pid, started)` and `started_at(pid)`, which read the process's start time from `/proc/<pid>/stat` so a reused process id is not mistaken for the original. Make T007 pass.

### The store (`factory/store.py`)

- [X] T009 Write `tests/test_store.py`: (1) opening a new store creates the tables and both unique indexes exactly as in `contracts/run-store.md` and sets WAL mode [`FR-025`]; (2) `runs.create` returns a `Run` whose `branch` is `factory/<id>-<slug>` and whose `workspace` is the path the `files` repo gives for that id, set in the creating transaction; the slug follows the rule in run-store.md for these requests: `"Create a hello-world app, please!"` → `create-a-hello-world-app-please`, `"!!!"` → `run`, a 200-character request → at most 40 characters [`FR-001`]; (3) a second un-ended run is refused by the database [`FR-033`]; (4) ids are never reused after a run ends [`FR-001`]; (5) `runs.set_state` writes exactly one `run_state` event without the caller writing it, and `runs.end` sets state, outcome, reason and `ended_at` together, clears `driver_pid`, `driver_started` and `child_pgid`, and refuses a second call on the same run [`FR-015`, `FR-016`]; (6) plans: versions are 1, 2, 3 in order, earlier versions and comments are kept, and a second `approved` plan for one run is refused [`FR-004`]; (7) steps: `steps.start` creates a row with `ended_at` empty and `passed` empty, sets `attempt` to one more than the earlier rows of that run and name, and stores `persona`; `steps.finish` completes it once with `checks` as a list of name, passed and note [`FR-026`, `FR-027`, `FR-028`, `FR-047`]; (8) events: ids only increase; `events.after(run, last_seen)` returns exactly the events after the given id, in order, with no gaps or repeats when called repeatedly while another connection writes [`FR-025`]; (9) a second, read-only connection can read while a write transaction is open [`FR-025`]; (10) every repo returns the typed records named in run-store.md, with JSON columns already parsed, and `state`, `outcome`, `decision`, `kind` and `failure` reject values outside their allowed sets [`FR-026`]; (11) files: `raw_sink(run, step)` returns a callable that appends each line to `runs/<id>/steps/<step-id>.jsonl`; `stderr_file` and `driver_log` return open files at the paths in run-store.md; `workspace_path` and `snapshot_dir` return the documented paths [`FR-025`, `FR-029`]. Run and confirm they fail.
- [X] T010 Implement `factory/store.py`: `open_store(home) -> Store` with the five repos in `contracts/run-store.md`, the exact schema there, the typed records `Run`, `Plan`, `StepRecord`, `Event` (dataclasses; allowed values as `Literal` types, checked on construction), and every rule in that contract's "Rules the repos keep". No SQL and no file opened under the home directory anywhere else in the package. All timestamps UTC ISO 8601 ending in `Z`. Make T009 pass.

### Configuration (`factory/config.py`)

- [X] T011 [P] Write `tests/test_config.py`: (1) the home directory is `TOMFACTORY_HOME` when set and `~/.tomfactory` otherwise, created on first use [`FR-020`]; (2) target configuration is read from `.factory.toml` at a given commit, not from the files on disk, shown by changing the file on disk without committing and still reading the committed values [`FR-009`]; (3) the defaults in data-model.md "Target configuration" apply for any missing key [`FR-014`, for the time limit]; (4) a target with no committed `.factory.toml` raises a readable error [`FR-001`]; (5) the ideals text is the content of `ideals.md` in the home directory, or empty when the file is absent [`FR-020`]; (6) a changed `ideals.md` is what the next read returns, with no cache [`FR-023`]; (7) `test_argv(config)` splits the test command into words without starting a shell [`FR-009`]. Run and confirm they fail.
- [X] T012 [P] Implement `factory/config.py`: `home()`, `read_target_config(target, commit) -> TargetConfig` (a dataclass; uses `git show <commit>:.factory.toml` through `factory.proc.run`, and `tomllib`), `read_ideals()`, `test_argv(config)` (`shlex.split`), the defaults, and the default text of a new target's `.factory.toml` and `.gitignore`. Make T011 pass.

### The run's checkout (`factory/workspace.py`)

- [X] T013 Write `tests/test_workspace.py` against the `target` fixture: (1) `Workspace.create(target, path, branch)` makes a git worktree at `path` on a new branch from the target's current commit, and the target's own working copy — including an uncommitted change and an untracked file placed there beforehand — is byte-for-byte unchanged afterwards [`FR-019`]; (2) `status()` returns the set of files git reports as added, modified or deleted, honouring `.gitignore`, so a `__pycache__/` folder does not appear [`FR-032`]; (3) `undo()` restores the checkout exactly to its last commit, removing new files and restoring deleted ones [`FR-032`]; (4) `commit(message)` commits everything not ignored and returns the commit id, and returns `None` when nothing changed [`FR-013`]; (5) `diff_since_base()` returns the run's whole change [`FR-012`]; (6) `fingerprint(paths)` changes when any file under the paths is added, removed or modified and is stable otherwise [`FR-030`]; (7) `snapshot(paths, dest)` then, after files under `paths` are changed, added and deleted, `restore(paths, dest)` returns them to exactly the snapshot [`FR-032`]; (8) `remove()` deletes the worktree, and deletes the branch only if it has no commits beyond the base [`FR-003`]. Run and confirm they fail.
- [X] T014 Implement `factory/workspace.py`: the `Workspace` class and the module functions `fingerprint`, `snapshot`, `restore` from T013, running git only through `factory.proc.run`. Make T013 pass.

### The adapter (`factory/agent.py`)

- [X] T015 Write `tests/fake_agent.py` exactly as `contracts/agent-adapter.md` "The fake adapter" describes: the same call signature, a script of entries (events to emit, files to write or change under `cwd`, the envelope, and optionally `timed_out`, `error` or `block`), a record of every call received, failure if called more times than scripted, and loading of the script from the JSON file named by `TOMFACTORY_FAKE_SCRIPT` with calls recorded to a file beside it. A `block` entry starts a real child process through `factory.proc.run` that sleeps until stopped, so `on_child` and stopping behave as they do for a real agent. This file is a test helper and contains no test functions.
- [X] T016 Write `tests/test_agent.py`, using a stub executable (a small Python script the test places on `PATH` under the agent program's name) that replays a file from `tests/fixtures/streams/`: (1) `agent_text` and `tool_call` events reach `on_event`, and raw lines reach `raw_sink`, while the stub is still running [`FR-025`]; (2) replaying `edits.jsonl` yields exactly one `tool_call` event per tool use, with the summary form in the adapter contract [`FR-026`]; (3) the result carries text, envelope, tokens, cost estimate, duration and denials; replaying `edits.jsonl` yields a non-empty `denials` [`FR-031`]; (4) a reply with no JSON object, or a malformed one, gives `envelope` None and `ok` true [`FR-015`]; (5) a stub that hangs is stopped at the time limit, the result has `timed_out` true, and no process is left [`FR-014`]; (6) replaying `error.jsonl`, and a stub that exits non-zero, each give `ok` false with a readable `error` and do not raise [`FR-016`]; (7) the persona text is delivered in the way T001 established, and `read` and `read+edit` produce the flags T001 adopted for each [`FR-042`, `FR-031`]; (8) `on_child` receives a process-group id and then `None` [`FR-014`]; (9) with `TOMFACTORY_AGENT` set to `tests.fake_agent:run_agent`, `get_adapter()` returns the fake, and without it the real one [`FR-041`]; (10) no file in `factory/` other than `agent.py` contains the agent program's name — and to see this test fail first, temporarily add the name to a comment in `factory/proc.py`, run it red, then remove the comment [`FR-041`]. Also write `tests/test_live.py` with one test marked `live` and `fr("FR-040")`: with `ANTHROPIC_API_KEY` and `CLAUDE_CODE_OAUTH_TOKEN` removed from the environment, the real adapter answers a one-line prompt with `ok` true. Run both files (`-m live` for the second) and confirm they fail.
- [X] T017 Implement `factory/agent.py` per `contracts/agent-adapter.md` and the spike results: `run_agent(...)` builds the command line, runs it through `factory.proc.run`, passes each raw line to `raw_sink`, translates lines into `agent_text` and `tool_call` events, extracts the envelope in the way T001 established, and returns an `AgentResult` dataclass; `get_adapter()` honours `TOMFACTORY_AGENT`. It decides nothing and never raises for agent failures. Make T016 pass, including the live test.

### Notification (`factory/notify.py`)

- [X] T018 [P] Write `tests/test_notify.py`, marked `fr("FR-017")`: (1) `send(title, body)` runs the notification command with the title and body and returns true; (2) when the command is missing, fails or times out, `send` returns false and does not raise. Add to `tests/test_live.py` a test marked `live` and `fr("FR-017")`: a notification sent from a detached child process (started with `start_new_session=True`) reports success. Run and confirm they fail.
- [X] T019 [P] Implement `factory/notify.py`: `send(title, body) -> bool` using `notify-send` through `factory.proc.run` with a 10-second time limit. Make T018 pass, including the live test; if the detached case fails, pass the desktop session's bus address through explicitly and record what was needed in research.md.

### The shape of a step (`factory/workflow.py`, `factory/checks.py`)

- [X] T020 Write `tests/test_step_shape.py` against `contracts/workflow.md` "A step entry", "Checks" and "Types": (1) an agent `Step` given only a name, kind, persona and `on_pass` has capabilities `read`, `may_change` `nothing`, no inputs, no checks, `on_fail` `End("needs-me")`, `commit_after` false [`FR-037`]; (2) constructing an agent `Step` without a persona raises; a code `Step` has no persona [`FR-042`]; (3) `checks.register(name)` adds a function to the registry and `checks.get(name)` returns it; an unknown name raises a readable error [`FR-037`]; (4) `envelope_valid` passes for an object with every required key of the right type (`text`, `list`, `verdict`) and fails with a note naming the missing or mistyped key; a `verdict` other than `accept` or `reject` fails [`FR-015`]; (5) `envelope_valid` fails a review envelope with a non-empty `ideals_broken` and verdict `accept` [`FR-022`]; (6) `changes_allowed` for each scope in "may_change scopes": `nothing` fails on any change; `tests` passes only for files under `test_paths`; `not_tests` fails for any file under `test_paths` — one written in this run, an older one, and a `conftest.py` there — and for `.factory.toml` and `.gitignore`, and passes otherwise; `docs` passes only under `docs_paths`; the note lists the offending files [`FR-032`]; (7) `factory_untouched` fails when the fingerprint of the factory package folder, `personas/`, `prompts/` or `ideals.md` differs from `context.before` [`FR-030`]. Run and confirm they fail.
- [X] T021 Implement, per `contracts/workflow.md`: in `factory/workflow.py`, the `Step` dataclass with its closed defaults, and the `Rework`, `End`, `Run`, `Wait`, `StepResult` types, with `STEPS` as an empty list for now; in `factory/checks.py`, `CheckContext`, `CheckResult`, the name registry (`register`, `get`), and the three always-applied checks `envelope_valid`, `changes_allowed`, `factory_untouched`. Make T020 pass.

**Checkpoint**: `uv run pytest -q` passes. `uv run python scripts/traceability.py` lists fewer requirements than at T006.

---

## Phase 3: User Story 1 — Hand over a request and approve its plan (Priority: P1) 🎯 MVP

**Goal**: The operator hands over a request, gets a plan, and approves it, sends it back with a comment, or abandons it. Nothing in the target changes before approval.

**Independent Test**: With the fake agent, make a request, see a plan and a waiting run, send the plan back and see a revised plan that received the comment, and confirm the target is unchanged throughout.

### Tests for User Story 1 (write first, see them fail)

- [X] T022 [P] [US1] Write `tests/test_workflow.py` (first part), calling `next_step` and `after_wait` directly: (1) the `plan` entry matches row 1 of the steps table in `contracts/workflow.md` [`FR-002`]; (2) plan passes → `Wait` [`FR-002`]; (3) `after_wait("approve")` → `Run("baseline")`; `after_wait("revise")` → `Run("plan")`; `after_wait("abandon")` → `End("rejected", "abandoned by operator")` [`FR-003`]; (4) rule 4: a malformed envelope → `Rework` of the same step, and when that step has already run `limit` times → `End("needs-me")` naming the step and the count [`FR-011`]; (5) rule 1: a timed-out result → `End("needs-me")` naming the step and the limit [`FR-014`]; (6) rule 2: an `error` result → `End("needs-me")` carrying the message [`FR-016`]; (7) rule 3: a `guard` result → `End("needs-me")` naming the files [`FR-032`]; (8) `next_step` and `after_wait` are defined in `factory/workflow.py` and no other module defines a function of either name; `workflow.py` imports nothing that does input or output [`FR-038`]. Run and confirm they fail.
- [X] T023 [P] [US1] Write `tests/test_personas.py`: every persona named by an entry in `workflow.STEPS` has a file in `personas/` with exactly the headings `## Expertise`, `## Priorities`, `## Must not`, each followed by non-empty text; and `personas/planner.md` exists with them. Mark `fr("FR-042")`. Run and confirm it fails.
- [X] T024 [P] [US1] Write `tests/test_operations.py` (first part), using `home`, `target`, `fake_notify`, the fake agent and an in-process launcher (passed to operations in place of the detached one): (1) `init_target(dir)` creates a git repository with one commit containing the default `.factory.toml` and `.gitignore`, and refuses a directory that already has content [`FR-034`]; (2) `request(text, target)` returns a `Run`; it refuses an empty request, a target that is not a git repository, and a target with no committed `.factory.toml`, each with a readable reason [`FR-001`]; (3) it refuses while another run has not ended, with a reason naming that run, and leaves that run untouched [`FR-033`]; (4) `request(..., attempts=2)` stores an attempt limit of 2 [`FR-010`]; (5) after the plan step the run is `awaiting_approval` with no driver process recorded, plan version 1 is stored with its text, `ideals_addressed` and `conflicts`, a notification saying the run is waiting was sent and a `notify` event recorded, and both the target's working copy and the run's checkout are unchanged [`FR-002`]; (6) `revise(run, comment)` stores the comment on version 1, marks it `revised`, and the fake's second call received the earlier plan and the comment in its prompt; version 2 is stored [`FR-004`]; three revisions in a row all work and none counts as an attempt [`FR-003`]; (7) `approve(run)` marks the current plan `approved`, sets the run `working` with `current_step` `baseline`, and refuses unless the run is `awaiting_approval` [`FR-003`]; (8) `abandon(run)` ends the run rejected with reason "abandoned by operator", removes the checkout, and sends the run-ended notification [`FR-003`, `FR-017`]; (9) the plan step's record names the persona `planner` and the fake received that persona's text [`FR-047`]; (10) a plan step whose envelope is malformed three times ends the run needs-me with a reason naming `plan` and 3 attempts, with three step records [`FR-011`, `FR-028`]; (11) every operation returns typed records or dataclasses, never formatted text [`FR-026`]. Run and confirm they fail.
- [X] T025 [P] [US1] Write `tests/test_cli.py` (first part), calling `factory.cli.main(argv)` with output captured: (1) `init-target`, `request` (with `--target` and `--attempts`), `plan`, `approve`, `revise`, `abandon` each call the matching operation and print its result as text [`FR-001`, `FR-003`]; (2) a refusal prints the reason and returns 1; bad arguments return 2 [`FR-001`]; (3) `plan --json` prints valid JSON with the plan's text, `ideals_addressed` and `conflicts` [`FR-021`]; (4) `factory/cli.py` imports `factory.operations` and does not import `factory.store`, `factory.driver` or `factory.workflow` [`FR-038`]. Run and confirm they fail.
- [X] T026 [US1] Write `tests/test_detached.py`, starting the real detached driver with `TOMFACTORY_AGENT` and `TOMFACTORY_FAKE_SCRIPT` set: (1) `request` returns while the plan step is still running (the fake entry blocks), the run is `planning`, and `driver_pid` and `driver_started` identify a live process [`FR-005`]; (2) once the fake is released the run reaches `awaiting_approval`, the process fields are empty, and `runs/<id>/driver.log` exists [`FR-005`]; (3) nothing the driver started is alive afterwards [`FR-014`]. Use short polling with a time limit so a hang fails the test. Run and confirm they fail.

### Implementation for User Story 1

- [X] T027 [P] [US1] Write `personas/planner.md` with the three headings. Expertise: turning a request into a plan a builder can follow without asking questions. Priorities: read the ideals first; the smallest change that satisfies the request; say plainly when the request conflicts with an ideal. Must not: change any file. Make T023 pass.
- [X] T028 [P] [US1] Write `prompts/plan.md`: the task for the plan step using the placeholders `{{request}}`, `{{ideals}}`, `{{previous_plan}}`, `{{comment}}`, `{{failure}}`, and ending by requiring the `plan` envelope from `contracts/workflow.md` "Envelopes".
- [X] T029 [US1] In `factory/workflow.py`: add the `plan` entry to `STEPS`, and implement `next_step(step, result, attempts, limit) -> Next` and `after_wait(decision) -> Next` exactly as `contracts/workflow.md` "What happens next" specifies, plus `get(name) -> Step`. The function is general: it reads the entry and the result and names no step. Make T022 pass.
- [X] T030 [US1] Implement `factory/driver.py` exactly as `contracts/workflow.md` "How the driver uses this": `advance(store, run_id, adapter)` running the eight numbered actions in a loop; `gather(name, …)` producing each input in the "Inputs and prompts" table; `fill(prompt_text, inputs)` replacing `{{name}}` placeholders, `(none)` for empty, and raising for a placeholder the entry does not list; `end_run(store, run, outcome, reason)`, the single end-of-run routine, which stops the recorded child group, ends the run through the runs repo, and sends and records the notification; and a terminate-signal handler that makes the loop stop its child and call `end_run` with needs-me, "stopped by operator". The driver names no step and no persona. At run start it snapshots `personas/`, `prompts/`, the package folder and `ideals.md` into the run's snapshot folder; when `factory_untouched` fails it restores from that snapshot.
- [X] T031 [US1] Implement `factory/operations.py` (first part): `init_target`, `request`, `plan`, `approve`, `revise`, `abandon`. Each reads top to bottom as: resolve the run, check its state, perform the repo operations (constitution S4). Each returns typed data and raises `Refused(reason)` when it cannot proceed. `request` holds the one-run rule. `launch(store, run, state, step)` spawns `python -m factory _drive <run-id>` as a detached process with output to the run's driver log, then sets the state, `current_step`, `driver_pid` and `driver_started` in one update; the launcher is a parameter so tests pass an in-process one. Make T024 and T026 pass.
- [X] T032 [US1] Implement `factory/cli.py` (first part) with `argparse`: `init-target`, `request`, `plan`, `approve`, `revise`, `abandon`, and the hidden `_drive`; each calls one operation and renders the returned data as text, or as JSON with `--json` where `contracts/cli.md` lists it; `Refused` prints the reason and returns 1. No rules in this module. Make T025 pass.

**Checkpoint**: `uv run pytest -q` passes. Story 1 works on the fake agent. Run the traceability script.

> Done 2026-11-18. Two changes from the list as written: the whole nine-entry step table was added in T029 (it is data, and `approve` needs a successor step to hand on to), so its tests, T033, were written with T022 ahead of it; and T023 checks the planner persona only, with the other four left to T034.

---

## Phase 4: User Story 2 — Unattended test-first cycle with a clear outcome (Priority: P2)

**Goal**: After approval the factory writes failing tests, builds until they pass, reviews, documents, ends in exactly one outcome with a reason, and notifies.

**Independent Test**: With the fake agent, approve a plan and see the run end accepted with tests that failed first; then script each failure path and see the right outcome and reason.

### Tests for User Story 2 (write first, see them fail)

- [X] T033 [P] [US2] Extend `tests/test_workflow.py`: (1) `STEPS` matches the steps table in `contracts/workflow.md` row for row: name, kind, persona, capabilities, `may_change`, checks, `on_pass`, `on_fail`, `commit_after` [`FR-006`, `FR-043`]; (2) for each entry, a passing result → its `on_pass`; `finish` passing → `End("accepted")` [`FR-015`]; (3) a failed `baseline` → `End("needs-me")` [`FR-016`]; a failed `tests_added` or `edge_cases_stated` on `write_tests` → `Rework("write_tests")` [`FR-045`]; a failed `tests_fail_first` on `red` → `Rework("write_tests")` [`FR-007`]; a failed `tests_pass` on `test` → `Rework("build")` [`FR-010`]; a failed `verdict_accept` on `review` → `End("rejected")` carrying the review's reasons [`FR-012`]; (4) each of those reworks, when the target step has already run `limit` times, → `End("needs-me")` naming the target step, the count and the last failure [`FR-011`]; (5) the persona on `write_tests` differs from the persona on `build`, and the persona on `review` differs from the persona on `build` [`FR-043`, `FR-044`]. Run and confirm they fail.
- [X] T034 [P] [US2] Extend `tests/test_personas.py`: the five files `planner.md`, `test_writer.md`, `code_writer.md`, `reviewer.md`, `documenter.md` exist with the three headings [`FR-042`]; the Priorities section of `test_writer.md` mentions both edge cases and failure cases, and its Must not section forbids writing the implementation; the Must not section of `code_writer.md` forbids editing tests [`FR-043`]; the Must not section of `reviewer.md` forbids changing files [`FR-044`]. Run and confirm it fails.
- [X] T035 [P] [US2] Write `tests/test_checks.py` for the step-specific checks against real temporary checkouts and real test commands: (1) `baseline` passes on exit 0 and on the target's `no_tests_exit_code` (with the note "no prior tests"), and fails otherwise with the output in the note [`FR-008`]; (2) `tests_added` fails when the step changed no file under `test_paths` [`FR-006`]; (3) `edge_cases_stated` fails on an empty `edge_cases` list and passes on a list with one entry [`FR-045`]; (4) `tests_fail_first` passes only when the test command exits non-zero and not with `no_tests_exit_code`; it fails on exit 0 and on "no tests found" [`FR-007`]; (5) `tests_pass` passes only on exit 0, and its note carries the output [`FR-008`]; (6) `verdict_accept` passes only for `accept` [`FR-012`]; (7) the test command used is the one in the target's configuration at the run's base commit, shown by changing `.factory.toml` in the checkout and seeing the committed command still run [`FR-009`]; (8) running the test command leaves `status()` empty in a target created by `init_target`, so caches never look like a change [`FR-032`]; (9) the test command runs under the step's time limit and a hanging one is stopped with nothing left running [`FR-014`]. Run and confirm they fail.
- [X] T036 [US2] Write `tests/test_cycle.py`: whole runs through the fake agent with a target made by `init_target`, the real test command, and the driver in-process. (1) Happy path from an empty target: the fake test writer writes a failing test under `tests/`, the fake code writer writes code that passes it; assert step names in order `plan, baseline, write_tests, red, build, test, review, document, finish`; the baseline note says "no prior tests"; outcome `accepted` with a reason; exactly three commits on the run's branch; a run-ended notification and `notify` event; `step_start`, `step_end` and `check` events for every step; and no call to the fake asked whether tests passed [`FR-034`, `FR-006`, `FR-009`, `FR-013`, `FR-015`, `FR-017`, `FR-018`, `FR-025`]. (2) A second request against the same target after the test merges the first run's branch: same step order, and its baseline runs the first run's tests [`FR-035`]. (3) Build needs two attempts: the second `build` call received the failing test output as `failure`; both attempts are recorded with attempt numbers 1 and 2 [`FR-010`, `FR-028`]. (4) Build fails three times: needs-me; the reason names `build` and 3 attempts; the last step record's check note holds the failing output; a run-ended notification was sent [`FR-011`, `FR-017`]. (5) The tests pass before any build: `write_tests` runs again and received the note that the tests did not fail [`FR-007`]. (6) The test writer writes a test that is never collected, so the command reports "no tests found": treated as not failing, `write_tests` runs again [`FR-007`]. (7) Review rejects: outcome `rejected`, the reason carries the review's reasons, no `document` step ran, notification sent [`FR-012`, `FR-015`, `FR-017`]. (8) The code writer edits the run's test file; in a second case it adds a new file under `tests/`; in a third it deletes an older test: each is undone, outcome needs-me naming the file, a `guard` event recorded [`FR-032`]. (9) The test writer writes outside `tests/`: undone, needs-me [`FR-032`]. (10) An agent step times out: needs-me naming the step and the limit; nothing left running; notification sent [`FR-014`, `FR-017`]. (11) The test writer lists no edge cases three times: needs-me naming `write_tests` and 3 attempts [`FR-045`, `FR-011`]. (12) The fake reports an `error` ("usage limit reached"): needs-me carrying that message; the partial work and record are kept [`FR-016`]. (13) Every agent step record names its persona; `write_tests` and `build` name different ones; the `review` call's prompt contains the diff and the passing test output and none of the code writer's events [`FR-043`, `FR-044`, `FR-047`]. (14) After every run above, the target's own working copy is unchanged and the factory fingerprint is unchanged [`FR-019`, `FR-030`]. (15) A fake step that changes a file in `personas/` (through a test hook, since the fake writes only under `cwd`): the file is restored from the run's snapshot, outcome needs-me naming it [`FR-030`, `FR-032`]. (16) Baseline already failing in a target with a broken test: needs-me "the existing tests were already failing" and no agent after `plan` was called [`FR-008`]. (17) A failed notification is recorded as a `notify` event and does not change the outcome [`FR-017`]. Run and confirm they fail.
- [X] T037 [US2] Extend `tests/test_detached.py`: (1) `stop(run)` on a `working` run whose current step blocks: the step's child process group is gone, the driver process is gone, the run is ended needs-me with reason "stopped by operator", a run-ended notification was sent, and every step and event recorded before the stop is still present [`FR-014`, `FR-029`]; (2) `stop` on a `planning` run does the same; `stop` on an `awaiting_approval` or `ended` run is refused [`FR-014`]; (3) after `approve`, the unattended cycle runs to an outcome in the detached driver with no further call from the test [`FR-005`]. Run and confirm they fail.

### Implementation for User Story 2

- [X] T038 [P] [US2] Write `personas/test_writer.md`. Expertise: a testing specialist. Priorities: list the edge cases and failure cases before the main path (empty input, missing files, boundaries, bad input, repeated calls) and cover them; tests fail for the right reason and read as a description of the behaviour. Must not: write or change the implementation; write outside the target's test paths.
- [X] T039 [P] [US2] Write `personas/code_writer.md`. Expertise: implementation. Priorities: make the failing tests pass with the smallest change that follows the plan and the ideals; keep layers and their interfaces clear. Must not: edit, delete, weaken or add tests; change anything under the test paths; change `.factory.toml`.
- [X] T040 [P] [US2] Write `personas/reviewer.md`. Expertise: review. Priorities: judge the result against the request, the approved plan and each ideal in turn; name anything that does not match in sentences the operator can read; any broken ideal means reject. Must not: change any file.
- [X] T041 [P] [US2] Write `personas/documenter.md`. Expertise: plain technical writing. Priorities: a short account of what the run changed, for the operator. Must not: change code or tests; write outside the target's documentation paths. With T038–T040, make T034 pass.
- [X] T042 [P] [US2] Write `prompts/write_tests.md`, `prompts/build.md`, `prompts/review.md` and `prompts/document.md`, each using exactly the placeholders that `contracts/workflow.md` "Inputs and prompts" lists for that step, and each ending by requiring that step's envelope.
- [X] T043 [US2] Implement the step-specific checks in `factory/checks.py`, each registered by name: `baseline`, `tests_added`, `edge_cases_stated`, `tests_fail_first`, `tests_pass`, `verdict_accept`. The three that run the test command do so through one helper, `run_tests(context)`, which uses `config.test_argv`, `factory.proc.run`, the step's time limit, the environment in data-model.md, and the store's `files` repo for standard error. Make T035 pass.
- [X] T044 [US2] In `factory/workflow.py`, add the entries for `baseline`, `write_tests`, `red`, `build`, `test`, `review`, `document`, `finish` exactly as the steps table in `contracts/workflow.md`. `next_step` should need no change; if it does, it was not general. Make T033 pass.
- [X] T045 [US2] Extend `factory/driver.py` only where T036 shows a gap: `gather` for the remaining inputs; commit when `commit_after` is set; undo and a `guard` event on a guard failure; restore from the snapshot when `factory_untouched` fails. Do not name a step. Make T036 pass.
- [X] T046 [US2] Extend `factory/operations.py` with `stop(run)`: refuse unless the run is `planning` or `working`; stop the recorded child process group; signal the driver process and wait for it to exit; if the run has still not ended, call `driver.end_run` with needs-me, "stopped by operator". Extend `factory/cli.py` with `stop`. Make T037 pass.

**Checkpoint**: `uv run pytest -q` passes. Stories 1 and 2 work end to end on the fake agent. Run the traceability script. **This is the earliest point for a first real run**: T058 and T059 may be done here if the operator wants to see it work sooner.

---

## Phase 5: User Story 3 — See what a run is doing and read back what it did (Priority: P3)

**Goal**: The operator can see the current step of a run in progress and read back any finished run in full.

**Independent Test**: During a detached fake-agent run blocked inside a step, `status` shows the current step and its start time; after it ends, `show` lists every step with what it was asked, what it produced, duration and check results.

### Tests for User Story 3 (write first, see them fail)

- [X] T047 [US3] Extend `tests/test_operations.py` and `tests/test_detached.py`: (1) detached, with the current step blocked: `status()` returns the run's state, the current step's name and start time, and the result of each earlier step [`FR-027`]; (2) `show(run)` on a finished run returns the request, the attempt limit, the ideals in effect, every plan version with its comment and decision, every step attempt in order with persona, asked, produced, duration, checks and failure, then outcome and reason [`FR-026`, `FR-028`, `FR-010`]; (3) `show(run, step=<step id>)` returns that step with its events [`FR-026`]; (4) `follow(run, after=id)` returns only events after the given id, in order [`FR-025`]; (5) detached: kill the driver process with the kill signal while a step blocks; the next call to any operation ends the run needs-me with reason "interrupted", stops the orphaned child process group so nothing is left running, sends the run-ended notification, and keeps every step and event recorded before the interruption; the run is never afterwards reported as running [`FR-029`, `FR-014`, `FR-017`]; (6) a run whose recorded `driver_pid` now belongs to a different process (same id, different start time) is also treated as interrupted [`FR-029`]. Run and confirm they fail.
- [X] T048 [P] [US3] Extend `tests/test_cli.py`: `status` prints one line per recent run with id, state or outcome, current step, elapsed time and the first words of the request, and answers in well under a second on a store with 50 runs [`FR-027`]; `show` prints every step attempt with its persona and checks; `show --step <id>` prints one step in full [`FR-028`]; `watch` prints events as they are added and returns when the run waits or ends, driven by a store the test writes to from a thread [`FR-025`]; `--json` on `status`, `show` and `plan` prints valid JSON carrying the same fields [`FR-026`]. Run and confirm they fail.

### Implementation for User Story 3

- [X] T049 [US3] Extend `factory/operations.py` with `status`, `show`, `follow`, and `reconcile(store)` — called at the start of every operation — which, for any run in `planning` or `working` whose driver is not alive according to `proc.is_alive(pid, started)`, calls `driver.end_run` with needs-me, "interrupted". All return typed data. Make T047 pass.
- [X] T050 [US3] Extend `factory/cli.py` with `status`, `show` (with `--step`), and `watch` (calls `follow` once a second until the run waits or ends), with `--json` where `contracts/cli.md` lists it. Make T048 pass.

**Checkpoint**: `uv run pytest -q` passes. Run the traceability script.

---

## Phase 6: User Story 4 — State ideals once and have every run held to them (Priority: P4)

**Goal**: The operator's ideals reach every plan and review, a broken ideal can never be accepted, and editing them needs no change to the factory.

**Independent Test**: State an ideal, run through the fake agent, and see the ideal's text in the plan and review prompts, on the run's record, and enforced in the outcome.

### Tests for User Story 4 (write first, see them fail)

- [X] T051 [US4] Write `tests/test_ideals.py`, through the fake agent: (1) with an `ideals.md` present, its full text is in the prompts the `plan`, `build` and `review` calls received [`FR-021`, `FR-022`]; (2) the run's record holds a copy of the ideals text in effect, and `show` returns it [`FR-024`]; (3) editing `ideals.md` between two runs means the second run's prompts and record carry the new text, with no other file changed [`FR-023`]; (4) a review envelope with a non-empty `ideals_broken` and verdict `reject` ends the run rejected with the broken ideal named in the reason [`FR-022`]; (5) a review envelope naming a broken ideal with verdict `accept` is never accepted: it is malformed, `review` runs again, and after the attempt limit the run ends needs-me [`FR-022`]; (6) with no `ideals.md`, the prompts contain "No ideals have been stated.", the run completes, and its record's ideals are empty [`FR-020`, `FR-024`]; (7) a plan envelope with a non-empty `conflicts` list is returned by `operations.plan` and printed by `factory plan` [`FR-021`]; (8) `operations.ideals()` returns the path and the text, and `factory ideals` prints both [`FR-020`]; (9) `ideals.md` is byte-for-byte unchanged after every run in this file [`FR-030`]. Some of these may already pass because the general driver fills `{{ideals}}` from the run: for each one that does, confirm it fails when the ideals input is removed from that step's `inputs` in a temporary copy of `STEPS`, then restore it. Run and confirm the rest fail.

### Implementation for User Story 4

- [X] T052 [US4] In `operations.request`, copy the current ideals text onto the run; in `driver.gather`, return the run's copy for `ideals`, or "No ideals have been stated." when empty; add `operations.ideals()`; in `factory/cli.py` add `ideals` with `--edit` (opens `$EDITOR` on the file, creating it if absent). Make T051 pass.

**Checkpoint**: `uv run pytest -q` passes. Run the traceability script.

---

## Phase 7: User Story 6 — Understand, use and extend the factory (Priority: P6)

Done before the real runs of Story 5 so that the README exists when the operator first uses the factory.

**Goal**: A reader can read the factory in one sitting, use it from the documentation alone, and add a step or a persona without touching existing ones.

**Independent Test**: The extension tests pass, the size test passes, and the README's named sections exist.

### Tests for User Story 6 (write first, see them fail)

- [X] T053 [P] [US6] Write `tests/test_size.py`, marked `fr("FR-039")`: counts non-blank lines in `factory/*.py` and fails above 1,500, printing the count per file. To see it fail first, set the limit in the test to one below the current count, run it red, then restore 1,500.
- [X] T054 [P] [US6] Write `tests/test_extending.py`, changing nothing on disk — it registers and inserts from the test itself: (1) register a new check with `checks.register`, insert a code `Step` after `test` in a copy of `workflow.STEPS` (pointing `test`'s `on_pass` at it), run a fake-agent cycle, and assert the new step appears in the run's record with its check listed; assert no source file in `factory/` was modified [`FR-037`]; (2) write a persona file into a temporary personas folder, name it on an agent step in the copied table, and assert the step record carries the new name and the fake received its text [`FR-046`]; (3) a new agent step entry that states no capabilities and no `may_change` runs with `read` and ends the run needs-me if the fake edits a file [`FR-037`, `FR-032`]; (4) the always-applied checks appear in the new step's record although its entry lists none [`FR-030`]; (5) `factory/store.py`, `factory/cli.py` and `factory/driver.py` contain none of the step names or persona names in `workflow.STEPS` [`FR-037`]. Run and confirm they fail; where one already passes, confirm it fails with a deliberate violation, as in T016(10).
- [X] T055 [P] [US6] Write `tests/test_docs.py`, marked `fr("FR-036")`: `README.md` exists and contains the headings "How a run flows", "Using the factory", "Adding a step", "Adding a persona", "Where the rules live", and "What this proof of concept does not protect you from"; and every command in the tables of `contracts/cli.md` appears in the README. Run and confirm it fails.

### Implementation for User Story 6

- [X] T056 [US6] Make T054 pass: provide the seams it needs (a way to pass a step table and a personas folder into a run, defaulting to `workflow.STEPS` and `personas/`) and remove any step or persona name from `store.py`, `cli.py` and `driver.py`.
- [X] T057 [US6] Write `README.md` with the six headings in T055: the run's flow as the steps table and the six rules from `contracts/workflow.md`; every command with an example; a worked example of adding a code step and of adding a persona, matching what T054 does; one paragraph pointing at `factory/workflow.py` as the only place the rules live; and, under the last heading, in plain words: tests written by an agent are executed on this machine with the operator's permissions; what the spike found about whether an agent can read files outside its checkout; and that sandboxing is not part of this stage. Make T055 pass. If T053 fails, shorten the code without removing behaviour until it passes.

**Checkpoint**: `uv run pytest -q` passes. Run the traceability script.

---

## Phase 8: User Story 5 — The factory builds its own observability app (Priority: P5)

**Goal**: From an empty target and a written request, the factory produces a working hello-world observability app with a real agent, and further requests go through the same cycle.

**Independent Test**: `init-target`, a hello-world request, approval, and an accepted run with a working app and passing tests; then a second request extends it.

The requirements of this story (FR-034, FR-035) are already tested through the fake agent in T024 and T036. These tasks prove them with the real agent program.

- [X] T058 [US5] Extend `tests/test_cli.py` with `doctor`, marked `fr("FR-040")`: with stand-ins, it reports one line per check in `contracts/cli.md` and returns 1 if any fails. See it fail, then add `operations.doctor()` and the `doctor` command. Then add to `tests/test_live.py` a test marked `live`, `fr("FR-034")`: the hello-world request from quickstart.md scenario 3 runs to `accepted` against a temporary target, with the plan approved by the test; see it fail if the real path is not yet working, and fix what it shows.
- [X] T059 [US5] Run all live tests: `uv run pytest -m live -q`. Then run quickstart.md scenario 3 for real against `../tomfactory-viewer`, and scenario 4 after it. Record under a new heading "Results (date)" in `specs/001-near-loop-factory/quickstart.md`: each run's id, outcome, reason, duration, cost estimate, and anything that did not match the scenario's "Expect". Do not merge the run branches into `../tomfactory-viewer`'s main line except as the scenarios require; say what was merged.

**Checkpoint**: The factory has built a real hello-world app from a written request.

---

## Phase 9: Polish and cross-cutting

- [X] T060 [P] Run quickstart.md scenarios 1, 2, 5, 6 and 7 and append each outcome to its "Results" section, including the measured time for `factory status` to answer (SC-005) and the count of consecutive real requests that completed through the same cycle (SC-011, which needs three).
- [X] T061 Run `uv run python scripts/traceability.py`. It must list nothing. If it lists a requirement, that requirement was built without a test: go back to the phase that built it and write the test, seeing it fail against a deliberate break before restoring the code. Do not add a marker to a test that does not exercise the requirement.
- [X] T062 [P] Delete `spikes/` once its findings are in `research.md` and its streams are in `tests/fixtures/streams/`. Confirm `uv run pytest -q` and `uv run pytest -m live -q` both pass.
- [X] T063 Operator task: read the factory's own source and README in one sitting and note the time (SC-007, under 60 minutes); then follow "Adding a step" and note the time until the new step shows in a run's record (SC-008, under 30 minutes). Record both in quickstart.md "Results". The implementer prepares this by confirming T054 and T055 pass and then hands it to the operator; it is not done by the implementer.
- [X] T064 Write the completion report to `../../artifacts/technical/2026-11-18-tomfactory-poc-completion.md` in the workspace, following `../../templates/completion-report.md`: what was built, the method, what the spike and the live runs showed, what the real runs cost and how long they took, what the independent analysis found and how it was resolved, and the open questions. Extract reusable findings — how to run the agent program unattended and what it can and cannot be confined to, the process-handling pattern, the personas-plus-code-checks pattern — to `../../knowledge/technical/` as short notes (constitution IV).

---

## Dependencies and execution order

### Phases

- **Phase 1 (Setup)**: T001 first. T002–T006 do not depend on T001. T016 and T017 need T001's recorded results and saved streams.
- **Phase 2 (Foundational)**: after Phase 1. Blocks every story.
- **Phase 3 (US1)**: after Phase 2.
- **Phase 4 (US2)**: after US1 — the cycle starts from an approved plan.
- **Phase 5 (US3)** and **Phase 6 (US4)**: each after US2. They touch the same files (`operations.py`, `cli.py`, `tests/test_cli.py`), so do them one after the other, in either order.
- **Phase 7 (US6)**: after US3 and US4, because T056 touches the driver and the command line.
- **Phase 8 (US5)**: after US2 at the earliest; placed here so the README exists first. Uses the operator's subscription.
- **Phase 9 (Polish)**: after all stories.

### Within Phase 2

T007→T008 (proc) first; everything else runs child processes through it. Then, in any order: T009→T010 (store); T011→T012 (config); T018→T019 (notify). T013→T014 (workspace) needs T008. T015, then T016→T017 (adapter), need T008, T010 and T001. T020→T021 need T012 and T014.

### Within each story

Tests first, seen to fail. Then personas and prompts (text, parallel). Then `workflow.py`, `checks.py`, `driver.py`, `operations.py`, and `cli.py` last: control before presentation, so the command line never holds a rule.

### Parallel opportunities

- Phase 1: T003, T004.
- Phase 2: T011/T012 and T018/T019 alongside the store pair.
- US1: T022, T023, T024, T025 (four test files); T027, T028 (text).
- US2: T033, T034, T035 (three test files); T038–T042 (text).
- US6: T053, T054, T055.
- Polish: T060, T062.

## Parallel example: User Story 2

```bash
# Tests, written together, each seen to fail:
Task: "T033 the step table and next_step in tests/test_workflow.py"
Task: "T034 the five personas in tests/test_personas.py"
Task: "T035 the step-specific checks in tests/test_checks.py"

# Personas and prompts, written together:
Task: "T038 personas/test_writer.md"
Task: "T039 personas/code_writer.md"
Task: "T040 personas/reviewer.md"
Task: "T041 personas/documenter.md"
Task: "T042 the four prompts"
```

## Implementation strategy

### MVP first

1. Phase 1, including the spike.
2. Phase 2.
3. Phase 3 (US1). **Stop and check**: on the fake agent, a request produces a plan that can be approved, revised or abandoned.

US1 alone shows the plan gate but builds nothing. The first point at which the factory does its whole job is the end of US2 on the fake agent; the first real run is T058–T059, which may be pulled forward to that point.

### Incremental delivery

1. Setup + Foundational → the layers are in place.
2. US1 → the plan gate works.
3. US2 → the whole cycle works on the fake agent.
4. US3 → runs can be watched and read back; interrupted runs are handled.
5. US4 → ideals are enforced.
6. US6 → the README, the extension proof and the size limit.
7. US5 → the hello-world observability app, built by a real agent.
8. Polish → traceability clean, quickstart results, the operator's reading test, the completion report.

## Notes

- Tests marked `live`, T001, T059 and T060 use the operator's subscription. Run them deliberately.
- Nothing is committed to git by these tasks unless the operator asks. Suggested commit points are the checkpoints.
- If the spike (T001) overturns a decision in research.md, update research.md and the affected contract before continuing, and say so.
- T063 is the operator's. Everything else can be done by the implementer.

## Completion notes (2026-11-18)

- T059 and T060 are marked done with shortfalls recorded in quickstart.md "Results": four real runs were made, of which one was accepted, one genuinely rejected and two wrongly failed by an adapter bug since fixed. SC-011 is not met as written, scenario 5 was not completed for real, and the long live test was written but not run, because the operator's usage window had reached 91%.
- T063: the operator skimmed the source in about 30 minutes (SC-007 met). He has not timed adding a step (SC-008).
- Added during the build, each test-first: documentation before review; refused edits end the run at once; the operator's comments travel with the request (under question, research.md R22); usage warnings are not refusals; changed factory files are kept when restored; and, at the operator's request, the architect persona with advisory steps (FR-048 to FR-050).
- Deferred at the operator's request: the repo layer (R19), personas using spec kit commands (R20), the architect in planning (R21).
