# Contract: The Workflow

`factory/workflow.py` is the one place that says which steps exist, in what order, and what happens after each (FR-038). It holds a table of step entries and one small function, `next_step`, that reads the table. It does no input or output. This document is that file's specification.

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
| `advisory` | The step's failure is recorded but does not stop the run, and whatever it changed before failing is put back, so a half-written file cannot be committed by the next step. A change it may not make is still undone and still stops the run. | no |
| `timeout` | Seconds; overrides the target's `step_timeout_seconds` | none |
| `model` | Agent steps: passed to the adapter; unused in this stage | none |

A code step has no persona, capabilities, inputs or envelope. Its work is its checks: a code step runs its named checks and passes if they all pass.

## The steps

| # | `name` | `kind` | `persona` | `capabilities` | `may_change` | `checks` | `on_pass` | `on_fail` | `commit_after` |
|---|--------|--------|-----------|----------------|--------------|----------|-----------|-----------|----------------|
| 1 | `plan` | agent | `planner` | read+edit | spec | — | `WAIT` | — | yes |
| 2 | `baseline` | code | — | — | nothing | `baseline` | `write_tests` | `End("needs-me")` | no |
| 3 | `write_tests` | agent | `test_writer` | read+edit | tests | `tests_added`, `edge_cases_stated` | `red` | `Rework("write_tests")` | no |
| 4 | `red` | code | — | — | nothing | `tests_fail_first` | `build` | `Rework("write_tests")` | yes |
| 5 | `build` | agent | `code_writer` | read+edit | not_tests | — | `test` | — | no |
| 6 | `test` | code | — | — | nothing | `tests_pass` | `architecture_review` | `Rework("build")` | yes |
| 7 | `architecture_review` | agent | `architect` | read+edit | docs | — | `document` | — (advisory) | yes |
| 8 | `document` | agent | `documenter` | read+edit | docs | — | `review` | — | yes |
| 9 | `review` | agent | `reviewer` | read | nothing | `verdict_accept` | `finish` | `End("rejected")` | no |
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
| `edge_cases_stated` | the envelope's `edge_cases` list has at least one entry (FR-045) |
| `tests_fail_first` | the test command exits non-zero **and** not with `no_tests_exit_code` (FR-007). "No tests found" is not a failing test. |
| `tests_pass` | the test command exits 0 (FR-008) |
| `verdict_accept` | the envelope's `verdict` is `accept` |

`envelope_valid` also enforces one cross-field rule: a review envelope that lists any broken ideal with the verdict `accept` is malformed (SC-009).

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
| `failure` | On a rework: the failed check and its note |
| `speckit_instructions` | Where the target uses spec kit and the step names commands: the instruction text of those commands, from the target's own copy |
| `speckit_context` | What spec kit's scripts set up for this step: the feature directory and the paths of its documents |
| `diff` | The run's whole change so far, as a diff |
| `test_output` | The output of the most recent test command run |

| Step | `inputs` |
|------|----------|
| `plan` | `request`, `constitution`, `ideals`, `previous_plan`, `comment`, `failure`, `speckit_instructions`, `speckit_context` |
| `write_tests` | `request`, `plan`, `test_paths`, `failure` |
| `build` | `request`, `plan`, `constitution`, `ideals`, `test_files`, `failure` |
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
                note           why it failed, or a short remark; may hold test output
                timed_out      the check ran a command that hit the time limit; the step then
                               fails as "timeout", not "check"

StepResult      passed         bool
                failure        None | "timeout" | "error" | "guard" | "malformed" | "check"
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
