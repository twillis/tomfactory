# Contract: The Workflow

`factory/tables.py` says which steps exist and in what order, and `factory/workflow.py` what happens after each (FR-038): the tables are data, and the rules are small pure functions, chief among them `next_step`, that read them. It does no input or output. This document is that file's specification.

## A step entry

Every step is one entry with these fields. Defaults are closed: an entry that says nothing gets the most restrictive value.

| Field | Meaning | Default |
|-------|---------|---------|
| `name` | The step's name, unique in the table | required |
| `kind` | `agent` or `code` | required |
| `persona` | Agent steps: the name of a file in `personas/` | required for agent steps; constructing an agent step without one raises |
| `capabilities` | Agent steps: `read`, or `read+edit`. Neutral names; only the adapter knows which tools they mean | `read` |
| `may_change` | What the step may change in the checkout: `nothing`, `tests`, `not_tests`, `docs` or `spec` (defined below) | `nothing` |
| `inputs` | Agent steps: the names of the inputs its prompt receives, from the list below | `()` |
| `envelope` | Agent steps: required keys and their types (`text`, `list`, `verdict`) | `{}` |
| `checks` | Names of step-specific checks, run in order after the always-applied ones | `()` |
| `on_pass` | The next step's name, or `WAIT`, or `END_ACCEPTED` | required |
| `on_fail` | What a failed step-specific check leads to: `Rework(step)` or `End(outcome)` | `End("needs-me")` |
| `commit_after` | Commit the checkout to the run's branch when the step passes | no |
| `speckit` | Spec kit commands this step follows where the target uses spec kit, for example `("specify", "plan")`. The factory's code runs their scripts; the agent is given their instructions. | none |
| `routes` | For a step that judges: where each verdict other than `accept` leads — `Rework(step)`, `Replan(step)` or `End(outcome)` | none |
| `revise_from` | For a step the run waits after: where "send it back" returns to. The start of the stage. | the step itself |
| `advisory` | The step's failure is recorded but does not stop the run, and whatever it changed before failing is put back, so a half-written file cannot be committed by the next step. A change it may not make is still undone and still stops the run. | no |
| `timeout` | Seconds; overrides the target's `step_timeout_seconds` | none |
| `model` | Agent steps: passed to the adapter; unused in this stage | none |

A code step has no persona, capabilities, inputs or envelope. Its work is its checks: a code step runs its named checks and passes if they all pass.

## The steps

| # | `name` | `kind` | `persona` | `capabilities` | `may_change` | `checks` | `on_pass` | `on_fail` | `commit_after` |
|---|--------|--------|-----------|----------------|--------------|----------|-----------|-----------|----------------|
| 1 | `plan` | agent | `planner` | read+edit | spec | — | `WAIT` | — | yes |
| 2 | `baseline` | code | — | — | nothing | `baseline` | `write_tests` | `End("needs-me")` | no |
| 3 | `write_tests` | agent | `test_writer` | read+edit | tests | `tests_added`, `tests_within_budget`, `edge_cases_stated` | `red` | `Rework("write_tests")` | no |
| 4 | `red` | code | — | — | nothing | `tests_fail_first` | `build` | `Rework("write_tests")` | yes |
| 5 | `build` | agent | `code_writer` | read+edit | not_tests | — | `test` | route: `test_defect` → `Rework("mend_tests", at_most=2, then="test", once_per_test=True)` (FR-097, FR-150) | no |
| — | `mend_tests` | agent | `test_writer` | read+edit | tests | `tests_within_budget` | `test` | `Rework("mend_tests")` | no |
| 6 | `test` | code | — | — | nothing | `tests_pass` | `architecture_review` | `Rework("build")` | yes |
| 7 | `architecture_review` | agent | `architect` | read+edit | docs | — | `document` | — (advisory) | yes |
| 8 | `document` | agent | `documenter` | read+edit | docs | — | `review` | — | yes |
| 9 | `review` | agent | `reviewer` | read | nothing | `verdict`; routes `reject` → `End("rejected")` | `finish` | `Rework("review")` (a reply that contradicts itself) | no |
| 10 | `finish` | code | — | — | nothing | — | `END_ACCEPTED` | — | no |

`architecture_review` is the one advisory step. The architect reviews the change for maintainability and adds its suggestions and warnings to `docs/backlog.md` in the target; its envelope puts the same findings on the run's record. Nothing it finds, and no way it can fail short of changing what it may not, stops the run (FR-048 to FR-050).

The branch history of an accepted run therefore reads: tests, then the change, then the documentation — three commits.

**Documentation is written before the review, not after.** The first real run (2026-11-18) showed why: the reviewer judges the result against the approved plan, the plan included documentation, and with the review placed first the documentation did not yet exist, so a correct change was rejected. The reviewer now sees the whole change.

`WAIT` after `plan` means: store the step's envelope as a new plan version, set the run to `awaiting_approval`, notify the operator, and stop. The operator's three decisions are also in `workflow.py`, as `after_wait(decision)`:

| Decision | Result |
|----------|--------|
| approve | continue at the waiting step's successor, here `baseline` |
| revise, with a comment | run the waiting step again, here `plan` |
| abandon | `End("rejected")`, reason "abandoned by operator" |

## Two tables: the table is chosen by the codebase (FR-055)

`tables.table_for(spec_kit, run_kind)` returns, for a change, the plain table above for a codebase without spec kit, and the table below for one that has it. Both are data in `tables.py`; the driver and the operations take whichever applies and name no step.

| # | `name` | `persona` | spec kit stage | `may_change` | `on_pass` | notes |
|---|--------|-----------|----------------|--------------|-----------|-------|
| 1 | `specify` | `analyst` | specify | spec | `clarify` | commits |
| 2 | `clarify` | `analyst` | clarify | spec | `WAIT` | commits; `revise_from="specify"`. First approval: the specification |
| 3 | `plan` | `planner` | plan | spec | `tasks` | commits |
| 4 | `tasks` | `planner` | tasks | spec | `analyze` | commits |
| 5 | `analyze` | `reviewer` | analyze, checklist | nothing | `WAIT` | `revise_from="plan"`. Second approval: plan and tasks |
| 6–10 | `baseline`, `write_tests`, `red`, `build`, `test` | as in the plain table | implement, for the two writers | as in the plain table | | |
| 11–12 | `architecture_review`, `document` | as in the plain table | — | | `document` leads to `converge` | |
| 13 | `converge` | `reviewer` | converge | nothing | `finish` | routes: `rework` → `Rework("build")`, `replan` → `Replan("specify")`, `reject` → `End("rejected")` |
| 14 | `finish` | — | — | nothing | `END_ACCEPTED` | |

### A step that judges (FR-058, FR-059)

A step with `routes` gives a verdict in its envelope. The check `verdict` is applied to it automatically: it passes on `accept`, and otherwise fails with the reasons as its note. `next_step` then follows the route for that verdict:

| Route | What happens |
|-------|--------------|
| `Rework(step)` | That step runs again, told what was found. Bounded by the attempt limit. With `at_most`, once that step has run that many times the route goes on to `then`. With `once_per_test`, it is taken only for a report naming a test no earlier report in the run named (FR-150). |
| `Replan(step)` | The driver sets the build aside, and the run returns to that step in the planning stage, told what was found. It reaches a wait again. Bounded by the attempt limit on that step. |
| `End(outcome)` | The run ends. |

### Setting a build aside (FR-060)

On `Replan`, the driver commits whatever is in the checkout, puts a branch `<run's branch>-aside-<n>` on it, and returns the checkout to the commit recorded at the last approval (an `approved` event carries it). A `set_aside` event names the branch. The run then replans; after the operator approves again the cycle starts from `baseline` on the newly approved documents, so tests are again written and seen to fail before the code.

### Waiting more than once (FR-057)

Any step may have `on_pass=WAIT`. `after_wait("approve", …)` continues at the next entry in the table; `after_wait("revise", …)` returns to the step's `revise_from`. A run's state is `planning` up to and including the last waiting step, and `working` after it.

## Kinds of run (FR-066)

`tables.table_for(spec_kit, run_kind)` chooses the table from `tables.RUN_KINDS`. A run's kind is stored on it (`runs.run_kind`), and `driver.table_of(run)` is the one place a run's table is decided, from its own checkout. What the planner and reviewer are told about each kind is in `prompts/run_kinds/`.

| Kind | Table | For |
|------|-------|-----|
| `change` (the default) | the plain table, or the spec kit table where the codebase uses spec kit | Anything that changes behaviour. Tests are written and seen to fail first. |
| `tidy-tests` | `plan` → *wait* → `baseline` → `tidy_tests` (test writer; may change tests only) → `test` → `review` → `finish` | Making the tests smaller or clearer. The code is held still. |
| `tidy-code` | `plan` → *wait* → `baseline` → `tidy_code` (code writer; may change anything but tests) → `test` → `review` → `finish` | Reshaping the code. The tests are held still. |

In a tidy run nothing is required to fail first. The tests must pass before (`baseline`; a failure ends the run) and after (`test`; a failure sends the work back to the tidy step, within the attempt limit).

## Checks

A check is a named function in `factory/checks.py`, registered by name, with the signature `check(context) -> CheckResult`. Types are in "Types" below.

**Always applied by the driver to every step**, whatever its entry says (constitution S7 — an entry cannot leave these out):

| Check | Passes when |
|-------|-------------|
| `factory_untouched` | the factory's package folder, `personas/`, `prompts/` and `ideals.md` have the same fingerprint as before the step |
| `changes_allowed` | every file the step changed in the checkout is within the step's `may_change` scope |
| `envelope_valid` (agent steps only) | the reply ended with a JSON object carrying every required key with the right type |

**Step-specific**, named in an entry's `checks`:

| Check | Passes when |
|-------|-------------|
| `baseline` | the test command exits 0, or exits with the target's `no_tests_exit_code` (recorded as "no prior tests") |
| `tests_added` | the step changed at least one file under the target's `test_paths` |
| `tests_within_budget` | the lines the step added under the test paths are no more than the target's `test_budget_lines`; 0 means no limit (FR-065) |
| `edge_cases_stated` | the envelope's `edge_cases` list has at least one entry (FR-045) |
| `tests_fail_first` | the test command exits non-zero **and** not with `no_tests_exit_code` (FR-007). "No tests found" is not a failing test. Where the target names a `red_command`, it is run first on the run's own test files, and settles the check when it exits so **and** its test report names a failing test; anything else but a timeout is settled by the whole suite (FR-152). |
| `tests_pass` | the test command exits 0 (FR-008) |
| `verdict` | given to every judging step (one with `routes`): the verdict is `accept`, and the reply does not name broken ideals while accepting (SC-009). A failed verdict leads where the step's route for it says; a reply that contradicts itself leads to `on_fail`. |

The three checks that run the test command (`baseline`, `tests_fail_first`, `tests_pass`) run it contained (feature 002, `factory/sandbox.py`). If it cannot be contained, the step fails as `error` and the run ends as needs-me without running the tests.

### `may_change` scopes

"Changed" means the files git reports as added, modified or deleted in the checkout after the step that it did not report before the step. The target's `.gitignore` is honoured, so caches do not count.

| Scope | A changed file is allowed when |
|-------|--------------------------------|
| `nothing` | never |
| `tests` | it is under one of the target's `test_paths` |
| `not_tests` | it is **not** under any `test_paths`, and it is not `.factory.toml` or `.gitignore` |
| `docs` | it is under one of the target's `docs_paths` |
| `spec` | the target uses spec kit, **and** the file is under `specs/` or is `.specify/feature.json`. In a target without spec kit this scope allows nothing. |

`not_tests` is what keeps the cycle honestly test-first: the code writer cannot edit, delete or add anything under the test paths, including the tests written in this run, the target's older tests, and shared test set-up files.

## What happens next

`next_step(step, result, attempts, limit) -> Next` is the whole decision logic. `attempts` maps a step name to how many times it has run in this run. It is a pure function.

Rules, in the order they are applied:

| # | Situation | Result |
|---|-----------|--------|
| 1 | `factory_untouched` or `changes_allowed` failed | the driver undoes the change; `End("needs-me")`, naming the files |
| 2 | The step is advisory and failed in any other way | carry on to its `on_pass`; the failure stays on its step record |
| 3 | The step timed out | `End("needs-me")`, naming the step and the time limit |
| 4 | The agent program failed (an error, or a usage limit), or refused to let the agent edit a file inside its own checkout | `End("needs-me")`, carrying the program's message or the refused paths. Trying again cannot help, so no attempt is spent on it. |
| 5 | `envelope_valid` failed | `Rework(this step)` |
| 6 | A step-specific check failed | the entry's `on_fail` |
| 7 | Everything passed | the entry's `on_pass` |

And one rule about rework:

| Situation | Result |
|-----------|--------|
| The result is `Rework(target)` and `attempts[target]` is already `limit` | `End("needs-me")`, naming the target step, the count, and the failure that caused the last rework |

**An attempt is one execution of a step.** Every execution creates a step record and counts, whatever the reason for it. There is no separate notion of a retry. With the default limit of 3, a step can run at most three times in a run. Sending a plan back with a comment is the operator's decision and does not count.

When a step is run again because of a rework, it receives the `failure` input: the failed check's name and note, including the test output where there is some.

## Inputs and prompts

An agent step's prompt is `prompts/<step name>.md` with placeholders written `{{name}}`. The driver replaces each with the named input. An input with nothing to give is replaced with `(none)`. A placeholder naming an input the step's entry does not list is an error.

| Input | What it is |
|-------|-----------|
| `request` | The operator's request, followed by every comment the operator made when sending a plan back. Later steps, the reviewer above all, must judge against what the operator asked for in total. |
| `constitution` | The target codebase's own constitution (`.specify/memory/constitution.md`), or "This codebase has no constitution of its own." An unfilled template counts as none. |
| `ideals` | The ideals text stored on the run, or "No ideals have been stated." |
| `plan` | The approved plan's text |
| `previous_plan` | On a revision: the plan version that was sent back |
| `comment` | On a revision: the operator's comment |
| `test_paths` | The target's test paths |
| `docs_paths` | The target's documentation paths |
| `test_files` | The test files this run's `write_tests` step changed |
| `limits` | The target's `line_length` and `test_budget_lines`, or that it sets none, to write within; measured after as smells, never gates (FR-153) |
| `failure` | On a rework: the failed check and its note |
| `speckit_instructions` | Where the target uses spec kit and the step names commands: the instruction text of those commands, from the target's own copy |
| `speckit_context` | What spec kit's scripts set up for this step: the feature directory and the paths of its documents |
| `diff` | The run's whole change so far, as a diff, without the run's own record under `docs/runs/` (FR-099) |
| `test_output` | The output of the most recent test command run |

| Step | `inputs` |
|------|----------|
| `plan` | `request`, `constitution`, `ideals`, `previous_plan`, `comment`, `failure`, `speckit_instructions`, `speckit_context` |
| `write_tests` | `request`, `plan`, `test_paths`, `limits` (FR-153), `failure` |
| `build` | `request`, `plan`, `constitution`, `ideals`, `test_files`, `limits`, `failure` |
| `mend_tests` | `request`, `plan`, `test_paths`, `limits`, `failure`, `defective_tests`, `failing_tests` (FR-150) |
| `architecture_review` | `request`, `plan`, `constitution`, `ideals`, `diff`, `docs_paths` |
| `document` | `request`, `plan`, `diff`, `docs_paths` |
| `review` | `request`, `plan`, `constitution`, `ideals`, `diff`, `test_output` |

Each agent step starts fresh. Nothing is carried between steps except its inputs, so the reviewer never continues the code writer's conversation (FR-044).

### Order of precedence (FR-054)

Every step that is given the operator's ideals is also given the target codebase's constitution, and its prompt states the order, as the operator ruled on 2026-11-18:

1. the target codebase's own constitution — local to the repository being worked on
2. the operator's ideals — the factory's constitution
3. spec kit's own instructions

Where two disagree, the earlier wins, and the agent is told to say so. The steps are `plan`, `build`, `architecture_review` and `review`.

## Questions (FR-061 to FR-064)

Any agent step may end its reply with only `{"question": "..."}` instead of its envelope. Every agent prompt whose step `may_ask` is given a shared part (`prompts/fragments/asking.md`) saying how, together with the questions that step asked earlier in the run and their answers.

| What happens | Where |
|--------------|-------|
| The question is recorded at once, with the step and persona that asked | `records.ask` |
| `next_step` returns `Ask(question)`; or, if the step has used its attempts, `End("needs-me")` | `workflow.py` |
| The lead (`workflow.LEAD`: persona `lead`, read-only, envelope `answer` and `confident`) is run. It is a step like any other: recorded, checked, and unable to change anything | the driver |
| `confident` is `yes`: the answer is recorded as the lead's, and the step that asked runs again | the driver |
| Otherwise, or if the lead fails: the run is set to `awaiting_approval` at the step that asked, and the operator is notified | the driver |
| The operator answers: recorded as the operator's, and a driver is launched at the step that asked | `operations.answer` |

A step that asks is recorded as failed, with a check named `question` carrying the question. An advisory step that asks is simply carried past. `approve` and `revise` are refused while a question is waiting; `abandon` is not.

## Envelopes

Each agent step must end its reply with one JSON object. Required keys and types:

| Step | Key | Type |
|------|-----|------|
| `plan` | `plan` | text |
| | `ideals_addressed` | list |
| | `conflicts` | list |
| `write_tests` | `summary` | text |
| | `test_files` | list |
| | `edge_cases` | list |
| `build` | `summary` | text |
| | `files_changed` | list |
| | `verdict` | `accept`, or `test_defect` (FR-097) |
| | `reasons` | list |
| | `defective_tests` | list: the id of each test reported (FR-150) |
| `mend_tests` | `summary` | text |
| | `mended` | list |
| `architecture_review` | `summary` | text |
| | `suggestions` | list |
| | `warnings` | list |
| `review` | `verdict` | verdict: `accept` or `reject` |
| | `reasons` | list |
| | `ideals_broken` | list |
| `document` | `summary` | text |
| | `files_changed` | list |

A missing key or a wrong type is a malformed envelope (rule 4). An `edge_cases` list that is present but empty is a failed `edge_cases_stated` check (rule 5). Both lead to `Rework("write_tests")`.

File lists in envelopes are the agent's own account and are recorded as given. The factory decides what changed from git alone.

## Personas

Each agent step is carried out by a persona: a Markdown file in `personas/` (FR-042). The persona is the agent's standing instructions; the step's prompt is the task. Every persona file has exactly these three headings, each with text under it:

```markdown
## Expertise
## Priorities
## Must not
```

| Persona | File | Serves | Must not |
|---------|------|--------|----------|
| planner | `personas/planner.md` | `plan` | change anything |
| test writer | `personas/test_writer.md` | `write_tests` | write the implementation |
| code writer | `personas/code_writer.md` | `build` | edit the tests |
| architect | `personas/architect.md` | `architecture_review` | change code or tests; reject the change |
| reviewer | `personas/reviewer.md` | `review` | change anything |
| documenter | `personas/documenter.md` | `document` | change code or tests |

Each "must not" is enforced by `may_change`; the persona's wording is never the only safeguard. The test writer's Priorities must direct it to cover edge cases and failure cases before the main path (FR-043).

## Types

These are plain dataclasses in `factory/workflow.py` and `factory/checks.py`.

```text
Step            the entry described above

CheckContext    run            the run record
                step           the Step
                checkout       the run's Workspace
                target_config  the target's configuration at the base commit
                changed        files the step changed, from git
                envelope       the parsed envelope, or None
                before         the factory fingerprint taken before the step
                factory_paths  what that fingerprint covers
                stderr_file, on_child, timeout
                               for a check that runs a command

CheckResult     name           the check's name
                passed         bool
                note           why it failed, or a short remark
                output         what a command it ran printed
                contained      for a check that ran the target's tests: {"network": bool}
                timed_out      the check ran a command that hit the time limit; the step then
                               fails as "timeout", not "check"

StepResult      passed         bool
                failure        None, or one of workflow.FAILURES: timeout | error | guard | malformed | check | question
                failed_check   the CheckResult that failed, or None
                message        the agent program's message, for "error"

Next            one of:
                Run(step_name)
                Wait()
                End(outcome, reason)       outcome: accepted | rejected | needs-me
```

## How the driver uses this

The driver is general: it names no step and no persona. For the run's `current_step`, it:

1. Takes a fingerprint and notes what git reports.
2. Starts a step record and writes a `step_start` event.
3. For an agent step: loads the persona and prompt, fills the inputs, calls the adapter, records each event. For a code step: does nothing here.
4. Runs the always-applied checks, then the entry's checks, stopping at the first failure. Writes a `check` event for each.
5. If a guard check failed, undoes the change and writes a `guard` event. For the factory's own files, the changed versions are first copied to the run's `displaced/` folder, so an operator who edited them mid-run loses nothing.
6. If the step passed and `commit_after` is set, commits and writes a `commit` event.
7. Completes the step record and writes a `step_end` event.
8. Calls `next_step`. On `Run`, sets `current_step` and repeats. On `Wait`, stores the plan version, sets `awaiting_approval`, notifies, and exits. On `End`, calls the single end-of-run routine.

**Every ending goes through one routine**, `end_run(run, outcome, reason)`: it sets the state, outcome and reason through the runs repo, stops any child process still recorded on the run, clears the process fields, and sends the "run ended" notification. The driver, `stop`, `abandon` and the interrupted-run check all use it, so no ending can skip the outcome, the reason or the notification (FR-015 to FR-017).

## Adding a step (FR-037)

1. For an agent step: write `prompts/<name>.md`, and name an existing persona or write `personas/<name>.md` with the three headings.
2. For a code step that needs a new check: write the function in `factory/checks.py` and register it by name.
3. Add one entry to the table in `factory/workflow.py`, and point the previous step's `on_pass` at it.

No existing step's behaviour changes, and `store.py`, `cli.py` and `driver.py` are not touched. A test proves this by registering a check and inserting an entry from outside the package.
