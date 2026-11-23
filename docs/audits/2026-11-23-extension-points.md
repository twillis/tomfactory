# Audit: what decides how a run goes, and what a project could set

2026-11-23. Read: `README.md`, `factory/*.py` (workflow, tables, driver, checks, config, agent, run_record,
records, operations, sandbox, speckit, own_files), `prompts/`, `personas/`, `orchestrator/playbook.md`,
`specs/001-near-loop-factory/spec.md`, `specs/002-contain-target-code/spec.md`, `specs/003-fitness-and-feedback/spec.md`
(part 2), `docs/suggestions.md`, the change records' git history, and bttr_erp's committed `.factory.toml`.
No code was run and no file was changed but this one. Line numbers are as of commit `6704670` of bttr_erp and the
factory's working tree today. Where I infer rather than read, I say so.

The operator's goal: "To be able to quickly configure how a run goes without changing the factory code would be
killer. Provide factory primitives you tailor over time to your project."

## The short answer

The factory is already built from data. A run is a list of `Step` entries (`workflow.py:108-151`) read by one pure
function (`workflow.next_step`, `workflow.py:222-262`); checks, inputs and personas are looked up by name; a table is
validated before any paid step (`driver.py:456-487`). What is missing is only *where* that data may come from: every
table, every persona and every prompt is the factory's own, shared by every target. What a project sets today is the
15 fields of `TargetConfig` (`config.py:33-51`) plus two committed files (`IDEALS.md`, the constitution); everything
about the steps themselves (order, routes, caps, checks, smells, grades, personas, prompts, per-step time) needs a
factory edit; and a handful of guards must stay closed. Most of the factory edits of the last five days were per-project tuning made globally:
model grades (FR-109), which steps carry which smells (FR-107, run 78), coverage on the test step (FR-110).

The first step I propose is small: let `.factory.toml` override a short, whitelisted list of fields on the existing
step entries, by name, and print the table a run will actually use. Everything later builds on that one seam.

## 1. Inventory

Key: **(a)** set per project in `.factory.toml` today; **(b)** changeable only by editing factory code or the
factory's own files; **(c)** hard-coded, and risky to open.

### Which steps, in what order, and where they lead

| Decision | Where | Today | Note |
|---|---|---|---|
| Which table a run uses: kind x cycle x spec kit | `tables.py:192-209`, `driver.py:37-40` | cycle (a); kinds and tables (b) | `cycle` is the one routing choice a project has (FR-093). Spec kit is detected from the run's *checkout* (`driver.py:40`), see finding F2 |
| The kinds of run | `tables.py:192-196`, `operations.py:105-107` | (b) | `change`, `tidy-tests`, `tidy-code`; each has a `prompts/run_kinds/<kind>.md` |
| Step order (`on_pass`) | every entry in `tables.py:12-186` | (b) | |
| What a failed check leads to (`on_fail`) | e.g. `tables.py:29` red→write_tests, `:48` test→build | (b) | Only `Rework` or `End` (`workflow.py:121`) |
| Verdict routes and their caps | build `test_defect` at_most=1 (`tables.py:35`); converge `rework` at_most=2 then retro (`:120`); check_plan `amend` (`:149`); review `reject` End (`:65`); tidy review reject→Rework (`:174`) | (b) | `at_most`/`then` (`workflow.py:55-64`) are the factory's cleanest tuning knob and none is reachable from a project |
| Where the operator decides (WAIT, `on_approve`, `revise_from`) | `tables.py:15,101,148,153` | (c) | The approval is his (FR-003, FR-005, FR-006) |
| The decision logic itself: guard, timeout, error end needs-me; advisory goes on; question to lead | `workflow.py:222-281` | (c) | The rules a project's table is read by; FR-038 wants them in one place |
| The lead, who answers questions | `tables.py:76-78`, `driver.py:77-85` | (b) | Its persona, grade and inputs; the measurement path (FR-100) around it is (c) |
| Advisory steps: a failure is discarded, never retried | `driver.py:133-134`, `workflow.py:231-232` | (b) | Suggestion #41: run 46's architect errored and was skipped; the orchestrator ran it by hand |

### Attempts and models

| Decision | Where | Today | Note |
|---|---|---|---|
| Attempts any one step may run | `cli.py:53` (`--attempts`, default 3), `operations.py:144` | per request only | Not per project, not per step |
| What counts as an attempt; what climbs a grade | `records.py:132-169`, `NOT_THE_WORK` `:138` | (c) | Fixed by FR-105, FR-108, FR-109 after real losses; a project should not redefine them |
| Each step's grade | `model=` in `tables.py` (document light `:59`, retro light `:128`, judges standard) | (b) | |
| The grades and how far a retry climbs | `GRADES`, `CLIMBS_TO` `workflow.py:17-18`, `grade_for` `:211-217` | (b) | `CLIMBS_TO` is a cost ceiling: a per-project value is reasonable, its existence is not negotiable |
| Which model a grade is | `agent.MODELS` `agent.py:34-35` | (b) | Belongs where it is (FR-041); a project names grades, never model ids |

### Checks and smells

| Decision | Where | Today | Note |
|---|---|---|---|
| The guards on every step | `checks.ALWAYS` `checks.py:19`; applied `driver.py:235-240`; undone `driver.py:268-280` | (c) | `factory_untouched` (FR-030), `changes_allowed` (FR-032) |
| Reply shape and verdict checks, prepended | `workflow.checks_for` `workflow.py:159-162` | (c) | A step cannot leave them out |
| Each step's own checks | `checks=` in `tables.py` | (b) | |
| The checks that exist | `@register`, `checks.py:39-51` | (b) | All are Python in the factory process |
| Each step's smells | `smells=` in `tables.py` (`:16,24,36,43,47,154,179,184`) | (b) | Run 78: the tidy steps had no line smell until a factory edit (suggestions, "Open, from run 78") |
| Thresholds: line length, test budget, coverage floor and drop | `TargetConfig` `config.py:41,48,50,51` | (a) | bttr_erp sets all four |
| Coverage report format | `checks._coverage` `checks.py:255-264` | (b) | coverage.py JSON only |
| How much test output is kept and quoted | `OUTPUT_LIMIT` `checks.py:237`, `SUMMARY_LINES` `:252` | (b) | Run 58 lost output at "655 lines left out" (#34) |
| What "red" means | `tests_fail_first` `checks.py:329-346` | (b), partly (a) | Exit codes only; `no_tests_exit_code` and `tests_readable_command` are (a). #23 (collection error is not red) and #26 (guard tests) are both about this |

### Agents: personas, prompts, inputs, capabilities

| Decision | Where | Today | Note |
|---|---|---|---|
| Which persona does a step | `persona=` in `tables.py` | (b) | |
| The persona's text | `personas/*.md`, read each step at `driver.py:209` | (b), factory-wide | FR-046 makes them editable without code, but one roster serves every target. "Long term we may want to configure this per project" (`changes/2026-11-23-the-stations-are-staffed.md`) |
| The step's prompt | `prompts/<step>.md`, `driver.py:176` | (b), factory-wide | bttr_erp's lessons live here: "If the database does not behave as the plan says" (`prompts/build.md:35`), also `check_plan.md:32`, `amend_plan.md:36`, `mend_tests.md:33` |
| Shared prompt parts | `prompts/fragments/` rules, speckit, asking, reply; `driver.py:177-188` | (c) for reply and asking | `reply` is written from the envelope; the rules' order of precedence is FR-021's |
| What a step is told (inputs) | `inputs=` in `tables.py`; the registry `driver.INPUTS` `driver.py:414-438` | (b) | 22 inputs, each a function over the run's records |
| The reply's shape (envelope) | `envelope=` in `tables.py` | (b) | Also read by name elsewhere: see "Couplings" |
| Capabilities | `capabilities=`; `agent.CAPABILITIES` `agent.py:27-30` | (c) | No capability includes a shell (FR-031) |
| Where a step may write | `may_change=`; `SCOPES` `workflow.py:16`; `checks._allowed` `checks.py:73-82` | scope per step (b); paths (a) | `test_paths`, `docs_paths` are (a); `spec` is spec kit's `specs/` only (`speckit.py:28-30`) |
| Files no writer may touch | `checks.py:79` | (c) | `.factory.toml`, `.gitignore`, `IDEALS.md` only; see F1 |
| Agent isolation from the operator's settings | `agent.ISOLATION` `agent.py:38` | (c) | |
| Which agent program | `TOMFACTORY_AGENT` `agent.py:173-179` | per machine | |

### Commands, time, containment

| Decision | Where | Today | Note |
|---|---|---|---|
| Test, setup, readable commands; exit code for none; tools; network | `config.py:36-47` | (a) | Read from the starting commit (`config.py:71-85`, FR-075, FR-089) |
| Time limit | `step_timeout_seconds` `config.py:40` (a); `Step.timeout` `workflow.py:130` (b) | (a) one for all | No entry sets `timeout`; bttr_erp's 2400 s applies equally to the light documenter and the planner |
| Containment | `sandbox.py:25-90` | (c) | FR-068 to FR-077 |
| Ideals | `IDEALS.md` from the starting commit, `config.py:126-132` | (a) | The precedent for a committed file that replaces the factory's own (FR-082) |
| Constitution | `.specify/memory/constitution.md` read from the *checkout*, `driver.py:418`, `speckit.py:33-39` | (a) by file | See F1 |

### Records and commits

| Decision | Where | Today | Note |
|---|---|---|---|
| Commit subjects | `run_record.LABELS`, `SUBJECT_LENGTH` `run_record.py:12-15` | (b) | FR-103 |
| Trailers `Factory-Run`, `Factory-Step`; author | `run_record.py:91`, `workspace.py:12` | (c) for trailers | Tools find a run's commits by them |
| Which steps commit | `commit_after=` | (b) | |
| The run record and its sections | `run_record.render` `run_record.py:117-155`; at `docs/runs/` `:104-106` | (b) | |
| Where the backlog and retros go | `prompts/architecture_review.md:25`, `prompts/retro.md:46` | (b) | Fixed `docs/` paths in prompt text. A project whose `docs_paths` left out `docs/` would have its retro and backlog refused by `changes_allowed` (inferred, not tried) |
| Branch names | `records.py:36` | (b) | FR-081 |

### What the orchestrator does by hand (playbook)

| By hand today | Where | Could be |
|---|---|---|
| Before/after comparison of a tidy ("compiled SQL", "a corpus of inputs") | memory "How I verify a tidy"; #31 | A project command run contained, as a check or smell on `test` |
| Re-running the architect when it errored | #41 | `advisory` steps given a retry count |
| Checking a request against the constitution and its own counts | playbook lines 36-67; #55, #56 | A project's own agent step before `plan` (later step 4) |
| Measuring on a scratch database | playbook 49-51, 76-84 | Stays the orchestrator's: it needs the network and a database, which containment refuses (#2, declined three times) |
| Approve, merge, push, record rulings | playbook 86-124 | Stays his and the orchestrator's |

### Couplings that make a table less than data

A table is not the whole story: some code reads steps by name. Renaming or replacing these steps in a project's
table would silently drop record sections or inputs, so the first steps below override fields and never names.

- `driver._findings` keys `converge`, `review`, `architecture_review` (`driver.py:385-386`).
- `run_record.render` reads `architecture_review`, `document`, and the `reviewer` persona (`run_record.py:138-148`);
  the sprint review appears only if the verdict has `unbuilt` (`:142`).
- `driver.wait_for_operator` reads envelope keys `plan`, `summary`, `findings`, `taken`, `declined` (`driver.py:498-511`).
- `checks.verdict` reads `requirement_changes`, `unbuilt`, `reasons`, `ideals_broken`, `findings` (`checks.py:121`).
- `_red_output` and the record find red's output by the check name `tests_fail_first` (`driver.py:358-359`,
  `run_record.py:191`); `step_message` skips `answer_question` by name (`run_record.py:25`).

## 2. The primitives, and which could be a project's

| Primitive | Where | Expose? | How |
|---|---|---|---|
| `Step` entry | `workflow.py:108-151` | Yes, by field | Overrides of named fields on existing entries first; whole new entries later |
| `Rework(step, at_most, then)` | `workflow.py:55-64` | `at_most` yes | A number in config; the target and `then` later, validated |
| `End`, `Replan`, `WAIT` | `workflow.py:67-103` | No for WAIT | A project may not remove or move an approval |
| Check registry | `checks.py:16-51` | Not as code | A project registers *commands*, run contained like its tests, never Python in the factory's process |
| Smells | `Step.smells`, `driver.py:256-260` | Yes | The safest thing to open: by FR-107 a smell can never fail a step |
| Grades | `GRADES`, `CLIMBS_TO`, `Step.model` | Yes | Per step grade; per project ceiling no higher than `standard` without the operator's word |
| Inputs | `driver.INPUTS` | Choose from, not add | A step override may list existing inputs; a new input is code |
| Personas | `personas/*.md`, `Step.persona` | Yes | A committed project folder whose files override the factory's by name |
| Prompts | `prompts/<step>.md` | Yes | Same, with the same validation (placeholders within inputs, every envelope key explained) |
| Fragments | `prompts/fragments/` | No | `reply` and `asking` are protocol, `rules` is FR-021's precedence |
| Run kinds | `RUN_KINDS`, `prompts/run_kinds/` | Later | A kind is a table plus a prompt; once tables can be a project's, so can kinds |
| Settings | `TargetConfig` | Already | The model to copy: closed list of fields, defaults stated once, read from the starting commit |

### What must stay closed

These hold whatever a project's configuration says. The rule under all of them is the one `.factory.toml` already
states on its first line: settings are "read from the commit a run starts at, never from a run's checkout, so an
agent cannot change what 'passing' means" (`config.py:59-60`; FR-075, FR-082, FR-089).

1. **The guards.** `factory_untouched` and `changes_allowed` run on every step and cannot be named, removed or
   reordered by a table (`checks.py:19`, `driver.py:235-240`). Nor can `envelope_valid` and `verdict` (`workflow.py:159-162`).
2. **Containment.** A project's command runs only through `sandbox.command` (`checks.py:222-228`). No project code is
   ever imported into the factory (that would run the target's code uncontained, against FR-068). No capability
   gains a shell (`agent.py:27-30`, FR-031).
3. **The source of configuration.** Every project file the factory reads to shape a run (settings, step overrides,
   personas, prompts, check commands) is read with `workspace.committed(target, run.base_commit, …)`
   (`workspace.py:188-191`), never from the checkout; and every such path joins the list no step may write
   (`checks.py:79`). One list, named once, so a new file cannot be forgotten.
4. **The operator's approval.** A project table keeps at least one WAIT before the first step that changes code, and
   approval leads to `baseline` (FR-003, FR-005, FR-006). `validate` refuses a table otherwise.
5. **The gates of a change.** A change run keeps `baseline`, `tests_fail_first` before the build, and `tests_pass`
   after the last step that writes code; a tidy keeps `baseline` and `tests_pass` (FR-006, FR-066). Overrides may add
   checks and smells, never take these away. This is the line between "tailoring a run" and "changing what passing means".
6. **Scopes only narrow.** A project may narrow a step's `may_change` (the documenter to `nothing`), never widen it
   (the test writer to `not_tests` would let it write the code its tests describe, against FR-043).
7. **The resolved table is shown and recorded.** FR-038 wants the rules readable in one place; an overlay scatters
   them. So `factory table --target <path>` prints the table a run will use, and the run's record names the
   overrides that were in force, as it does the ideals (FR-024).

### Two findings on the way

- **F1. The constitution is read from the checkout, and the builder may change it.** `INPUTS["constitution"]` reads
  `speckit.constitution(src.checkout.path)` (`driver.py:418`), and `not_tests` excludes only `.factory.toml`,
  `.gitignore` and `IDEALS.md` (`checks.py:79`). bttr_erp has `.specify/memory/constitution.md`. So, as I read it,
  `build` or `tidy_code` could rewrite rule 1 of the precedence (`prompts/fragments/rules.md`) and `converge` would
  judge the work by the rewritten one. Not tried. It is the gap FR-082 closed for `IDEALS.md`; the same fix applies:
  read it from the starting commit and add it to the protected list. It is also the shape every new project file in
  this proposal must avoid.
- **F2. Which table a run uses is decided from the checkout.** `table_of` calls `speckit.available(run.workspace)`
  (`driver.py:40`) on every advance, approval and resume. A step that wrote `.specify/scripts/bash/setup-plan.sh` would
  switch a non-sprint change run to the spec kit table at its next resume (inferred). bttr_erp's sprint cycle makes it
  unreachable there today. Fix: decide it once, from the starting commit.

## 3. The proposal

### First step: step overrides in `.factory.toml`, and the table shown

A `[steps.<name>]` table per step, for steps that already exist in the run's table, with a closed list of fields:

```toml
[steps.document]
model = "light"                 # one of GRADES
timeout = 600                   # seconds, in place of step_timeout_seconds

[steps.tidy_code]
smells = ["lines_within_length"]   # registered checks, run as smells: added to the entry's own

[steps.converge]
rework_at_most = 2              # the `at_most` of its Rework routes

[run]
attempts = 3                    # the default for `factory request --attempts`
climbs_to = "standard"          # never above standard, unless the operator commits it
```

How: `TargetConfig` gains a `steps` mapping, read as it is now (`config.py:71-85`); `table_of` applies it with
`dataclasses.replace` (as `tables.py:94-186` already does to build the sprint and tidy tables from the plain one) and
the result goes through `validate` (`driver.py:456-487`) plus two refusals: an unknown step or field names itself, and
nothing in "What must stay closed" moves. `factory table` prints the resolved table. Perhaps 60 lines of code, and a
change record; inferred, not measured.

What it lets the operator do that he cannot today, from bttr_erp's history:

- **Run 78**: the tidy steps carried no line smell, and a 147-character line cost a second tidy and review. That was a
  factory bug, but its cure for one codebase is one line of TOML, the same day, while a run is open on another.
- **FR-109**: putting the documenter and retro on the light grade was a factory commit that changed every target. With
  this, the grades become the factory's defaults and each project's choice; a cost experiment is one committed line,
  undone by reverting it.
- **FR-110**: coverage as a smell on `test` was a factory edit; with this, a project that wants it on `tidy_tests` too adds it.
- **Spec 003 part 2, modes** (FR-311, FR-312): a mode's dials (plan-check rounds, the retro's length) are mostly
  `rework_at_most`, `model` and `advisory`. A mode then becomes a named set of these overrides, not new code. The
  "nannyware design-thinking run, budget about $15" could be tried as a mode without touching the tables.
- **Timeouts**: bttr_erp's 2400 s is sized for the builder; the light documenter gets the same.

Not in this step on purpose: `persona`, `prompt`, `inputs`, `checks`, `may_change`, `capabilities`, `on_pass`,
`on_fail`, route targets. Each either changes what passing means or needs the closed rules above enforced first.

### Second step: a project's own personas and prompts, by name

A committed folder in the target, say `.factory/personas/` and `.factory/prompts/`, whose files replace the
factory's of the same name, read from the starting commit (the `IDEALS.md` precedent, `config.py:126-132`), and
protected from writes. A step override may then name `persona = "db_veteran"` if that file exists in either place.
`validate` applies to an override exactly as to the factory's file: three headings for a persona, placeholders within
the entry's inputs, every envelope key explained (`driver.py:475-485`). The record of each step already names its
persona (FR-047); it would also say whose file it was.

What it lets him do: **the per-project roster** he asked for, and spec 003's "plan check as a team of personas"
(a database veteran, an ERP parity hand, a test sceptic) staffed for bttr_erp without changing the roster any other
target sees. It also gives bttr_erp's lessons a home that is bttr_erp's: the "if the database does not behave"
sections in four factory prompts (`build.md:35`, `check_plan.md:32`, `amend_plan.md:36`, `mend_tests.md:33`) are one
project's experience written into every project's prompt. Several OPEN suggestions are prompt-only and bttr_erp's alone
(#16's narrow checks, #19, #21, #22): each becomes a commit in the target, decided at merge, not a factory change.

### Third step: checks a project registers as commands

A `[checks.<name>]` table: a command, run in the checkout, contained exactly like the test command (`checks.py:222-228`),
with the target's tools and without the network unless it says so; exit 0 passes, and its output is kept as a failing
test's is. A project check may be added to a step as a smell freely, and as a check only on steps that already have
checks of their own, never in place of the gates.

What it lets him do:

- **#31, the before/after comparison** the orchestrator does by hand after every tidy ("compiled SQL for query
  builders, a corpus of good and faulty inputs"): a project command that compares the checkout with the base commit,
  as a check on `tidy_code`'s `test`.
- **Run 62's "each id on its own row"**, declined as "one codebase's convention, not the factory's"
  (suggestion #27): exactly right, and now the codebase can have it.
- **#23, a collection error is not red**: `pytest --collect-only -q` as a check before `tests_fail_first`, for a codebase
  on pytest, without the factory learning pytest.
- The coverage smell (`checks.py:255-264`) could later be one such command, and the factory would stop knowing coverage.py.

### Later: whole entries, and kinds a project defines

Only after the couplings above are removed (each becomes a field of the entry, such as which envelope keys are its
findings for the retro and the record): let a project add a step entry with an `after = "<step>"` and its own prompt
and persona, and define a run kind as a table. Examples: a `check_request` agent step before `plan` that checks the
request against the constitution and its own counts (#55, #56, the two OPEN themes that come back most); an advisory
step's retry (#41). This is where FR-037 ("adding a step must not require altering existing steps") becomes true for a
project and not only for the factory. I would not build it until the first three have been used for a few runs.

## Open questions for the operator

- May a project's committed settings put a step on the strongest grade, or does that stay his word each time (memory:
  "not the most expensive model unless he says")? I would make it refuse unless a separate `allow_strongest = true` is set.
- Should overrides live in `.factory.toml` or a second file (`.factory/steps.toml`)? One file is fewer things to protect;
  two keep the settings readable. I lean to one file until it passes about a hundred lines.
- F1 and F2 are worth fixing before any of this, whatever is decided: they are the same rule this proposal depends on.
