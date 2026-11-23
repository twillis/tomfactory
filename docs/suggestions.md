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

# Retro suggestions for the factory and the orchestrator, and what became of them

Source: the Opportunities and Threats of all 29 retros in `bttr_erp/docs/retros/` (runs 27, 28, 30, 33, 43–63, 66–69; the tidy runs 31–42, 64, 65 and the runs before 27 have no retro). I left out suggestions that change bttr_erp itself (the "Next request:" items and the architect's code warnings). I checked each theme against `tomfactory/specs/001-near-loop-factory/changes/*.md`, the FR notes in `spec.md`, `prompts/*.md` and `prompts/fragments/*.md`, `personas/*.md`, `orchestrator/playbook.md`, the factory code where a prompt did not settle it (`factory/checks.py`, `driver.py`, `tables.py`), and the orchestrator's memory file `scope-idiom-iteration.md`. No retro suggestion for the factory was routed to `bttr_erp/docs/backlog.md`.

## Summary

**60 themes: 31 TAKEN, 7 DECLINED, 22 OPEN.**
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

**15. The plan check should test the request's rulings against the constitution's B-rule that covers them, and against the parity ideal.**
Runs 51, 60. Aimed at: check_plan.
**DECLINED.** `2026-11-22-a-longest-line-and-answers-for-the-judges.md`: "it wants the constitution's rules indexed by subject, which is the target's document, not the factory's."

**16. Narrow checks that were never added.**
- Check new names against every relation, index names included (run 45).
- Check that no single insert breaks two unique indexes (run 45).
- Check that each function a test calls is given the type it takes (run 48).
- Ask whether a column a handler orders or filters on can hold a null (run 59).
- A test's stand-in names must not be names a later run will take (run 67).

Aimed at: check_plan and test writer.
**OPEN.** I searched `check_plan.md`, `write_tests.md`, `test_writer.md` and the change records, and found none of these. No later retro repeats any of them.

**17. The planner should estimate test lines against the budget and propose a split before planning.**
Run 45. Aimed at: planner.
**OPEN** for the planner. Nothing about this is in `planner.md` or `plan.md`. The orchestrator took the other half in its memory: "split big steps BEFORE requesting". Not repeated since.

**18. The planner should ask its one question when the request contradicts itself, hits a platform limit or would break a constitution MUST.**
Runs 45, 46, 47. Aimed at: planner, and the lead for run 46.
**OPEN (unsure).** `fragments/asking.md` already lets any agent ask "if a wrong guess would matter", but no prompt names contradictions. The only record of this kind is `2026-11-21-the-sprint-cycle.md`, which declined it for spec kit's specify step only. After FR-100 the planner's questions have been measurements, in runs 58, 60, 63 and 68.

**19. The plan should state each message and placement once, and after a send-back list the places each ruling touches.**
Run 49. Aimed at: planner.
**OPEN.** Not in `plan.md` or `planner.md`. Not repeated.

**20. Before any refusal, the planner should name what Django or the open-source ERPs do.**
Run 51. Aimed at: planner.
**TAKEN, in the target, not the factory.** bttr_erp's `IDEALS.md` line 13: "When an edge case comes up, ask first how they handle it, before designing for it."

**21. The planner should cite a ruling only by who made it and where.**
Run 52. Aimed at: planner.
**OPEN.** The playbook's "Recording his rulings" covers the orchestrator only. Nothing is in `planner.md`.

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

**35. Leave the run record and the repeated plan out of the diff the architect and converge read.**
Runs 30, 43, 45, 50, 51, 52, 55. Aimed at: architect and converge inputs.
**TAKEN.** FR-099 (`diff_since_base(leaving_out=)`).

**36. The run record should say which check sent a step back, and why a build was sent back.**
Run 63. Aimed at: the record writer.
**TAKEN.** FR-104 ("check: tests_pass").

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

**53. Spec-kit leftovers in the sprint: create the feature directory, or take spec kit out of the plan and converge prompts.**
Runs 43, 44. Aimed at: orchestrator run setup and prompts.
**OPEN.** `plan.md`, `write_tests.md`, `build.md` and `converge.md` still carry their "If this codebase uses spec kit" sections, which date from 2026-11-18 (git log). Not repeated after run 44, apart from the specs/ documents in #51.

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

**57. The request should name the existing tests that pin what changes, sorted by whether they should move, and grep the callers and monkeypatches of a removed name.**
Runs 33, 60, 61, 62, 66. Aimed at: orchestrator requests.
**TAKEN.**
- Playbook: "Name the existing tests that pin what the run changes, sorted into 'expected to move' and 'read only, should not move'. Grep for them".
- Callers are only in memory ("ask for 'every caller of X'"), not in the playbook. Run 66 asked for callers and monkeypatches again.

**58. Put every open backlog entry that names the requested step into the request's reading list.**
Runs 58 and 59, with threats in 61 and 69. Aimed at: orchestrator requests.
**TAKEN (in memory only).** Memory: "put in the reading list every open backlog entry that names the step being requested". The playbook lacks it. Run 69's threat: "No step in this run's record carries an entry into the request of the run it names".

**59. When a request takes a backlog item, say which of its names are in scope, reuse its example or say why not, and ask for one test row per outcome.**
Runs 47, 54. Aimed at: orchestrator requests.
**OPEN.** Not in the playbook or memory. Not repeated.

**60. A ruling the request would make in passing should be marked as the operator's to confirm.**
Run 60. Aimed at: orchestrator requests.
**TAKEN.** Playbook: "A ruling the request would make in passing (which of two readers is right) is the operator's: ask him, or leave it out of the request."

