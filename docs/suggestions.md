# The suggestion box: what the factory's agents have asked for, and the answer

Each retro is the agents' feedback. This file is the factory's answer to it, kept so that a suggestion is
answered once and a "no" carries its reason. Seeded 2026-11-23 from the 29 retros of bttr_erp's runs 27 to 69
(the processing is described under its first heading below). From run 72 on the orchestrator updates it at
each merge: a new suggestion is added OPEN, and a theme's status changes only with where it was taken or why
it was declined. A retro may ask again for a declined theme only with a reason the decline did not weigh.
The operator, 2026-11-23: "Your job as assistant CEO is to make sure stuff gets recorded and passed along to
the relevant factory teams." Specification: `specs/003-fitness-and-feedback/spec.md`.

## Since the seeding

- **Taken, FR-106 (2026-11-23, from run 69):** the plan check asks whether a planned case would still pass with
  its rule broken, and searches the whole package for a reworded phrase; the test writer never drops a
  planned case. `specs/001-near-loop-factory/changes/2026-11-23-a-case-that-shows-its-rule.md`.
- **Declined (2026-11-23, from run 69): let a step edit the run-order rows a plan names.** The run order holds
  the operator's rulings, quoted; the orchestrator records them at merge after checking each attribution (an
  agent's reasoning was once filed under his name). The operator, asked "So they essentially want more access?",
  was told the reason and let it stand. The real need underneath is theme #52 (nobody tracks the merge-time
  work), which stays OPEN and is to be answered by the scorecard's merge checklist (spec 003).
- **Open, from run 70:** show a plan's declared conflict with the constitution to the operator as a direct
  question at approval and record his answer in the run; give "findings for the operator" a stated home; check
  that every "silent and open" reason names the comment that carries it; a line-length tool for the builder;
  make converge's "never accept work that breaks an ideal" agree with "a broken ideal is reported".
- **Open, from run 71:** a refusal under a new root checks the segment where traversal stopped (taken into
  run 71's plan, not yet into the test-writer persona); count a collection error as not yet red; the
  orchestrator reads a dictated sentence about a later run against what the module already says; list and
  create at a new root's top-level table among the cases.

- **Taken, 2026-11-23, from run 76 (the operator: "Yeah edit the playbook"):** three lines under "Writing a request" in
  `orchestrator/playbook.md`: state the failing condition the code allows, say whether a recent run's structure is kept
  or folded in, and name the inputs where the language differs from the reference. This answers part of #56.
- **Open, from run 76 (the first run of the named personas):** the orchestrator states, for a new keyword, the red condition the
  code allows (through the gateway a case fails at `_untaken`; through a path it is proved by the build alone), and says
  whether a structure a recent run introduced is kept or folded in (continues #56); a plan that keeps a reference
  implementation's rules lists the inputs where the language's own primitive differs, each with a test (new); the plan
  check asks the loud-or-silent question of every new default (new); a plan that parametrises every case one way names
  the cases that cannot follow it (new). Threats repeated: keywords threaded by hand (run 69's entry), test modules
  importing from one another, run-order rows left for merge (#52).

- **Open, from run 77:** the plan check asks how many statements a new read or write path adds where every input is
  good, and whether an existing path already solves it (new; would likely have saved a plan round of 13.2 minutes and
  $4.14); the plan check searches today's message for each refusal fragment as a substring (continues FR-106's theme);
  the test writer writes every non-printing or non-ASCII character as an escape (new); converge is shown the diff with
  non-ASCII characters visible (new); the build step keeps a one-line reason for each check verdict, since three build
  attempts on line length could not be explained afterwards (new); the orchestrator quotes an order from the reference
  file or leaves it out, never retypes it (continues #56). Threats repeated: a handler can take a filter and list
  unfiltered rows; test modules importing from one another (third run running); run-order rows left for merge (#52);
  requests long enough to carry their own mistakes.

- **Taken, 2026-11-23, FR-107 (the operator: "smells that don't stop the build", "By build I mean run"):** the line
  length and the test budget are smells, reported and never sent back, and the tidy steps are measured too. Answers the
  item below.
- **Open, from run 78 (found by the orchestrator, from the review's friction):** the line-length check measures the
  test writer, the builder and a mended test, not `tidy_code` or `tidy_tests`. Run 78's tidy left a 147-character
  docstring line that only the final review caught, costing a second tidy and review (about 3 minutes). A change to the
  factory: give the two tidy steps the same check.

- **Caught up 2026-11-25 by the orchestrator (runs 79 to 98, 18 retros; the box had not been updated since run 78).**
  Eight retro claims the run records contradict were declined as misreadings; they are listed under run 98 below and
  in the theme notes.
- **Open, from run 79 (beyond #61 and #62):** cite a backlog entry "by its run and first words, never by line
  number" (new, #70); the document step "was also not given the test results, so 'I could not say whether the suite
  passes'" (continues #30). The CHANGELOG ask ("drop the CHANGELOG.md entry, or have the operator decide once to
  start one") is overtaken: bttr_erp has had `CHANGELOG.md` since run 84 (f8ce399, the documenter's commit).
- **Open, from run 80:** cite a backlog entry "by the heading it is filed under, copied from docs/backlog.md, plus
  its first words" (#70); "for each step that follows Clojure, the request should list every difference from it,
  not 'the one'" (continues #5 and run 76's "name the inputs where the language differs"). Taken already: the
  "fails today because" column (#11; `dialogue_check.md`: "For each test, say what makes it fail before the build");
  "always keep the tail" (#34; `checks.kept_output` keeps the beginning and the end since FR-096). The CHANGELOG ask
  ("the second time it is raised") is overtaken, as for run 79. Threat repeated: run-order rows left for merge (#52).
- **Open, from run 81:** "measure every case the proof list names, not only the main ones ... Failing that, the
  planner persona should send a `measure` request" (continues #3; new #65); "before asking the planner to choose a
  shape, check that the request's own constraints leave more than one option open" (continues #56); "when a plan
  adds a query or function beside an existing one, ask whether facts both state are written once (B6)" (new, #67).
  CHANGELOG ("the third time") overtaken. Threat repeated: #52, "the second step running to leave its rows this way".
- **Open, from run 82:** check_plan: "where a plan gives both prose and a code sample for one rule, check that they
  agree" (new); "for every statement that replaces a stored value ... ask what else that value holds and whether
  losing it is loud (B6)" (continues #10); the request names "every operation that returns a row" (continues #56);
  "cite code by symbol name, not by line number" (#70); architecture_review input: "collapse repeated tracebacks"
  (continues #34); the request says "which later step will read each new fact" (new). Threats repeated: #52
  ("Decisions are piling up at merge"); #17 ("Splitting a request when it spans more than one layer may be cheaper").
- **Open, from run 83:** baseline "emit the existing tests that compare whole rows, by name" (new); "print failed
  test ids, capped, instead of the full report" (continues #34: "34,287 lines and named only errors"); "compare the
  plan's file list with the diff" (new, #69); "a fix the request names must have a test before converge passes"
  (continues #5). Taken already: "use the measure channel for questions the plan cannot settle by reading" (FR-100;
  `dialogue_planner.md:51`). Declined: "a checklist for hand-written test tables (key default, listed through the
  entity handler ...)": one codebase's convention, not the factory's (as #27's decline); it belongs in bttr_erp's
  `knowledge/` or test helpers. Left out as product knowledge: "constraint and computed-value order follows
  constraint names".
- **Open, from run 84:** "grep for every symbol the request names ... and list each hit as reading" and "check each
  safety claim in the request ('safe by D8') against the code" (new, #66); "for each new rule, grep for an existing
  rule over the same input and for a second place that decides the same thing" (#67); "keep each failing test's
  message in the red log, and print one traceback per distinct error cause" (continues #34); converge: "give each
  architecture warning a disposition ... and list each deviation from the approved plan" (new, #68). Threat: a plan
  wider than the request, "approved without comment" (continues run 70's "show a plan's declared conflict ... as a
  direct question at approval").
- **Open, from run 85:** "a mechanical check that every 'section X' reference names a section that exists" (continues
  #16; saved "$2.26, 6.6 min"); "quote each message once, verbatim" (continues #19); a count "stated as 'unchanged'
  carries a cost note naming the reads that gained a join" (new); decision rows say "which reads it covers" (new);
  "one sentence stating who writes requirements/ rows ... Three steps raised it" (continues #52; #50's decline stands);
  "name each constitution MUST the plan touches" (#15 asked again, with a reason the decline did not weigh: B5
  "surfaced only at merge"; it asks for the MUSTs a plan touches, not an index of the constitution); document and
  converge "take test results from the factory's test record" (continues #30).
- **Open, from run 86:** "each claim about a named call site must be checked against the code" (#66); "when a plan
  rests on library behaviour ... request a measurement instead of relying on memory" (#65); the record "should say how
  totals are rounded" (new, #74). Taken already: "the test list should name the family" (#9, FR-098;
  `dialogue_check.md`: "A rule the plan states for a whole family"). Left out as product design: a Store method's
  name must say what it joins.
- **Open, from run 89:** "give the plan the feature directory, or state where a plan-only reply is kept" (continues
  #53); "before writing a helper's or test module's location into the plan, grep for its definition" (#66; "6.0 min
  and $2.11"); "do not ask for commands the builder cannot run" (continues #14: the plan said "Run `uv lock` (or `uv
  sync`) and commit the updated `uv.lock`"); converge should "name which commits are factory paperwork" (continues
  #40: converge is not told of the `Factory-Step:` trailer); the documenter should "copy measured values from the
  request verbatim rather than restating them. The `'1_0'` error came from a paraphrase" (new).
- **Open, from run 90:** "make the planner ask for measurements in its first round, for every claim about PostgreSQL
  or the driver" (#65). Taken already: "record every operator ruling ... before the plan step runs" (FR-133 `factory
  note` and FR-134 `.factory-main/`, `changes/2026-11-24-tuning-the-dialogue.md` item 4; the hash ruling 27e2c14 was
  committed at 07:39 EST, after the run started at 07:25). Left out as product: the version-hash tidy, one SELECT.
- **Open, from run 91:** "a plan [that] rests on driver or database behaviour ... lists every measurement it needs in
  its first request" (#65); "write the two measured tables ... as a reference the plan persona reads" (new, #73);
  "the test step reports a pass or fail line per named gate test before the build" (continues #34); "the plan names
  exact test names and imports, or the build step lists each deviation" (#68). Left out as product: the shared
  "statements that read no table" helper.
- **Open, from run 92:** "a plan that relies on a new dependency's behaviour lists each behaviour as a measure
  request in its first version" (#65); "`test_budget_lines` should not count a vendored fixture" (new, #71); the plan
  check checks "each new extension point against the ideal of explicit interfaces, and against B6" (continues #10;
  #67). Declined: write_tests "end by running `pytest --collect-only`": agents run nothing (#2); the conftest move is
  bttr_erp's backlog. Friction repeated: the builder "was asked to run `uv lock`, which it cannot run" (#14).
- **Open, from run 93:** the document brief states "whether the architect's backlog edits are already in the change"
  (continues #48); converge lists "each departure from the plan's named edits as its own item ... not under
  'details'" (#68); baseline, red and test "take 15.4 of the 25.2 minutes, 61% ... whether baseline and red run the
  whole suite or only what each needs" (new); "split waiting for the operator from time between steps" (#74; run 98's
  record still prints one figure, "Waiting for the operator, and between steps: 17.7 minutes"). Taken already:
  "write check_plan's findings and what amend_plan changed into the record" (FR-127, the dialogue's transcript is in
  the record from run 95).
- **Open, from run 94:** the plan lists "every file it expects to change, generated docs included", and checks "that
  any signature sketch matches the exact shape the tests will assert" (#69); "where a plan rests on a database limit
  or a printed form, make it a measure request before build" (#65); "have the plan state the exact refusal fragments"
  (continues #19); "the CHANGELOG entry should carry the suite's result line" (continues #30); amend the knowledge
  README to cite this run (#73). Left out as product: `live_only` on unique indexes; the handler check at setup.
- **Taken, 2026-11-24, FR-130 to FR-138 (from run 95), `changes/2026-11-24-tuning-the-dialogue.md`:** "batch small
  corrections into one plan round" (FR-130, the check's `blocking`/`notes`); "give the builder a way to remove a
  file" (FR-135); "state the convention for a new module that tests import" (FR-138); "take counts from the measured
  numstat, and check 'no test was cut'" (FR-136); the budget messages' "$11.52 and $11.42" (FR-137); the rulings "not
  in the file the agents read" (FR-134).
- **Open, from run 95:** "the orchestrator confirms that each requirement row the ask cites exists in the worktree and
  is current, and stops if one does not" (new, #75; FR-134 now gives agents main's copy, but nothing checks the cited
  rows); "mark each clause in the ask as decided or raised. The analyst should refuse a row whose agreed list holds a
  raised item" (#75); "say whether edited carried lines count against `test_budget_lines`" (#71).
- **Open, from run 96:** "require the plan to list every existing test whose expected outcome changes" (continues
  #57, plan side: three outcomes changed where the plan named two); "answer the constitution's B6 question ... for
  each fallback, not only the defaults" (continues #10); "name the shared helper before two places write the same
  logic" (#67: five duplicates found at review); "write the full converge test output to a file and print the failing
  names" (continues #34: "cut at '5553 lines left out'"); "move the rulings the plan cites into standing documents"
  (continues #21; #73); the long `8 …` rows in run-order.md "come back from search as omitted. Wrap them or add a
  line-range index" (new). "Place the documenter after architecture review" is declined as a misreading (section 3,
  claim 5); the need beneath it continues #48. Threat: "635 test lines against a 300-line budget ... the overrun
  becomes routine" (#71).
- **Open, from run 97:** analyst: "when a claim depends on database behaviour, batch the measurement request into
  round 1 and say that its answer settles the later questions" (#65); `merge_questions`: "group questions that
  measure the same shape into one request" (new, #72: 13 answers read "See Q48's answer"); "give the planner a spec
  feature directory, so the plan is written once and each round sends only its changes ... about 25 KB" (continues
  #53, a new reason); `dialogue_check`: "check each new name against the target module and the reserved-word list"
  (continues #16: `_bound`, `then`) "and check each test case against the entry point that can reach it" (new: case
  27); a note on how Odoo and ERPNext record periods in `knowledge/` (#73); write_tests: "parametrize them into tables
  rather than cut them, and name the owning module of every type" (#71; #66). Its "Q60 and Q64 asked the same thing"
  is declined as a misreading (section 3, claim 6).
- **Open, from run 98:** `dialogue_check`: "for each default, whether a wrong answer is loud or silent (B6)"
  (continues #10 and run 76's "every new default"); `merge_questions`: "each question must restate its context and
  name its referent" (#72: Q76 to Q79, "those rows"); "batch every measurement a round needs into one request ... the
  planner should say which numbers only the build can give" (#65); "run the repo's own gate rules against the
  sketches in the plan. The `sa.literal` sketch would have failed test_scope" (new); "cite backlog entries by quoted
  text, not line number" (#70); "the test step: write the reason for a 'check' outcome into the step record"
  (continues #36). Declined as misreadings (section 3): "Finding 3 was put to the operator three times"; "the plan put
  the documenter after the architect" (the need continues #48).

- **Taken, 2026-11-25, FR-150 (from run 99; found by the orchestrator; the operator: "exactly"),
  `changes/2026-11-25-a-mend-per-defect.md`:** a second `test_defect` report that names
  different tests from the one already mended gets a mend of its own; before, `Rework("mend_tests", at_most=1)` mended once
  and ignored later reports, so the builder, having diagnosed the second defect exactly ("psycopg cannot parse a
  timestamptz in that format"), could only repeat it until its attempts ran out and the run ended needs-me. A repeat
  report on the same tests stays unchased. The builder now names the tests in `defective_tests`; two mends at most.

- **Open, from runs 99 to 101 (2026-11-25, the orchestrator's reading at merge):** narrow the `red` step to the run's new
  tests (each of baseline, red and test runs the whole suite, about 5.5 minutes; test stays the gate; runs 100 and 101);
  give `write_tests` and `build` the line length and the test budget up front, not only as smells after (#71; runs 100,
  101); quote the one ruling row in the ask, since run-order.md is over 45,000 tokens and the planner missed a row (run
  99; the orchestrator's request practice); the analyst confirms each path the ask names in the code (run 101: the ask
  named the one-table save, which never removes); write each run's prior-art reading into the target's `knowledge/` (#73;
  run 101); the planner's search reaching `.factory-main/` (run 99). Declined as a misreading: run 101's "the operator
  answered one rule twice" (its batch held no duplicate after FR-151). Taken already: FR-150 and FR-151 (runs 99, 100).

# Retro suggestions for the factory and the orchestrator, and what became of them

Source: the Opportunities and Threats of all 29 retros in `bttr_erp/docs/retros/` (runs 27, 28, 30, 33, 43–63, 66–69; the tidy runs 31–42, 64, 65 and the runs before 27 have no retro). I left out suggestions that change bttr_erp itself (the "Next request:" items and the architect's code warnings). I checked each theme against `tomfactory/specs/001-near-loop-factory/changes/*.md`, the FR notes in `spec.md`, `prompts/*.md` and `prompts/fragments/*.md`, `personas/*.md`, `orchestrator/playbook.md`, the factory code where a prompt did not settle it (`factory/checks.py`, `driver.py`, `tables.py`), and the orchestrator's memory file `scope-idiom-iteration.md`. No retro suggestion for the factory was routed to `bttr_erp/docs/backlog.md`.

## Summary

**60 themes: 31 TAKEN, 7 DECLINED, 22 OPEN.**
- **2026-11-25:** themes 65 to 75 added from runs 79 to 98, all OPEN; #10, #14 and #30 now taken in part, #34 and #48 reopened, #52 homed in spec 006 item 3, #15 put to the operator to reconsider.
- 2 of the 31 TAKEN are taken only outside the factory: #58 lives in the orchestrator's memory and not in the playbook, and #20 lives in bttr_erp's `IDEALS.md`. #40 is TAKEN (unsure).
- 4 of the 22 OPEN are marked "unsure": #18, #38, #45 and #51.

**Raised most often**
1. **Give agents a shell or a scratch database** (#2: planner, plan check, test writer, builder): 14 retros. DECLINED three times as a change to containment. The measurement route (FR-100) was built in its place.
2. **Archive done backlog entries, so the architect reads only the open ones** (#47): 11 retros. TAKEN (FR-099).
3. **Send plan-check findings to the planner without the operator's round trip** (#1): 9 retros. TAKEN (FR-104), after being turned down twice.

**OPEN themes that keep coming back (best candidates)**
1. **#55: check the request against the constitution and the rule it cites before sending it** (runs 43, 46, 52, 53, 55, 68). The playbook only says to carry rulings into the request. It never says to check the request against them.
2. **#56: the request checks its own examples, counts, keys and test caps before it goes** (runs 48, 49, 50, 52, 60, 67). The playbook has no such line.
3. **#26: "guard" tests and plans with no new test, which the red step cannot accept** (runs 33, 44, 47, 52, 66, 67). The plan check allows "existing behaviour", but `tests_fail_first` still needs at least one new test to fail.
4. **#52: nobody tracks the operator's merge-time work** (threats in runs 43, 44, 61, 68, 69). It became more pressing once #50 was declined.
5. **#31: no step owns the before/after comparison a plan promises, such as "bytes unchanged"** (runs 46, 48, 67).

Also worth knowing:
- **#58 (open backlog warnings in the request's reading list)** is in the orchestrator's memory but not in the playbook. Run 59 asked for it again, and run 69 raised it as a threat.
- **#48 (one owner for amending and closing backlog entries)** was declined twice as "small", and run 67 hit it again.

The threat "Retro advice is not reaching the factory" (runs 49, 50, 51, 52) and "Factory changes keep waiting" (runs 59, 60) stopped once the batches of 2026-11-22 landed (FR-097 to FR-106).

## Themes

Key: **Runs** = the retros that raised the theme. **Aimed at** = who would make the change.

### Planning, and the plan check

**1. Plan-check findings should go to the planner automatically, so they do not wait on an operator send-back.**
Runs 45, 46, 48, 50, 51, 52, 57, 58, 63. Aimed at: orchestrator requests and step settings.
**TAKEN.** FR-104 and `changes/2026-11-22-the-planner-amends-from-the-check.md` added the `amend_plan` step. Before that it was turned down twice:
- `2026-11-22-a-builder-may-report-a-defective-test.md`: "not built here so this change stays one thing".
- `2026-11-22-an-agent-may-ask-for-a-measurement.md`: "still open".

Run 63 put it as "A 'passed' outcome that the operator must then send back costs him a round trip."

**2. Give agents a shell or a scratch database.**
Runs 28, 30, 33, 43, 44, 47, 49, 50, 51, 53, 54, 55, 56, 57. Aimed at: planner, check_plan, test writer, builder (step settings).
**DECLINED.**
- `2026-11-21-lessons-from-run-30.md`: "Agents have no shell by design; the fuller output is the cheaper answer."
- `2026-11-22-a-builder-may-report-a-defective-test.md`: "the largest change to containment since bubblewrap … it wants a decision of its own".
- `2026-11-22-an-agent-may-ask-for-a-measurement.md`: "a change to containment, which this is not".
- `2026-11-22-the-planner-amends-from-the-check.md`: "the measurement route has carried it".

FR-100 (an agent may reply `{"measure": …}`) was built in its place. Agents then asked for measurements in runs 58, 60, 63 and 68.
*2026-11-25, runs 79–98:* **#2 (shell), DECLINED:** asked again, run 92 (`pytest --collect-only`), no new reason. Stays DECLINED.

**3. The orchestrator should measure every statement and catalog text on a scratch database before sending a request.**
Runs 58, 59, 61, 63, 68. Aimed at: orchestrator requests.
**TAKEN.** The playbook says: "Before sending, measure on a scratch database every statement the request names, and every text a test will compare from the catalog (`pg_get_constraintdef`, `pg_indexes`)". Run 68 still needed a send-back for shapes nobody measured ("a tenant with no node, and a key with no tenant row").

**4. The plan check and the final review should see the answers to the planner's measurements.**
Run 60. Aimed at: check_plan inputs.
**TAKEN.** FR-102 (`2026-11-22-a-longest-line-and-answers-for-the-judges.md`).

**5. Each plan should name where it differs from what it carries over, and plan a test for every refusal or behaviour.**
Runs 28, 47, 51, 68. Aimed at: planner and check_plan.
**TAKEN.** FR-095. `prompts/plan.md` has "Where it differs from what it carries over" and "A test for every refusal". `check_plan.md` looks for "a refusal the build will make that no planned test shows". Gaps still reached merge after this:
- Run 51: "Give one test row for every behaviour the plan builds".
- Run 68: "check that each of them has a test under each condition".
*2026-11-25, runs 79–98:* **#5 (a test for every refusal or behaviour):** asked again, runs 80 ("list every difference from it, not 'the one'") and 83 ("a fix the request names must have a test before converge passes"). Stays TAKEN; note the asks.

**6. The planner should write new SQL as the library's own expressions.**
Run 30. Aimed at: planner.
**TAKEN.** FR-096 and `plan.md`: "New queries in the form the code will use".

**7. When a finding allows more than one fix, the plan check should name the one to take.**
Runs 30, 51. Aimed at: check_plan.
**TAKEN.** FR-096 and `check_plan.md`: "When a finding allows more than one fix, name the one the plan should take".

**8. The plan check should work out each planned test's expected values from that test's own setup and the plan's code.**
This covers seed rows, tables the setup creates, list order, the types passed, message fragments word for word, file counts and `match=` regexes.
Runs 44, 45, 46, 48, 49, 50, 56. Aimed at: check_plan.
**TAKEN.** FR-098 (`2026-11-22-a-builder-may-report-a-defective-test.md`). `check_plan.md`: "Work each one out from that test's own setup, step by step".

**9. The plan check should verify the plan's claims about PostgreSQL and Python, with one measured case for each type family.**
Runs 47, 55. Aimed at: check_plan.
**TAKEN.** FR-098. `check_plan.md`: "A rule the plan states for a whole family … ask for one measured case of each".

**10. The plan check should ask B6's question, "loud or silent?", of each new list, field, drop and refusal remedy.**
Runs 53, 54, 61, 62. Aimed at: check_plan.
**TAKEN.** FR-098 covers the remedy. FR-104 covers a new list or mapping ("is that mistake loud or silent?").
*2026-11-25, runs 79–98:* **#10 (loud or silent):** asked again, runs 82, 92, 96, 98, after run 76's open "every new default". Evidence: `dialogue_check.md:71-72` asks it only of "A new list, mapping or table of names"; run 98's lock key (`::text` following DateStyle and TimeZone) is a silent default the check passed. Change to: **TAKEN for new lists (FR-104); OPEN for defaults, fallbacks and replaced values in `dialogue_check`.**

**11. The plan check should ask what makes each planned test fail before the build.**
Run 62. Aimed at: check_plan.
**TAKEN.** FR-104.

**12. Every comment and docstring a run makes untrue should be found, searching the whole package and asking by behaviour.**
Runs 58, 61, 63, 66, 69. Aimed at: check_plan and orchestrator requests.
**TAKEN.**
- FR-104: "every module docstring … still true".
- FR-106: "search the whole package".
- Playbook: "Ask for the comments a run makes untrue by the behaviour it changes, not by fixed phrases."

**13. A planned case must be able to fail if its rule breaks, and the test writer must never drop a planned case.**
Run 69. Aimed at: check_plan and test writer.
**TAKEN.** FR-106 (`2026-11-23-a-case-that-shows-its-rule.md`).

**14. The plan check should flag work given to a step that cannot do it, or a file that does not exist.**
Run 53. Aimed at: check_plan and planner.
**TAKEN.** FR-099 and `check_plan.md`: "Work the plan gives to a step that cannot do it".
*2026-11-25, runs 79–98:* **#14 (work given to a step that cannot do it):** asked again, runs 89 and 92 (the plan told the builder to run `uv lock`; plan lines 24 of run 89's record, 41 of run 92's). `dialogue_check.md` names files only ("a file that step may not write"). Change to: **TAKEN for files; OPEN for commands.**

**15. The plan check should test the request's rulings against the constitution's B-rule that covers them, and against the parity ideal.**
Runs 51, 60. Aimed at: check_plan.
**DECLINED.** `2026-11-22-a-longest-line-and-answers-for-the-judges.md`: "it wants the constitution's rules indexed by subject, which is the target's document, not the factory's."
*2026-11-25, runs 79–98:* **#15 (MUSTs at plan check), DECLINED:** asked again, run 85, with a reason the decline did not weigh (B5 reached the operator only at merge; it asks for the MUSTs a plan touches, not an index). For the operator to reconsider.

**16. Narrow checks that were never added.**
- Check new names against every relation, index names included (run 45).
- Check that no single insert breaks two unique indexes (run 45).
- Check that each function a test calls is given the type it takes (run 48).
- Ask whether a column a handler orders or filters on can hold a null (run 59).
- A test's stand-in names must not be names a later run will take (run 67).

Aimed at: check_plan and test writer.
**OPEN.** I searched `check_plan.md`, `write_tests.md`, `test_writer.md` and the change records, and found none of these. No later retro repeats any of them.
*2026-11-25, runs 79–98:* **#16 (narrow checks):** asked again, runs 85 (section references exist) and 97 (new names against the module and reserved words: `_bound`, `then`). Stays OPEN; first repeats since seeding.

**17. The planner should estimate test lines against the budget and propose a split before planning.**
Run 45. Aimed at: planner.
**OPEN** for the planner. Nothing about this is in `planner.md` or `plan.md`. The orchestrator took the other half in its memory: "split big steps BEFORE requesting". Not repeated since.
*2026-11-25, runs 79–98:* **#17 (split before planning):** threat in run 82 ("$14.87 is 2.6 times the fifth step's cost"). Stays OPEN.

**18. The planner should ask its one question when the request contradicts itself, hits a platform limit or would break a constitution MUST.**
Runs 45, 46, 47. Aimed at: planner, and the lead for run 46.
**OPEN (unsure).** `fragments/asking.md` already lets any agent ask "if a wrong guess would matter", but no prompt names contradictions. The only record of this kind is `2026-11-21-the-sprint-cycle.md`, which declined it for spec kit's specify step only. After FR-100 the planner's questions have been measurements, in runs 58, 60, 63 and 68.

**19. The plan should state each message and placement once, and after a send-back list the places each ruling touches.**
Run 49. Aimed at: planner.
**OPEN.** Not in `plan.md` or `planner.md`. Not repeated.
*2026-11-25, runs 79–98:* **#19 (each message stated once):** asked again, runs 85 ("quote each message once, verbatim") and 94 ("state the exact refusal fragments"). Stays OPEN; now three retros.

**20. Before any refusal, the planner should name what Django or the open-source ERPs do.**
Run 51. Aimed at: planner.
**TAKEN, in the target, not the factory.** bttr_erp's `IDEALS.md` line 13: "When an edge case comes up, ask first how they handle it, before designing for it."

**21. The planner should cite a ruling only by who made it and where.**
Run 52. Aimed at: planner.
**OPEN.** The playbook's "Recording his rulings" covers the orchestrator only. Nothing is in `planner.md`.
*2026-11-25, runs 79–98:* **#21 (cite a ruling by who and where):** asked again, run 96 ("'Ruling 2' ... lives only at `scope.py:179`") and run 90's friction ("Ruling 2 is cited only by number"). Stays OPEN.

**22. When a removal leaves every caller passing the same value, the planner should offer the next removal.**
Run 66. Aimed at: planner.
**OPEN.** Not found in the prompts or personas.

**23. A plan should import modules that are not built yet inside the test, and red should report a collection error apart from a planned failure.**
Run 59. Aimed at: planner and the red check.
**OPEN.** FR-089's `tests_readable_command` (compileall) catches syntax errors only. `tests_fail_first` in `checks.py` accepts any non-zero exit.

### Tests and the build

**24. Tell the test writer it cannot run the tests and that red is the check; have it check its setup against the plan by reading.**
Runs 33, 43, 49, 53, 54, 56. Aimed at: test writer.
**TAKEN.** FR-098. `write_tests.md`: "You cannot run the tests … check by reading that every name a test imports and every table, file or row its setup relies on exists." The other half of these asks, a shell, is #2.

**25. A builder should be able to send a defective test back to the test writer.**
Runs 43, 56. Aimed at: builder and step settings.
**TAKEN.** FR-097 (`2026-11-22-a-builder-may-report-a-defective-test.md`). Run 56's other option, "stop and send it to the operator after the first failure", was DECLINED in the same record: "The route was chosen because the test writer's change is checked by running the tests".

**26. "Guard" tests that are expected to pass at red, and plans with no new test.**
Runs 33, 44, 47, 52, 66, 67. Aimed at: test writer, the red check, and orchestrator requests (run 66).
**OPEN.** `check_plan.md` accepts a passing test "unless the plan names it as existing behaviour". The red check (`tests_fail_first`) reads only the exit code: a mixed set passes, but a set where no test fails is always sent back. Run 67 asked that the factory "Pick one, so the two steps never disagree after approval." It keeps coming back (66, 67).

**27. The factory's code should measure line length on added code, tests and docstrings, and on a plan's code blocks.**
Runs 33, 49, 59, 60, 61, 62. Aimed at: step settings and checks.
**TAKEN.** FR-101 (`lines_within_length`) and FR-104 (`plan_lines_within_length`). Run 62's other half, a mechanical check that each id sits on its own row, was DECLINED in `2026-11-22-the-planner-amends-from-the-check.md`: "That is one codebase's convention, not the factory's".

**28. When the plan gate refuses for a mechanical reason, return the refused text and the offending line so the planner edits it.**
Run 68. Aimed at: step settings.
**OPEN.** `plan_lines_within_length` returns up to 5 lines, cut to 60 characters, with "Wrap them". `previous_plan` is filled only on an operator send-back (`driver.py`), so the planner does not get its refused plan back. FR-105 fixed the attempt count, which is what actually cost run 68. Not repeated.

**29. A check that rewraps, or flags, any prose paragraph a run edits.**
Runs 66, 67. Aimed at: documenter and checks.
**OPEN.** FR-101 measures length only and skips the documentation paths. Raised twice in a row (run 67: "carried from the last retro").

### Evidence, records, inputs

**30. The factory itself should write the red and green output into the record and give it to the architect, converge and the documenter.**
Runs 27, 28, 30, 33, 43, 45, 47. Aimed at: step settings and the record writer.
**TAKEN.** FR-094 (red_output to the architect and the final review) and FR-095 (the record holds both, written by the factory).
- Records carry "The tests before and after the build" from run 30 on.
- The reviews of runs 30 to 47 still complained, because they read the record before the factory finishes it.
- The step order was never changed. The architect still runs before the documenter. The architect has had red_output since FR-094.
*2026-11-25, runs 79–98:* **#30 (evidence to every step):** asked again, runs 79, 85, 94 (the documenter). Evidence: `prompts/document.md`'s inputs are `request`, `plan`, `diff` and `measured` (FR-136): no test output, so no suite result line. Change to: **TAKEN except for the documenter.**

**31. A step should own the before/after comparison a plan promises, such as "bytes unchanged" or the `design.migrations` comparison.**
Runs 46, 48, with threats in 46, 48 and 67. Aimed at: step settings, the test step.
**OPEN.** No change record mentions it. FR-100 lets an agent ask during its own step, but not after the build. The orchestrator does it by hand (memory: "How I verify a tidy"). Run 67's threat: "Converge 'could run nothing', so the byte-for-byte check … is still the orchestrator's to do before merge."

**32. A retry after an agent-program failure should be told the real cause.**
Run 27. Aimed at: step settings.
**TAKEN.** FR-094 (`2026-11-21-the-sprint-cycle.md`).

**33. A resume should write the record again and keep what the build wrote.**
Run 27, and run 43's threat. Aimed at: other (resume).
**TAKEN.** FR-094(3), and FR-067 in `2026-11-21-resume-keeps-the-build.md`.

**34. Fuller test output: keep both ends, list failures per test, and give converge the whole list of failing tests.**
Runs 30, 58. Aimed at: the test step and converge inputs.
**TAKEN.** FR-096 (`kept_output`). `-rfE` was added in bttr_erp (`2026-11-21-lessons-from-run-30.md`). Run 58 still saw output cut at "655 lines left out".
*2026-11-25, runs 79–98:* **#34 (fuller test output):** asked again, runs 82, 83, 84, 91, 96 (and 80's "keep the tail", which FR-096 already does). The ask now is a list of failing test ids apart from the cut output: run 96 "cut at '5553 lines left out', so the failure list was inferred"; run 83 "34,287 lines". Change to: **OPEN again: the failing ids, listed whole.**

**35. Leave the run record and the repeated plan out of the diff the architect and converge read.**
Runs 30, 43, 45, 50, 51, 52, 55. Aimed at: architect and converge inputs.
**TAKEN.** FR-099 (`diff_since_base(leaving_out=)`).

**36. The run record should say which check sent a step back, and why a build was sent back.**
Run 63. Aimed at: the record writer.
**TAKEN.** FR-104 ("check: tests_pass").
*2026-11-25, runs 79–98:* **#36 (which check sent a step back):** asked again, runs 93 and 98. The record already shows "| test | 1 | check: tests_pass |" (run 98 record line 525); the further ask is which tests failed (#34). Stays TAKEN.

**37. Say where the documenter's account goes, and never overwrite it.**
Runs 45, 58, 62, 63. Aimed at: documenter and the record writer.
**TAKEN.** FR-104, and `document.md`: "your `summary` is put in it, under 'What changed'".

**38. Run records should be easier to read: a summary at the top, and the plan and rulings before the test output.**
Runs 45, 48. Aimed at: the record writer and documenter.
**OPEN (unsure).** Records now put the approved plan before the test output, but no change record says so, and there is no summary at the top. Not repeated after run 48.

**39. Name runs by number, and have requests point at records by path or id, not by a typed glob.**
Runs 30, 52. Aimed at: orchestrator requests.
**TAKEN.** `2026-11-21-lessons-from-run-30.md` ("requests name the records they point to by path"). Playbook: "Name the records a run should read **by path**."

**40. Mark which commits under docs/ come from the factory's own steps.**
Run 58. Aimed at: other (commits).
**TAKEN (unsure).** FR-103 subjects ("Backlog:", "Docs:", "Retro:") and the `Factory-Step:` trailer do this, but the record cites the operator, not run 58.
*2026-11-25, runs 79–98:* **#40 (factory commits marked):** asked again, run 89: converge flags paperwork commits as out of plan; `converge.md` does not mention the `Factory-Step:` trailer. Stays TAKEN (unsure), the converge half open.

**41. Retry `architecture_review` when it errors, instead of skipping it.**
Run 46. Aimed at: step settings.
**OPEN.** In `driver.py` a failed advisory step is discarded and the run moves on. Memory says the operator "will want that review", and the orchestrator ran the architect by hand. Not repeated.

**42. A second review pass should be told it is a second pass and given the diff since the last.**
Run 60. Aimed at: architect and converge.
**DECLINED.**
- `2026-11-22-a-longest-line-and-answers-for-the-judges.md`: "left until it costs again".
- `2026-11-22-the-planner-amends-from-the-check.md`: "Small, and not what cost these runs."

**43. Give converge the plan as changed by a hand fix or a send-back.**
Run 56. Aimed at: converge inputs.
**DECLINED.** `2026-11-22-a-builder-may-report-a-defective-test.md`: "The plan is what the operator approved; a hand fix is on the branch as its own commit and in the run's record".

**44. Give converge the record of who approved each departure from the plan.**
Run 67. Aimed at: converge inputs.
**OPEN.** Not in `converge.md` or the FRs.

**45. Read IDEALS.md from the branch head on every step.**
Run 51. Aimed at: step settings.
**OPEN (unsure).** FR-082 still says "read from the commit the run starts at", and no record answers run 51.

**46. Mark a draft kept from a partial run with the commit it was written against.**
Run 46. Aimed at: orchestrator.
**OPEN.** Not in the playbook or memory.

### Backlog and documents

**47. Archive done backlog entries, give the architect only the open ones, and close stale ones.**
Runs 33, 43, 44, 48, 50, 51, 52, 55, 56, 57, 58. Aimed at: architect and documenter.
**TAKEN.** FR-099. `architecture_review.md`: "moved whole to `backlog-done.md`". The memory records a one-off triage on 2026-11-22.

**48. Give one step alone the job of amending and closing backlog entries.**
Runs 44, 60, 67. Aimed at: documenter and architect.
**DECLINED.**
- `2026-11-22-a-longest-line-and-answers-for-the-judges.md`: "A prompt change for the architect and the documenter; small, and not what cost this run."
- `2026-11-22-the-planner-amends-from-the-check.md`: "Small, and not what cost these runs."

Run 67 hit it again after both: "That saves the documenter's empty pass and the architect's note."
*2026-11-25, runs 79–98:* **#48 (one owner for amending and closing backlog entries), DECLINED twice as "small":** asked again, runs 93, 96, 98, with costs the declines did not weigh: run 96 "the reviewer closed entries 317 and 319 by hand"; run 98 "four answered warnings stayed in place". The table runs architecture_review before document (`factory/tables.py:52-53`, `on_pass="document"`), so the architect cannot see the documenter's edits. Recommend: **reopen.**

**49. The plan should name documents outside every step's paths as left for the operator, and give no step a file it cannot write.**
Runs 43, 44, 51, 52, 53. Aimed at: planner and step paths.
**TAKEN.** FR-099. `plan.md`: "name it in the plan as left for the operator at merge."

**50. Let the documenter, or a step, edit the run-order rows a plan names.**
Runs 52, 69. Aimed at: step paths.
**DECLINED.** `2026-11-23-a-case-that-shows-its-rule.md`: "an agent writing there is how a ruling once came to be filed under his name."

**51. Let the documenter write under specs/ and knowledge/findings, or name a step that owns marking findings superseded.**
Runs 44, 51, with threats in 43, 44 and 51. Aimed at: step paths (`.factory.toml docs_paths`).
**OPEN (unsure).** FR-099 sends these to the operator at merge. bttr_erp's `docs_paths` is still `["docs/", "CHANGELOG.md"]`, and no record declines this.

**52. Track the operator's merge-time work somewhere other than converge's notes.**
Threats in runs 43, 44, 61, 68, 69. Aimed at: orchestrator and other.
**OPEN.** Not in the playbook, which only has "record in the run order what was built" after merge. Run 61: "None of this is tracked anywhere except converge's notes." Raised again in 68 and 69.
*2026-11-25, runs 79–98:* **#52 (merge-time work):** threats in runs 80, 81, 82, 85, 86, 89, 91, 97. Now has a home: spec 006 item 3 ("Merging and recording"), and the playbook's "merging an accepted run is the orchestrator's" (tomfactory 7d9446a). Change to: **OPEN, homed in spec 006 item 3.**

**53. Spec-kit leftovers in the sprint: create the feature directory, or take spec kit out of the plan and converge prompts.**
Runs 43, 44. Aimed at: orchestrator run setup and prompts.
**OPEN.** `plan.md`, `write_tests.md`, `build.md` and `converge.md` still carry their "If this codebase uses spec kit" sections, which date from 2026-11-18 (git log). Not repeated after run 44, apart from the specs/ documents in #51.
*2026-11-25, runs 79–98:* **#53 (spec-kit leftovers; feature directory):** asked again, runs 89 and 97, with a new reason (the plan "restated in full each round (about 25 KB)"). Stays OPEN.

**54. Run 27's spec-kit stage fixes.**
- specify should ask its one question when instructions collide.
- The analyze step's checklist clashes with "change no file".
- The plan should state the expected red result for each test.
- Regenerate tasks.md after a send-back.

Run 27. Aimed at: other (spec kit stages).
**DECLINED.**
- `2026-11-21-the-sprint-cycle.md`: "spec kit's own stages, which a sprint does not run".
- FR-096 rejects predicting the red result: "a predicted list has been wrong every time it was tried."

### Orchestrator requests

**55. Before sending, check the request against the constitution, the ideal it cites and the layer rules, and say which rule wins.**
This also covers asking the operator before planning when a request would break a MUST.
Runs 43, 46, 52, 53, 55, 68. Aimed at: orchestrator requests.
**OPEN.** The playbook says "Carry his standing rulings into the request where they apply", which is carrying, not checking. Neither the memory nor the change records mention it. It keeps coming back:
- Run 46: a MUST broken, which took two send-backs.
- Run 52: a refusal against the cited ideal.
- Run 53: B6 against Odoo.
- Run 55: Django against a fixed form.
- Run 68: B8.

**56. The request should check its own examples, counts, keys, test caps and single readings before it is sent.**
It should also say whether the line limit covers test files, and give the starting migration number.
Runs 48, 49, 50, 52, 60, 67. Aimed at: orchestrator requests.
**OPEN.** Not in the playbook or memory. It keeps coming back. Run 67: "count a list before giving its number".
*2026-11-25, runs 79–98:* **#56 (the request checks itself):** asked again, runs 81, 82 (and 79's "the request left out two facts"). Stays OPEN.

**57. The request should name the existing tests that pin what changes, sorted by whether they should move, and grep the callers and monkeypatches of a removed name.**
Runs 33, 60, 61, 62, 66. Aimed at: orchestrator requests.
**TAKEN.**
- Playbook: "Name the existing tests that pin what the run changes, sorted into 'expected to move' and 'read only, should not move'. Grep for them".
- Callers are only in memory ("ask for 'every caller of X'"), not in the playbook. Run 66 asked for callers and monkeypatches again.
*2026-11-25, runs 79–98:* **#57 (existing tests that pin):** asked again, run 96, for the planner. Stays TAKEN for requests; the plan side is open.

**58. Put every open backlog entry that names the requested step into the request's reading list.**
Runs 58 and 59, with threats in 61 and 69. Aimed at: orchestrator requests.
**TAKEN (in memory only).** Memory: "put in the reading list every open backlog entry that names the step being requested". The playbook lacks it. Run 69's threat: "No step in this run's record carries an entry into the request of the run it names".
*2026-11-25, runs 79–98:* **#58 (open backlog entries in the request's reading list):** threats in runs 82, 89, 93. Stays TAKEN (memory only).

**59. When a request takes a backlog item, say which of its names are in scope, reuse its example or say why not, and ask for one test row per outcome.**
Runs 47, 54. Aimed at: orchestrator requests.
**OPEN.** Not in the playbook or memory. Not repeated.

**60. A ruling the request would make in passing should be marked as the operator's to confirm.**
Run 60. Aimed at: orchestrator requests.
**TAKEN.** Playbook: "A ruling the request would make in passing (which of two readers is right) is the operator's: ask him, or leave it out of the request."


**61. A step that runs again after a question should count the work its asking attempt left, not only what it changes after the answer.**
Run 79. Aimed at: the factory (`driver.run_step`, `workspace.changed`).
**TAKEN 2026-11-23, FR-108:** `driver.counted_from`; an answered question is no longer shown as a failure. Was: The test writer wrote its tests, asked for a measurement, and was answered. Each attempt reads `dirty_before` afresh, so the tests already in the checkout counted as there before the step began. The resumed test writer rightly kept them as written, `tests_added` saw no change, and it failed three attempts: needs-me with "no test file was written under tests/". `factory resume` discarded the draft (a copy kept outside the run) and the test writer wrote again. Fix: take `dirty_before` from the step's first attempt in a question chain, or let `tests_added` count changes since the step's first start. Measuring and asking are the factory's own path, so this will recur on every asked-for measurement in write_tests or build.
Run 79's retro saw the same cost from the agent's side: attempt 3 "was spent checking existing work" because the retry note said no test file was written. Its fix: build a retried step's note from the worktree's diff.

**62. Let a step's finding about PostgreSQL come back as a measurement, not a test comment: from amend_plan, and from build.**
Run 79. Aimed at: the factory (amend_plan's reply format, the build prompt) and check_plan's persona.
**TAKEN 2026-11-23, FR-108:** in the prompts of amend_plan, build, mend_tests and check_plan. Was: amend_plan could not ask for a measurement without writing a whole plan, so write_tests asked instead (4.0 minutes, $1.65). The builder found that `[2026-01-01,` reads as a date and left it in a test comment, so converge handed the merge an unmeasured finding (the orchestrator measured it at merge: true). check_plan should also check that each measured statement is the one the plan sends (same cast, same type, bound or untyped). Fits the operator's direction of 2026-11-23: make interruptions cheap.

**63. Try spec kit's cycle again, on another project, with the cheaper grades.**
The operator, 2026-11-23: "I wonder if speckit is cheaper when the weaker models were used, we tested it on Fable I think. Maybe try it again on a different project someday." Aimed at: an experiment, no factory change.
**OPEN, an idea.** Spec kit's cycle has more stages (specify, clarify, plan, tasks, analyze, converge) and so more agent calls; it was tried when every step ran on the costliest model, before FR-088. Now FR-109's grades, a retry that climbs, and FR-112's `[steps.<name>]` make it a settings experiment: put specify, clarify, tasks and analyze on `light` or `middle` in that project's `.factory.toml`, keep plan and converge on `standard`, and compare the run records' time-and-cost tables (with their Model column) against bttr_erp's sprint runs. A small target with a clear first feature suits it. The operator, the same day: "I don't want to disrupt erp progress. Rather do a fuzzy project on spec kit. Not today though": so a separate, fuzzy project, never bttr_erp, on a later day; compare it with the sprint cycle on one fuzzy feature.

**64. When the agent program is missing for a moment, wait and try once more before ending the run.**
Run 84 (bttr_erp). Aimed at: the factory (`agent.run_agent`, `workflow.reply_failure`).
**OPEN.** check_plan ended the run needs-me with "the agent program exited with code 1"; its stderr said "No executable claude found for current version", most likely Claude Code updating itself at that moment. It was back a minute later and `factory resume` carried on. One retry after a short wait, for that message only, would make the interruption free (the operator's direction of 2026-11-23: cheap to interrupt and recover).


**65. Ask for every measurement a plan rests on in the first round, and say which numbers only the build can give.**
Runs 81, 86, 90, 91, 92, 94, 97, 98. Aimed at: dialogue_analyst, dialogue_planner, dialogue_check.
**OPEN.** The measure route exists (FR-100; `dialogue_analyst.md:47`), but nothing says "first round" or "batch".
Run 91: "This run needed two rounds". Spec 006 item 1 (the factory measures) is the larger answer.

**66. Check each claim about named code by reading it before the plan ends: a call site, a helper's location, a
type's owning module, a safety claim.** Runs 84, 86, 89, 97. Aimed at: dialogue_planner, dialogue_check.
**OPEN.** FR-131 has agents read the ask against the artifacts, not the code. Run 86: "a wrong claim survived two
plan steps and surfaced at the costliest step".

**67. One fact, one place, at plan time: does a new rule, query or helper repeat one that exists?** Runs 81, 84, 92,
96. Aimed at: dialogue_check and dialogue_architect. **OPEN.** Today found at review (run 96: five duplicates; the
architect watches coupling since tomfactory 0daebe6), after the build wrote them.

**68. Converge lists each departure from the plan, and each architect warning's disposition, as its own item for the
operator.** Runs 84, 91, 93 (and run 83's "The architect's warnings were not all closed"). Aimed at: converge.
**OPEN.** `converge.md` sorts differences into four kinds; a departure lands under "An implementation detail".

**69. The plan's file list is complete (generated docs, backlog files) and is checked against the diff.** Runs 83,
94. Aimed at: dialogue_planner, converge. **OPEN.**

**70. Cite a backlog entry or code by its heading or symbol and quoted words, never by line number.** Runs 79, 80,
82, 98. Aimed at: the planner, the orchestrator's requests. **OPEN.** Run 98: "'architect's run-97 warning at line
341' pointed at the orchestrator's warning". The playbook's "first words, not its label" covers records only.

**71. Say what `test_budget_lines` counts (edited lines, a vendored fixture) and what a complete set needs.** Runs
92, 95, 96, 97. Aimed at: write_tests prompt, `.factory.toml`, and the operator (the budget is his). **OPEN.** FR-107
made the budget a smell; run 96 measured 635 against 300 and calls the overrun "routine".

**72. `merge_questions` groups measurements of one shape, and every question stands alone.** Runs 97, 98. Aimed at:
`prompts/merge_questions.md`. **OPEN.** The prompt says "When in doubt, do not merge"; run 97 left eight overlapping
measurements of one two-row UPDATE apart (13 answers "See Q48's answer"); run 98's Q76 to Q79 lean on "the same
setup". Not the misread parts (section 3).
*2026-11-25, runs 99 and 100:* **#72 (plain duplicates):** run 99 asked one reason-for-a-change choice three times
(Q89, Q92, Q94) and run 100 one end-date choice twice (Q98, Q101), none merged: run 100's merge was given as a flat
list and read as none, run 99's was not proposed. Change to: **TAKEN for questions asking one decision (FR-151,
`changes/2026-11-25-one-decision-one-question.md`); OPEN for measurements of one shape and questions that stand
alone.**

**73. What is measured, ruled or researched once is kept in the target's standing documents, for the next plan.**
Runs 91, 94, 96, 97. Aimed at: the orchestrator and the documenter. **OPEN.** Run 91: "the next plan would not need
to ask"; run 96: a ruling living only in a code comment.

**74. The record's figures: split waiting for the operator from time between steps, and say how totals round.**
Runs 83, 85, 86, 91, 93, 96. Aimed at: the record writer. **OPEN, small.** Most of the gaps are explained: the retro
reads the record before its own row is added (run 86: record 30.6 min, $6.51 = the retro's 29.9, $6.50 plus the
retro's row, 0.7 min, $0.01), and rows round to 0.1 min and $0.01. One sentence in the record would end the asks.

**75. The ask marks each clause decided or raised, and every requirement row it cites is checked to exist and be
current before the dialogue.** Run 95 (and run 90's missing ruling). Aimed at: the orchestrator's ask, the analyst.
**OPEN.** FR-134 gives agents main's copy; nothing checks a cited row. Run 95: rounds 2-4 "cost $6.76" on an
overruled row.

Singles, OPEN, not themed: prose and code sample agree (82); the request says which later step reads each new fact
(82); baseline names the tests that compare whole rows (83); an "unchanged" count carries a cost note (85); decision
rows name the reads they cover (85); the documenter copies request measurements verbatim (89); whether baseline and
red need the whole suite (93); run-order rows too long for search (96); a test case reachable from its entry point
(97); plan sketches checked against the repo's own test rules (98).

