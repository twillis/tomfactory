# Research: Near-Loop Software Factory (Proof of Concept)

**Date**: 2026-11-18 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Each entry is a decision the plan depends on. Entries marked **Verified** were checked on the operator's machine on 2026-11-18. Entries marked **To verify** are believed but unproven, and each names the task that must prove it before anything is built on top.

## R1. Language and dependencies

- **Decision**: Python 3.13, standard library only at run time (`subprocess`, `sqlite3`, `argparse`, `json`, `tomllib`, `pathlib`, `signal`, `threading`). `pytest` is the only development dependency. `uv` runs it.
- **Rationale**: The operator chose Python scripts. A standard-library-only factory has nothing to install and nothing hidden, which serves "read in one sitting" (SC-007).
- **Alternatives considered**: A CLI framework and a rich-text library (as `sf` uses) were rejected as unnecessary reading. Rust, which the operator's design-ideals note leans towards long term, was rejected for the proof of concept because the operator asked for Python now.
- **Verified**: Python 3.13.5, uv 0.11.29, pytest and git 2.53.0 are installed. Python's built-in SQLite library is 3.46.1. The `sqlite3` command-line tool is not installed, so nothing may depend on it.

## R2. How an agent is started

- **Decision**: Run the official `claude` command non-interactively: `claude -p <prompt> --output-format stream-json --verbose`, with `--tools` set per step, `--strict-mcp-config`, `--setting-sources ""`, and `--no-session-persistence`. Standard input is closed.
- **Rationale**: This is the supported way to run Claude Code unattended on a subscription, and it emits one JSON event per line, which the recording needs.
- **Alternatives considered**: The Agent SDK (a Python dependency, and more to read). The Pi agent (needs an API key). Resuming one session across steps as `sf` does (saves tokens, but makes the reviewer continue the builder's conversation and adds session handling).
- **Verified**: With no `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` in the environment, a one-line prompt ran and exited 0 using the subscription login (the init event reported `apiKeySource: none`). Claude Code version 2.1.327. The stream contained four event types: `system` (subtype `init`), `assistant`, `rate_limit_event`, and `result`. The `result` event carried `is_error`, `duration_ms`, `num_turns`, `usage` (token counts), `total_cost_usd` (an estimate, present even on subscription), `permission_denials`, and the final text in `result`.
- **Verified**: The flags `--model`, `--effort`, `--tools`, `--allowedTools`, `--permission-mode` (choices include `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan`), `--json-schema`, `--max-budget-usd`, `--append-system-prompt`, `--add-dir` and `--bare` exist in this version.

## R3. The adapter seam (FR-040, FR-041)

- **Decision**: One module, `factory/agent.py`, is the only code that knows the `claude` command exists. Its contract is "given a prompt, a working directory, a tool list, a time limit and optional model, yield events as they arrive and return a final result". See [contracts/agent-adapter.md](contracts/agent-adapter.md).
- **Rationale**: Both prior-art projects isolate the agent this way (`sf`'s runner files, SSSF's `agent_pi.py` and `agent_cc.py`). It is what makes API keys, per-step models and other agents an addition and not a rewrite.
- **How it is proven**: The factory's own tests run the whole workflow against a fake adapter that replays canned events. If the tests pass without `claude` installed, nothing else depends on it.

## R4. What an unattended step is allowed to do

- **Decision**: No agent step gets a shell. Read-only steps (plan, review) get `Read,Glob,Grep`. Writing steps (write tests, build, document) get `Read,Glob,Grep,Edit,Write` with `--permission-mode acceptEdits`. The agent's working directory is the run's own checkout. Everything that must be executed — the test command, git — is run by the factory's code.
- **Rationale**: This is "agents propose, code disposes" taken literally. Without a shell an agent cannot run commands, install anything, or reach outside its checkout, so most of FR-030 and FR-031 hold by construction and no permission bypass is needed. It also removes the temptation for an agent to run the tests itself and report on them (FR-009).
- **Cost**: The build agent cannot run its own code. It learns whether it worked only when the factory runs the tests and passes the failure back. For a hello-world app this is acceptable; a richer app may need a restricted shell later.
- **Alternatives considered**: `bypassPermissions` as `sf` uses (simple, but an unattended agent could then do anything). A restricted shell allow-list via `--allowedTools` (deferred until a real need appears).
- **To verify (task: adapter spike)**: that in `-p` mode with `acceptEdits`, an edit outside the working directory is denied and shows up in `permission_denials`; and that `--setting-sources ""` plus `--strict-mcp-config` stops the operator's own hooks, memory and MCP servers from loading into factory runs. If either is false, the guard in R6 is the fallback and the spike records what was observed.

## R5. Structured hand-offs from agents

- **Decision**: Every agent step must finish with a small JSON object (its "envelope") whose shape is fixed per step — for example the review step returns `{"verdict": "accept" | "reject", "reasons": [...], "ideals_broken": [...]}`. The factory validates the envelope in code. A missing or malformed envelope sends the step round again, which uses an attempt; at the attempt limit the run stops as needs-me. There is no separate notion of a retry.
- **Rationale**: The driver must branch on facts, not prose. SSSF and `sf` both do this; `sf` parks on an unparseable verdict instead of guessing, which is the behaviour adopted here.
- **To verify (task: adapter spike)**: whether `--json-schema` makes the CLI enforce the shape and where the structured value appears in the `result` event. If it works, use it. If not, the prompt asks for a fenced JSON block at the end of the reply and the adapter extracts the last one. Either way the validation lives in the factory's code.

## R6. Keeping a run's changes separate, and the guard

- **Decision**: Each run gets its own git worktree and branch (`factory/<run-id>-<slug>`) created from the target codebase's current commit, under the factory's home directory. Agents work only there. The factory's code makes the commits. After every agent step, code compares what changed against that step's allowed paths:
  - plan, review: nothing may change.
  - write tests: only files under the target's declared test paths.
  - build: anything except the tests written by this run and the target's `.factory.toml`.
  - document: only files under the target's declared documentation paths.
  A violation is undone with git and the run stops as needs-me naming the files (FR-032). The factory also fingerprints its own package directory and the ideals file before and after each step.
- **Rationale**: A worktree leaves the operator's working copy untouched (FR-019). The build-step rule is what makes the cycle honestly test-first: the builder cannot make a failing test pass by editing the test.
- **Alternatives considered**: Working directly on the operator's checkout (simplest, but violates FR-019). A container or VM (the right answer eventually; listed as next stage).
- **Accepted risk**: Tests written by an agent are executed by the test command with the operator's permissions. The guard limits where files are written, not what test code does when run. Sandboxing is out of scope for this stage and this is stated in the README.

## R7. Process handling

- **Decision**: One module, `factory/proc.py`, runs every child process (agents and the test command) the same way:
  1. Start the child in its own session (`start_new_session=True`), with standard input closed and standard error sent to a log file.
  2. Read standard output line by line in the calling thread and hand each line to a callback as it arrives.
  3. A timer enforces the step's time limit by signalling the whole process group — terminate first, kill after a short grace period.
  4. A `finally` block signals the group again on any exit path, so nothing is left running.
  The driver records its own process id in the store. Every command first checks whether a run marked as working still has a live driver; if not, the run is marked needs-me with reason "interrupted" (FR-029).
- **Rationale**: These are the three classic failures the operator has met: a child stalling on a full output pipe, children outliving the parent, and a hung child blocking forever. Continuous reading fixes the first, process groups the second, the timer the third. One agent at a time means no concurrency beyond one reader and one timer.
- **Alternatives considered**: `asyncio` subprocesses (more concepts for the same result). `subprocess.run` with `timeout=` (kills only the direct child and gives no live output).

## R8. Running unattended after approval

- **Decision**: `factory request` and `factory approve` return immediately. Each starts the driver as a detached background process that advances the run until it must wait for the operator or has ended, then notifies and exits. Driver output goes to a per-run log file.
- **Rationale**: "I am not needed between approving the plan and the notification" should survive the operator closing the terminal. The plan step also takes minutes, so the operator gets a "plan ready" notification instead of watching.
- **Alternatives considered**: Running in the foreground (simplest, but dies with the terminal). A long-lived daemon (more than a proof of concept needs; scheduled and triggered runs are next stage).

## R9. Recording

- **Decision**: One SQLite file in the factory's home directory, opened in WAL mode, with four tables: `runs`, `plans`, `steps`, `events`. Every event is inserted as it arrives. Readers poll with one query: events for a run with an id greater than the last one seen. See [data-model.md](data-model.md) and [contracts/run-store.md](contracts/run-store.md).
- **Rationale**: Taken directly from SSSF: the live view and the history are the same query at different cadence, so there is no second code path. WAL lets the observability app read while a run writes.
- **Alternatives considered**: One JSON file per run as `sf` does (inspectable with `cat`, but the observability app would then need its own indexing). Raw event files are still kept per step as the fallback record.

## R10. Ideals

- **Decision**: A free-text Markdown file, `ideals.md`, in the factory's home directory. Its full text is inserted into the plan and review prompts. Each run stores a copy of the text it used (FR-024). Editing the file affects the next run and nothing else (FR-023).
- **Rationale**: The operator wants to state ideals in their own words. Their note `thoughts/2026-11-10-software-design-ideals.md` in the parent project is the natural first content; copying it in is the operator's choice, not something the factory does.
- **Alternatives considered**: Structured rules with machine checks (premature; the spec says ideals are read as written).

## R11. Notification

- **Decision**: `notify-send` for a desktop notification, called by code at two moments: plan ready, and run ended. A notification failure is recorded and never fails the run. The outcome is always in the store regardless (FR-018).
- **Verified**: `/usr/bin/notify-send` is installed.
- **To verify (task: notify)**: that a notification sent from a detached background process reaches the operator's desktop session.

## R12. Where the observability app lives, and its tests

- **Decision**: The app is a separate git repository, a sibling of the factory (`../tomfactory-viewer` by default; the name is the operator's to change). `factory init-target <dir>` creates the repository with one commit and a `.factory.toml` declaring the test command (`python -m pytest -q`), the test paths (`tests/`) and the documentation paths (`docs/`, `CHANGELOG.md`). The app reads the store read-only, at the path given by `TOMFACTORY_HOME`.
- **Rationale**: A separate repository means the build agent's working directory never contains the factory's code, which satisfies FR-030 by layout. The store's schema is the contract between the two.
- **Before the app has tests**: the factory runs the test command once before writing tests, as a baseline. "No tests found" is recorded as "no prior tests" and the run continues. A baseline that fails stops the run as needs-me, because the factory cannot tell its own breakage from breakage that was already there.
- **The test command is read from the target's committed `.factory.toml` at the run's starting commit**, never from the worktree, so an agent cannot change what "passing" means.

## R13. Where the rules live (FR-037, FR-038)

- **Decision**: `factory/workflow.py` holds the ordered list of steps and the single function that, given a step and its result, returns what happens next. Prompts are Markdown files in `prompts/`, one per agent step. Adding a step means adding one prompt file and one entry in the list.
- **Rationale**: SSSF keeps a workflow to about 180 readable lines of Python and deliberately avoids inventing a configuration language. The same reasoning applies here: the operator wants to read the rules, not a YAML dialect and its interpreter.
- **Alternatives considered**: YAML pipelines as in `sf` (more general, but adds a loader, a schema and validation to read).

## R14. Size budget (SC-007)

- **Decision**: The factory's own Python, excluding tests and prompts, stays under 2,000 non-blank lines. A test counts the lines and fails above the limit. (First set at 1,000, then 1,500; as built the code is about 1,760 lines, 1,560 without comments and docstrings. The number is only a stand-in for SC-007's sixty minutes, which the operator measures by reading. Tests are not counted.)
- **Rationale**: "Small enough to read in one sitting" needs a number or it drifts. A code check is in the spirit of the factory.

## R15. Personas (FR-042 to FR-047)

- **Decision**: Each agent step names a persona, a Markdown file in `personas/`. The persona's text is the agent's standing instructions; the step's prompt is the task. Five ship: planner, test writer, code writer, reviewer, documenter. The step record stores the persona's name.
- **Rationale**: The operator wants a test writer that is good at testing and at edge cases, distinct from the code writer. Separating who from what lets one persona serve several steps and lets the operator tune each on its own. SSSF does the same with a system prompt and a user prompt per role.
- **How the difference is made real, not only stated**: the test writer may change only test files and must list the edge cases it considered, which a code check enforces; the code writer may not change the tests; the reviewer starts fresh and sees only the result. A persona's wording is never the only safeguard.
- **To verify (task: adapter spike)**: that `--append-system-prompt` (or `--system-prompt`) carries the persona in non-interactive mode. If not, the persona text is placed at the top of the prompt.
- **Alternatives considered**: One prompt file per step with the persona inside it (duplicates a persona wherever it is reused). Claude Code's own subagent definitions (ties personas to one agent program, against FR-041).

## R16. Changes made to comply with the constitution

The constitution (copied from `bttr_rs`, then amended to 1.3.0) was applied after the first draft of the plan. It changed the design in these ways:

| Rule | Change |
|------|--------|
| S1 | The control layer is four named modules, and adding a step must not touch `store.py` or `cli.py` |
| S3 | `store.py` is four repos, one per table; the runs repo writes the state history behind a plain "set state" call |
| S4 | A new module, `operations.py`, holds the operations on a run; the one-run rule moved there from `cli.py` |
| S5 | Operations return plain data; `cli.py` and the observability app are two mediators over it |
| S7 | Step defaults are closed, each has a named override point, and safety checks are applied by the driver regardless of a step's entry |
| S8 | Every functional requirement is named by at least one test, written and seen to fail before the code; see R17 |
| IV | The final task writes a completion report to the workspace's `/artifacts` and extracts findings to `/knowledge` |

## R17. A test for every requirement, failing first (constitution S8)

- **Decision**: Every test names the requirement it covers with a marker, for example `@pytest.mark.fr("FR-007")`. A gate script, `scripts/traceability.py`, reads the FR numbers out of `spec.md` and fails if any of them is named by no test; `tests/conftest.py` refuses to collect a test with no marker, so S8's "each test MUST name the requirement it covers" holds for every test. Tasks are ordered so that each requirement's tests are written and run red before the code that satisfies them.
- **Rationale**: S8 requires coverage and a failing-first order. Making "every requirement has a test" itself a test means the rule cannot quietly lapse, and it is the factory's own principle (code checks, not promises) applied to its own construction.
- **Requirements that need care**:
  - FR-036 (documentation exists) and FR-038 (rules in one place) are tested by asserting the README has the named sections and that the decision function lives in `workflow.py` alone.
  - FR-039 (size) is the line-count test.
  - FR-040 (works on the subscription) needs the real agent program, so its test is marked `live` and runs on request (`uv run pytest -m live`), not in the default run. It is still written first and seen to fail.
  - FR-017 (notification) is tested against a recording stand-in for the notification command; a `live` test covers the real desktop.
- **Alternatives considered**: A hand-kept traceability table in the plan (drifts as soon as a requirement is added).

## R18. Changes after the independent analysis

`/speckit-analyze` was run by a fresh agent on 2026-11-18 and found 39 issues (8 critical, 17 high). The contracts and tasks were rewritten. **Where this section or a contract differs from R4–R17 above, this section and the contract win.**

| Finding | What was wrong | What changed |
|---------|----------------|--------------|
| Stopping left agents running | Every child starts in its own process group, so signalling the driver's group never reached it; a killed driver ran no clean-up | The run records the child's process-group id while a child runs. `stop` and the interrupted-run check stop that group. The driver handles the terminate signal. One end-of-run routine is used by every ending. Tested with real detached processes. |
| A dead driver could look alive, or a live one dead | The pid was written after the state, and a reused pid looked like the original | The launcher writes state, pid and the process's start time in one update; liveness compares both. |
| The test-first guarantee could be bypassed | "No tests found" counted as a failing run; the code writer could add or edit tests other than this run's | `tests_fail_first` rejects the no-tests exit code; `tests_added` requires a changed test file; the code writer may change nothing under the test paths. |
| Test caches tripped the guard | pytest's cache folders looked like forbidden changes | `init-target` writes a `.gitignore`; the guard honours it; the default test command disables the cache; bytecode writing is off. |
| The spec promised more containment than exists | "Nothing outside the target is altered" cannot hold when agent-written tests are executed | FR-030 to FR-032 now say exactly what is enforced: no shell, edits confined to the checkout, factory code, personas, prompts and ideals fingerprinted and restored from a per-run snapshot. What the test command runs is stated as uncontained. |
| Reads outside the checkout were never tested | The spike only covered edits | The spike now tests reading parent directories and absolute paths, and looks for flags that refuse them. |
| S3: files written outside a repo | Raw event files, standard error and the driver log were opened by other modules | A fifth repo, `files`, in `store.py` owns every per-run file; the adapter receives sinks. |
| S5: operations returned bare dictionaries | No types or constraints | Typed records with allowed values, defined in `store.py`. |
| S8: tests ordered after their code, or unable to fail | Four cases | Live tests are written before the adapter and the notifier; tests that would pass vacuously are seen to fail against a planted violation; first-product tests moved into the cycle tests; every test is marked. |
| FR-042 and FR-043 untestable | Nothing inspected a persona file; "specialise in testing" is not observable | Persona files have three required headings, tested; FR-043 is reworded to what a test can see. |
| Undefined shapes | Step results, the next-step value, check context, prompt placeholders, where attempts are counted | `contracts/workflow.md` now defines all of them, and the step table carries transitions as data, so `next_step` is general and adding a step is one entry. |
| A step record had one check | Steps run several | `checks` is a list on the step record. |
| The driver named steps | It committed "after red, test and document" and stored "the plan" | Those are fields on the step entry (`commit_after`, `on_pass = WAIT`); the driver names no step. |
| Tool names leaked out of the adapter | `workflow.py` listed the agent program's tool names | Steps name neutral capabilities, `read` and `read+edit`; the adapter maps them. |

## Spike results (2026-11-18, task T001)

Run with `spikes/adapter_spike.py` against Claude Code 2.1.327 on the operator's subscription login, using the cheapest model. Raw streams are saved in `tests/fixtures/streams/`: `edits.jsonl`, `reads.jsonl`, `structured.jsonl`, `error.jsonl`.

| Item | Observed | Adopted |
|------|----------|---------|
| (a) Confining edits | With `--tools Read,Glob,Grep,Edit,Write --permission-mode acceptEdits`, a file created inside the working directory succeeded without asking. Creating `../outside.txt` and an absolute path under `/tmp` were both **refused**; neither file existed afterwards. Each refusal appears in the result's `permission_denials` (tool name and input) and as a `system`/`permission_denied` line. | R4 stands. `read+edit` = those tools with `acceptEdits`. |
| (b) Confining reads | Under the same flags, reading `./local.txt` succeeded. Reading `../../ideals.md` and `/etc/hostname` were both **refused** and listed in `permission_denials`; the secret planted in the parent file did not appear in the reply. | An agent cannot read outside its checkout. Constitution S2 holds for reads as well as writes. `read` = `--tools Read,Glob,Grep` with the default permission mode. |
| (c) Isolation | `--setting-sources "" --strict-mcp-config` reduced connected MCP servers from 10 to 0 and the tool count to what `--tools` names. Built-in skills and plugins still load (36→19 skills, 8→4 plugins), and an empty per-directory memory path is still reported. `--bare`, which would remove those too, **exits 1 with no reply** on the subscription login, so it cannot be used. | R4's flags stand; `--bare` is rejected. The remaining built-ins give the agent no extra tools, because `--tools` limits those. |
| (d) Envelopes | `--json-schema` works: the `result` line carries the object in `structured_output`, and the reply text is the same JSON. | **Not used in this stage.** It would mean passing each step's shape through the adapter, which the contract keeps free of shapes. The adapter takes the last JSON object in the reply text; `envelope_valid` checks it. `--json-schema` is a known-good hardening step for later. |
| (e) Persona | `--append-system-prompt` delivered a marker word that the agent repeated when asked. | R15 stands. |
| (f) Tool events | One tool use is one `assistant` line whose `message.content` has a block `{"type":"tool_use","id","name","input"}`. Its outcome is a later `user` line whose `message.content` has a block `{"type":"tool_result","tool_use_id","content","is_error"?}`. Text is an `assistant` line with a `{"type":"text","text"}` block. | The adapter emits one `tool_call` event when the `tool_result` arrives, joined to its `tool_use` by id; `agent_text` for each text block. |
| (g) Errors | An unknown model gives exit code 1, a message on standard error, and a final `result` line with `is_error: true`, `api_error_status: 404` and a readable `result` text. | `ok` is false when the exit code is non-zero or the result has `is_error` true; `error` is the result text, else standard error. |
| Usage limits | Every run prints a `rate_limit_event` line with `rate_limit_info.status` (`allowed` here) and utilisation for the five-hour and seven-day windows. A rejected status was not provoked. | A status that does not begin with `allowed`, or an error result, is reported as the `error` failure with the message. **Corrected after the real runs**: at 90% of the five-hour window the program reports `allowed_warning` and keeps working; the first version of the adapter treated that as a refusal and wrongly failed three successful steps. What a real refusal looks like is still unverified. |

**Lines the adapter must handle**: `system` (subtypes `init`, `permission_denied`), `assistant`, `user`, `rate_limit_event`, `result`. Unknown types are passed to the raw sink and otherwise ignored.

**The `result` line** carries `is_error`, `result` (final text), `duration_ms`, `num_turns`, `total_cost_usd`, `usage` (`input_tokens`, `output_tokens`, cache counts), `permission_denials`, `stop_reason`.

**The command line adopted**:

```text
claude -p <prompt> --output-format stream-json --verbose --no-session-persistence
       --setting-sources "" --strict-mcp-config
       --append-system-prompt <persona text>
       --tools Read,Glob,Grep                         (read)
       --tools Read,Glob,Grep,Edit,Write --permission-mode acceptEdits   (read+edit)
       [--model <model>]
```

**What this does not show**: confinement was tested with direct requests to the file tools. It was not tested against an agent actively trying to get round a refusal, and a later version of the agent program could behave differently. The factory's own fingerprint check and snapshot restore do not depend on these flags.

## R19. Open concern: the repo layer (raised by the operator, 2026-11-18)

After skimming the whole source in about 30 minutes, the operator said: "the only concern i have which can be fixed later is the repo layer. but can just document that somewhere for now and we will get back to it."

**Status**: open, deliberately deferred. Nothing was changed. He did not say what about it concerns him, and that should be asked before anything is redesigned.

**What the repo layer is today** (`factory/store.py`, about 360 non-blank lines, the largest module):

- Five hand-written repo classes, one per table plus one for files: `Runs`, `Plans`, `Steps`, `Events`, `Files`.
- Every query is SQL text written out in the method that uses it. `Runs.update` builds its `SET` clause by formatting column names into a string (the names are checked against a fixed list first, and values are always bound parameters).
- The schema is one SQL string, duplicated in `contracts/run-store.md`.
- Typed records (`Run`, `Plan`, `StepRecord`, `Event`) are built by hand from rows, with JSON columns parsed in each repo.
- Rules such as "ending a run writes its own history event" are coded per method.

**What I think the concern may be — my reading, not his words.** His standing views on repos, from the constitution and from earlier work on bttr, are that a repo is matched to a table by the table's *archetype*, that the machinery (CRUD, history, absence) belongs to the archetype and not to each table, and that a repo's main job is to compose conditions as values, never as formatted SQL text. Measured against that, this layer is the opposite in three ways: it is one bespoke class per table with no archetypes (although the tables have obvious ones — `runs` is an entity with a status history, `events` is an append-only log, `plans` and `steps` are versioned children of a run); it formats SQL text; and it restates per table what an archetype would supply once. It passes constitution S3 as written ("all persistence goes through a repo"), but probably not in the spirit he means.

**If that reading is right**, the rework would be: name the archetypes, let each supply its operations, have conditions composed as values, and derive the schema and the typed records from one description instead of writing each twice. That would shrink `store.py` and remove the SQL text. It is also exactly the kind of change the factory's own tests make safe: `tests/test_store.py` pins the schema and every rule the repos keep.

**Before starting**: ask him to say the concern in a sentence. Do not assume the reading above.

### The concern, in his words (same day, when asked)

"The repo layer at the boundary I was hoping for an API gateway object where you call a function on a table like insert update delete or query. Similar to bttr. That in my mind reduces the ceremony elsewhere that has to interact with that layer. Right now for each table that we invent we need to write a data class and a repo class. That is the current design. I don't like that. I think there's a lot of repeatable code in there, and having specific repo operations should be discouraged; that's business logic hiding in there as far as I'm concerned."

**So the concern is three things:**

1. **The boundary should be one gateway object** with a small fixed set of operations that take a table: insert, update, delete, query. Like bttr.
2. **No per-table ceremony.** Inventing a table must not mean writing a data class and a repo class.
3. **No table-specific repo operations.** They are business logic hiding in the data layer.

My earlier guess was right about the missing generality and wrong in emphasis: it is less about archetypes and SQL text than about the boundary's shape and where logic lives.

**What this means for `store.py` as built.** These are the table-specific operations and the logic each one hides. Under point 3 every one of them belongs in the control layer, or goes away:

| Today | Logic hiding in it |
|-------|--------------------|
| `runs.create` | The branch name and its slug rule; the checkout path; the first state |
| `runs.set_state` | That a state change writes a history event |
| `runs.end` | That state, outcome, reason and end time change together; that the process fields are cleared; that a run ends only once |
| `runs.update` | Which fields may change |
| `runs.open`, `runs.latest` | What "open" and "latest" mean |
| `plans.add` | Version numbering; that a new plan starts as pending |
| `plans.decide`, `plans.current` | What a decision is; which plan is current |
| `steps.start`, `steps.finish` | Attempt numbering; that a step finishes once |
| `steps.count` | What an attempt is |
| `events.after`, `events.for_step` | Two named queries |

**What bttr already settled that applies here** (from `knowledge/technical/2026-11-10-repo-layer-in-rust.md`):

- One gateway holds what does not change (the catalog, the registry). It hands out a unit of work with the operations.
- Rows travel as plain mappings. The application does not hold a type per table; the catalog knows the columns.
- No operation takes SQL text. Conditions are composed as values.
- Events are written by the unit of work, not by a repo, so a table gets them without anyone remembering to.
- A table needs nothing described by hand: the catalog is read from the database.

**Tension to settle with him**: constitution S5 was read strictly during this build as "operations return typed records", which is why there is a data class per table. He has now said he does not want one. The bttr answer is that types and constraints come from the catalog, not from a class per table. S5 as written ("return data, its types and its constraints") is satisfied by that, and better.

## R20. Open request: personas should use the corresponding spec kit command (operator, 2026-11-18)

After reading the personas and prompts, the operator said: "between personas in prompts i would like it if they were instructed to use the corresponding speckit command as part of their work/responsibilities. i didnt see that called out explicitly."

**Status**: open, for a later stage. Nothing was changed. As built, each agent step uses only its own file in `personas/` and `prompts/`; no persona or prompt mentions spec kit.

**What it would take — my notes, not his words.**

- *Which command goes with which persona* is his to decide. An obvious first guess: planner with `/speckit-specify` and `/speckit-plan`; test writer and code writer working from `/speckit-tasks` output, the code writer through `/speckit-implement`; reviewer with `/speckit-analyze` or `/speckit-converge`. The documenter has no obvious counterpart.
- *Two things in the current design stand in the way*, and both are deliberate, so they need a decision and not a workaround:
  1. **Agents have no shell.** Spec kit's commands run shell scripts under `.specify/scripts/` (to find the feature folder, copy templates, and so on). A read-and-edit-only agent cannot run them. Either the factory's code runs those scripts on the agent's behalf before the step, which keeps "agents propose, code disposes", or some steps get a restricted shell.
  2. **Agents are isolated from project settings.** Runs start the agent program with the operator's and the project's settings switched off, so a target's spec kit skills are not loaded. The command's instructions would have to be given to the agent in its prompt, or that isolation relaxed for the target's own skills.
- *It changes what a run produces.* Spec kit writes `spec.md`, `plan.md` and `tasks.md` into the target. The plan the operator approves would become those files, `may_change` for the planner would no longer be "nothing", and the wait would move to after them.
- The target must have spec kit set up (`.specify/`), which `factory init-target` does not do today.

This overlaps with the next-stage item "using spec kit's own steps as the cycle" and should be designed together with it.

## R21. The architect persona (added at the operator's request, 2026-11-18)

The operator asked, while the build was in progress: "theres a persona i would like to add which is architect. that can do code reviews, and point out code maintenance quality things like too much repeated code etc..... my ideal would be a lisp thinker (to me that covers all the fashionable pardigms throughout the years and knows the strengths and weaknesses of a given choice). suggests or warns that gets documented as backlog if it cant be immediately be addressed. its a code review that shouldnt necessarirly fail the run. architect may also be useful in planning."

**Built now**, as FR-048 to FR-050:

- A persona, `personas/architect.md`, written from his description: a Lisp thinker who knows each paradigm as a tool with strengths and weaknesses; looks for repeated code, blurred boundaries and the wrong tool for the job; suggests and warns; never blocks.
- A step, `architecture_review`, after the tests pass and before the documentation. It may write only under the documentation paths, where it keeps `docs/backlog.md`. Its envelope carries the same suggestions and warnings onto the run's record.
- A new field on a step entry, `advisory`. An advisory step that fails — malformed reply, time-out, agent program error — is recorded and the run carries on. An advisory step that changes what it may not is still undone and still stops the run: advice is not a licence.
- The reviewer is told the backlog is advice, so a note there is not by itself a reason to reject.

**How it was added** is itself a test of the design: one field and one rule in `workflow.py`, one table entry, one persona file, one prompt file. `driver.py`, `store.py`, `cli.py` and `operations.py` were not touched.

**Deferred — "if it can't be immediately addressed".** As built, everything the architect finds goes to the backlog; nothing is sent back to the code writer in the same run. Addressing a finding immediately would mean a second rework loop, which the spec's assumptions rule out for this stage ("a rejecting review ends the run; only failing tests cause rework"). A backlog entry can be handed to the factory as a request of its own.

**Deferred — "architect may also be useful in planning".** Having the architect advise the planner, or review the plan before the operator sees it, is not built. It would be a second advisory step before the wait, and it raises a question worth his answer first: should the operator see the architect's view of a plan alongside the plan, or should the planner fold it in?

## R22. Open decision: what counts as the scope of a run (operator, 2026-11-18)

When told that later steps now see the request together with his plan-stage comments, the operator said: "but thats enabling scope creep so we will probably want to undo that. i mean scope creep is fine but it should go back up the waterfall to at least make sure it doesnt blow the plan. I guess what im saying is, just bc im asking for it doesnt mean i want it right now in the middle of a run."

**What is already true**: nothing can be added in the middle of a run. A comment can only be made while a plan is waiting, it goes to the planner, and the operator approves the revised plan before any work starts. After approval a run takes no input.

**What is open**: how the reviewer decides what was asked for. Two options were put to him and he has not chosen:

1. *As built*: later steps see the request plus the operator's plan-stage comments.
2. *The plan is the scope*: undo that, and tell the reviewer that the approved plan defines what was asked for, because the operator approved it. The reviewer then stops checking the plan against the request, which becomes the operator's job at approval.

My recommendation is option 2, as closer to what he said. Nothing was changed pending his answer.

**A gap his point exposes**: there is no way to note "I also want this, later" while a run is under way. The architect's backlog file would be a natural home for it.

### Resolved in principle (same day)

The operator's ruling: "For scope I think the plan needs to be aligned with whatever artifacts are produced. So if something is introduced midstream it needs to be assessed on whether it actually changes the requirement or is simply an implementation detail. If it changes the requirement then it needs to go back to the planning stage."

So the scope of a run is the approved plan, and the test is alignment between plan and artifacts:

- a difference that is an implementation detail is acceptable;
- a difference that changes the requirement sends the run back to planning, which means back to the operator's approval.

This is neither of the two options first offered. It is not yet built. The comments-travel change stays in place until it is replaced. The design is in `changes/2026-11-18-spec-kit-cycle.md`, because spec kit's converge stage is this same assessment.

**Also ruled the same day**: size "is not a thing that matters necessarily" at this point. The line-count limit was raised to 3,500 and kept only as a tripwire.

## R23. Idea: an expert panel before the plan, and a factory per project (operator, 2026-11-18)

The operator said, after the first real runs: "Initially I was thinking we need to put in a optional first step in the planning stage which is assembling an expert panel via persona descriptions or something and they have to all align and iterate on the requirements so for example if the project is just starting as in there is no code just an idea then maybe there needs to be a validation step as far as the likelihood of making money if that is a goal then what features should be made a priority first things like that it could almost mean that the factory is per project and can have its own custom conditions and steps."

**Status**: an idea, not yet a requirement. Nothing was built. He raised it while saying he wants to address technical debt first.

**The parts of it, in his terms:**

- An *optional* first step in planning: a panel of experts, each a persona description.
- They must align, and iterate on the requirements, before a plan is made.
- For a project that is only an idea: a validation step, such as how likely it is to make money if that is the goal, and which features come first.
- The consequence he drew: the factory may need to be per project, with its own conditions and steps.

**Connections worth having in view — mine, not his words:**

- *The last point is nearly true already.* The steps are a table of data and the personas are files, so a different project could have a different table. What is missing is where they live: today the table, personas and prompts belong to the factory, not to the target codebase. Letting a target carry its own would make "a factory per project" a matter of where files are read from.
- *He already has an expert panel.* The board personas used for bttr reviews, loaded into Hive, are a panel of this kind. They could be the first panel, instead of new personas.
- *Spec kit already has this stage.* Its assess commands (intake, define, research, shape, decide) take a raw idea through problem definition, evidence and a go, clarify or kill decision. That is the validation step for a project that is only an idea, and it overlaps with R20 (personas using spec kit commands).
- *A panel that must align is a loop with a stopping rule*, like the test rework loop: it needs a limit and a way to hand an unresolved disagreement to the operator.
- *Its output is requirements, not a plan*, so it sits before the plan step and the operator's approval would then cover both.

## Open items carried into tasks

| Item | Proven by | If it fails |
|------|-----------|-------------|
| Edits outside the working directory can be refused | adapter spike | rely on the fingerprint check and snapshot restore for the factory's own files; state the gap in the README |
| Reads outside the working directory can be refused | adapter spike | state plainly in the README and the completion report that an agent can read files this user can read |
| `--setting-sources ""` isolates runs from the operator's settings | adapter spike | try `--bare`; record the result |
| `--json-schema` enforces envelopes | adapter spike | fenced JSON block parsed by the adapter |
| The persona reaches the agent as standing instructions | adapter spike | put the persona at the top of the prompt |
| Desktop notification from a detached process | notify task | pass the session bus address explicitly; fall back to the log and `factory status` |
