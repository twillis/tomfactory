# Backlog

*From the factory's own architect persona, run once over a copy of the factory's code on
2026-11-19 (commit 26a7e00): 230 seconds, an estimated $4.04. It changed no other file.*

Maintenance notes from the architect. Each entry can be handed to the factory as a request
of its own (`--tidy code` or `--tidy tests` for most). A **Warning** will cause trouble if
left; a **Suggestion** would make the code better. Within each file, most serious first.

Whole-codebase review, 2026-11-19, at commit `26a7e00`. Nothing was changed.

## factory/driver.py

- **Warning** — `factory/driver.py`: split `run_step` (120 lines, eight jobs) into prompt assembly, execution and verification, and move the decisions it makes out of it — how an adapter reply is classed as timeout/error (126–132), what counts as a question (160–165), which checks a step gets (`envelope_valid`, plus `verdict` when it has routes, 167–168), and which guard is undone how (150) — into `checks.py` or `workflow.py`; the README says the driver "decides nothing" and today it decides all of these. (Layers with explicit interfaces; S1.)
- **Warning** — `factory/driver.py`: give the failure kinds one home; `timeout | error | guard | malformed | check | question` are spelled as literals in `workflow.StepResult`'s comment, `next_step`, `run_step` and the `steps.failure` CHECK in `store.py:79`, and because the schema lacks `question` line 198 quietly records a question as `check`, so the record disagrees with what the rules saw. (S9: one home; layers.)
- **Warning** — `factory/driver.py`: move the rule "the lead has answered only if it passed and said `confident: yes`" (69) into `workflow.py` as a pure function, and replace the two `step is not workflow.LEAD` tests (100, 161) with a field on the step entry (for example `may_ask`); the question path is the one branch of the cycle whose rule cannot be read in the rules file. (Layers; "the rules live in one file".)
- **Suggestion** — `factory/driver.py`: make `gather` a registry of named inputs, as `checks.py` is of named checks, and fold the two spec kit inputs (built separately at 95–98) into it; today an input is added in an if-chain, in each step's `inputs`, and in the README's hand-written list, and every call re-queries plans and steps whether or not the input uses them. (S9; S7: extend without changing the layer.)
- **Suggestion** — `factory/driver.py`: add one `validate(table)` that is run by a test over every table — each `on_pass`, `Rework`, `Replan` and route names a step in the same table, each check is registered, each persona and prompt file exists, each prompt's `{{placeholders}}` are in the step's `inputs`; today a wrong name is found mid-run as "the factory itself failed", after paid agent steps. (Discrete under fuzzy, S2; closed defaults.)
- **Suggestion** — `factory/driver.py`: give "the run now waits for the operator" one function in `records.py`; `set_state(..., "awaiting_approval", driver_pid=None, driver_started=None, child_pgid=None)` is written out at lines 72 and 266 and the same three fields are cleared again in `records.end`. (S9.)

## factory/workflow.py

- **Warning** — `factory/workflow.py`: make one mechanism for a step that judges; `review` uses the envelope kind `"verdict"`, the check `verdict_accept` and `on_fail`, while `converge` uses a tuple of verdicts, `routes`, a `verdict` check the driver adds, and `next_step` recognising it by `failed_check.name == "verdict"` (188) — write `review` as `routes={"reject": End("rejected")}` and delete the first mechanism, so a tidy's "send it back" is a route too. (S9: a repeated thing gets one home.)
- **Warning** — `factory/workflow.py`: give the kind of run one name and one table; it is `workflow` in the store, on `operations.request` and on the run, `kind` in `table_for`, `run_kind` as an input, `--tidy` plus `f"tidy-{...}"` in `cli.py:92`, and two near-homonym dicts `KINDS_OF_RUN` and `RUN_KINDS` (one without `change`), all beside `Step.kind` and `KINDS` which mean something else — a new kind of run is edited in five places. (S9: structure that can be read.)
- **Warning** — `factory/workflow.py`: drop the `steps or STEPS` defaults in `get` and `after_wait` (158, 218) and require the table; a caller that forgets it gets the plain table on a spec kit or tidy run, which is a wrong answer given silently rather than an error. (Explicit interfaces.)
- **Suggestion** — `factory/workflow.py`: let a waiting step say where approval leads; `after_wait` takes "the next entry in the list" (220) while every other transition follows a named `on_pass`, so reordering a table changes what approval does without any entry saying so. (Explicit interfaces.)
- **Suggestion** — `factory/workflow.py`: move the `RUN_KINDS` prose (301–308) into `prompts/`; it is prompt text living in the file that is meant to hold only the table and the rules. (Layers.)
- **Suggestion** — `factory/workflow.py`: use `KIT_INPUTS` in the plain table instead of spelling `"speckit_instructions", "speckit_context"` three times above its definition (105, 114, 122), or better, stop listing them at all (see `prompts/`). (S9.)
- **Suggestion** — `factory/workflow.py`: move `CheckResult` here (it is pure data) so `StepResult.failed_check` can be typed and `next_step` need not reach it through `getattr(..., "note", "")`; and have `End` refuse an outcome outside `accepted | rejected | needs-me`, which today is only caught by the database. (Explicit interfaces.)
- **Suggestion** — `factory/workflow.py`: when a fourth table arrives (docs/next.md, "a factory per project"), split tables from rules; three tables, the rules and the lead now share one file whose promise is that it can be read top to bottom. (S9: each piece has one obvious place.)

## factory/checks.py

- **Warning** — `factory/checks.py`: take the review's own rule "broken ideals with verdict accept" (116–118) out of `envelope_valid`, which is the general shape check applied to every agent step, and put it with the verdict check; it is domain logic keyed on two magic key names inside a general mechanism. (S1: general layers hold no domain; S4.)
- **Suggestion** — `factory/checks.py`: merge `verdict_accept` and `verdict` (216–236), which do the same thing with different lists of keys, as part of the single judging mechanism above. (S9.)
- **Suggestion** — `factory/checks.py`: give `baseline`, `tests_fail_first` and `tests_pass` one helper that runs the tests, handles the time limit and attaches `contained`, leaving each check only its judgement of the exit code; and have `register` stamp the name, which each check now repeats in every `CheckResult` it builds (about thirty times in the file). (S9.)
- **Suggestion** — `factory/checks.py`: ask `speckit.py` which files spec kit owns instead of hard-coding `specs/` in `_allowed` (86), and keep `under` with the path helpers rather than importing it into `driver.gather` from the checks; `speckit.py` is declared the only module that knows spec kit's layout. (Layers.)
- **Suggestion** — `factory/checks.py`: give test output its own field on `CheckResult`; `note` is at once the failure reason, a remark and up to 6,000 characters of output, and `driver.py` (194, 247) depends on which of the three it happens to be. (Explicit interfaces.)

## factory/operations.py

- **Warning** — `factory/operations.py`: decide a run's table once and in one function; `workflow.table_for(speckit.available(path), run.workflow)` is written at `operations.py:153`, `operations.py:180` and `driver.py:45`, the first against the operator's working copy and the others against the run's checkout, so a target with uncommitted spec kit files starts at `specify` and then fails in the driver looking for it in the plain table. (S9: one home; "read from the commit, never the disk".)
- **Warning** — `factory/operations.py`: pass the base commit to `Workspace.create`; `request` reads HEAD through `config.head_commit` (143), records it as the run's `base_commit`, and `Workspace.create` reads HEAD again (`workspace.py:40`), so a commit landing between the two leaves every later diff and guard measured from the wrong place. (Explicit interfaces.)
- **Suggestion** — `factory/operations.py`: give "launch a driver at this step, in the state that step implies" one function; the three lines are repeated in `_carry_on`, `resume` and `answer` (187–189, 251–254, 266–268). (S9.)
- **Suggestion** — `factory/operations.py`: add `Workspace.of(run)`; `Workspace(run.workspace, run.target, run.branch, run.base_commit)` is spelled out four times here and in the driver and again in the tests. (S9.)
- **Suggestion** — `factory/operations.py`: choose one seam for replacing the launcher; five operations carry a `launcher=None` parameter that exists only for tests (61 `launcher=in_process(...)` call sites) while `test_cli.py` replaces `operations.launch` instead. (S9; explicit interfaces.)
- **Suggestion** — `factory/operations.py`: rename `request`'s `workflow` parameter so the module need not be imported twice (`workflow` and `flow`, lines 14–15); and give "how a run is described" (`run.outcome or run.state.replace("_", " ")`) one function, now written at 81, 149, 230, 241 and in `cli.py` 160, 171. (S9.)

## factory/store.py

- **Warning** — `factory/store.py`: settle on one way the schema changes; there are three now — a `VERSION` that refuses older homes, an `ADDED_SINCE` list whose column must also be written identically in `SCHEMA` (52 and 110), and a `DROP INDEX` statement left inside `SCHEMA` (67) — and none can widen a CHECK, which is why a new failure kind could not be recorded. A numbered list of migrations would be the one home. (S9; S3.)

## factory/workspace.py and factory/config.py

- **Suggestion** — `factory/workspace.py`: separate the two jobs its docstring admits to — the run's git checkout, and fingerprint/snapshot/restore of the factory's own files — and state the cache rule once (it is `CACHES` at line 14 and again by hand in `_files` at 137). (One job per module.)
- **Suggestion** — `factory/config.py`: write each target default once; `TargetConfig`'s field defaults and `DEFAULT_FACTORY_TOML` state the same seven values, and a test exists only to check that two of them still agree. (S9.)
- **Suggestion** — `factory/config.py`: move `head_commit` and `read_target_config`'s `git show` behind `workspace.py`; the data layer shells out to git while another module is named as the one that knows git. (Layers.)

## factory/speckit.py and factory/records.py

- **Suggestion** — `factory/speckit.py`: share one slug function with `records.slug`; `_specify` (100–101) repeats the same lower-case, hyphenate, trim-to-40 rule with four words instead of five, and the "drop the front matter" split is likewise written in both `speckit.py:128` and `agent.py:180`. (S9.)

## factory/cli.py

- **Suggestion** — `factory/cli.py`: share the `[run] words` parsing between `revise` and `answer` (115–116, 122–123) and the "Run N ended: outcome — reason" line printed in four places (130, 138, 144, 227). (S9.)

## prompts/

- **Warning** — `prompts/*.md`: generate the closing "End your reply with one JSON object…" block from each step's `envelope` instead of writing it by hand in all fourteen prompts; the shape is stated in the table, again in the prompt and again in `test_workflow.py`, and when the first two drift the agent is failed as malformed and a paid attempt is spent. (S9; S2: a stronger discrete layer.)
- **Suggestion** — `prompts/*.md`: make the repeated blocks fragments the driver appends, as it already does with `asking.md` — the "rules, in order of precedence" block (eleven prompts) and the "Spec kit, if this codebase uses it" block (eight) — keyed on the step having those inputs or a `speckit` entry; changing the precedence wording is an eleven-file edit today. (S9.)
- **Suggestion** — `prompts/write_tests.md`: state the proportion rule once; "each behaviour once, at the level where it lives; parametrise; reuse helpers" is written here, in `personas/test_writer.md` priorities 6–7 and in the refusal note in `checks.py:176–178`, in three wordings. (S9.)

## README.md

- **Warning** — `README.md`: bring the map back in line with the code, and test the parts that can be derived — the file table omits `sandbox.py`; the list of prompt inputs omits `run_kind`, `question`, `speckit_instructions` and `speckit_context`; "Seven rules" omits the question rule that `next_step` applies third; `test_docs.py` takes the command list from the contract rather than the parser, so a new command can be undocumented and pass. (S9: a reader can tell where a thing lives before opening a file.)

## tests/

- **Warning** — `tests/test_cycle.py`: move `script`, the `cycle` fixture, `record`, `names` and the scripted entries into `conftest.py` or a helpers module; eight other test files import them from this test module (the fixture by a `# noqa` import) and two import `tree` from `test_workspace.py`, so splitting or trimming this file breaks its neighbours. (Layers with explicit interfaces, applied to tests.)
- **Warning** — `tests/`: test each rule once, at the level where it lives; the routing rules (rework, attempt limit, timeout, agent error, guard) are asserted as pure functions in `test_workflow.py` and again as whole runs in `test_cycle.py` and again in `test_operations.py` (170–197); the test-running checks in `test_checks.py` and again in `test_cycle.py` (179–194, 247, 300); `changes_allowed` as a ten-row table in `test_step_shape.py` and again as five whole runs in `test_cycle.py:210` plus the tidy, spec kit and extending files. Keep one whole-run test per route to show the layers join. The tests are 4,600 lines to the factory's 3,100. (S9: once, at its level; proportionate.)
- **Warning** — `tests/test_workflow.py`: stop restating the table; `TABLE` (28–40) and the inputs/envelopes dicts (53–70) are a second copy of `STEPS`, the persona map is copied again in `test_cycle.py:269` and twice in `test_speckit.py` (125–136, 163–167), so every table change is made in up to five places and the tests prove only that the copies agree — assert properties instead (different personas for tests, code and review; the reviewer may change nothing; every route resolves). (S9.)
- **Suggestion** — `tests/test_workflow.py`: make the single-case `next_step` tests one table of `(step, result, attempts) -> expected`; about ten tests here (85–181) and four in `test_engine.py` are variations of that one call. (S9; parametrised tests.)
- **Suggestion** — `tests/conftest.py`: give "write these files into the target and commit" and "request, then approve until it ends" one helper each; the first is rebuilt in `test_cycle.go`, `tidy`, `test_checks.make` and `test_speckit.with_constitution` although `make_target(extra_files=...)` exists, and the second in `cycle`, `tidy`, `to_the_end`, `finished` and `start`. (S9: reuse the helpers already there.)
- **Suggestion** — `tests/test_cycle.py`: remove the assertions that cannot fail — `calls[1]["persona"] == calls[1]["persona"]` (424), a list compared with itself (497), `[...] * 0 +` in `test_operations.py:176` and `[:-0 or None]` in `test_speckit.py:207`; each reads as a check and checks nothing. (S9: brevity without obscurity.)
- **Suggestion** — `tests/test_speckit.py`: split `test_prepare_runs_the_scripts…` (82–118, eight behaviours in one body) into a table over the commands plus the two revision cases; and likewise the multi-refusal tests in `test_operations.py:34` and `test_cycle.py:506`, where the first failure hides the rest. (Parametrised tests.)
- **Suggestion** — `tests/test_extending.py`: replace the regex over source text (103–114), which already needs hand-written exceptions for `plan`, `baseline` and `test`, with a check that will not need a new exception for each step whose name is an ordinary word. (S9.)

## scripts/traceability.py

- **Suggestion** — `scripts/traceability.py`: make the S8 gate one mechanism; `conftest.py` enforces "every test has a marker" from collected tests while this script enforces "every requirement has a marker" by a regex over source text, which a marker in a comment or an uncollected file satisfies — a single pytest check over collected markers would do both. (S8; S9.)

## Overall

The shape is sound and worth keeping: a table of steps, pure rules that read it, checks
registered by name, a general store, one adapter for the agent program, and effect modules
that decide nothing. Where it has worn is where features arrived quickly on top of that
shape — spec kit, questions, tidy runs, containment. Each added a second way of doing
something the design already had one way to do: two verdict mechanisms, three tables chosen
by an expression written three times, a question path whose rule sits in the driver, three
schema-change mechanisms, prompt blocks copied into each new prompt. The driver's
`run_step` is where most of this collected, and it is now the one place that contradicts
the README's claim that the rules live in one file. The tests carry the same history: they
are larger than the code, they restate the step table several times, and they assert most
rules at two or three levels. None of this is urgent, and none of it needs a redesign. The
order I would take it in: the single judging mechanism and failure-kind vocabulary first
(they unblock the rest), then `run_step`, then the generated prompt footer, then the tests.
