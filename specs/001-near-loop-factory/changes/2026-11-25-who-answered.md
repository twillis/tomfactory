# Change record: who answered, what the tests said, and the backlog's owner (2026-11-25)

Made outside spec kit, for spec kit to review later. The evidence is bttr_erp's run 98, its record and its retro:
twelve of its thirteen answers were the orchestrator's and every one was recorded as the operator's; the test step's
first attempt sent the work back and nothing said why; the documenter wrote "I did not have the suite's pass or fail
result". Built as FR-139 to FR-144, with FR-105, FR-121, FR-127 and FR-136 amended. Spec 006, item 8, is built.

**Asked for by the operator.** That the record never puts the orchestrator's words under his name (spec 006, item 8).
That the failing tests are read from the machine-readable report test runners already write, not parsed from their
text. One owner for the backlog (suggestion-box theme #48). The rest are mechanics, the orchestrator's.

**Changed**

1. **FR-139, who answered is recorded.** `workflow.ANSWERERS` is `("operator", "orchestrator")`; the lead answers
   inside the factory, as before. `operations.answer(..., by=)` and `factory answer --by operator|orchestrator`
   (default operator) record who answered; anyone else is refused, nothing recorded. In a batch, `answer
   (orchestrator):` or `answer (operator):` in place of `answer:` says who gave that one answer; a plain `answer:` is
   the `--by` one's; `answer (lead):` or any other name is refused (`dialogue.ANSWER`, `dialogue.Answer`,
   `parse_batch(text, questions, by)`). A merged duplicate (FR-132) gets the answer and the answerer of the question
   it was merged into. The budget's yes after a pause is recorded as whoever `--by` says. Store migration
   `_v7_who_answered`: SQLite cannot widen a CHECK in place, so `questions` is remade with `'orchestrator'` allowed,
   every row copied as it was (the pattern of `_v5` and `_v6`). `orchestrator/playbook.md`, "While a run is open"
   and "In a dialogue": measurements go in `--by orchestrator`, or after `answer (orchestrator):` in a batch; his
   answers go in as his.
2. **FR-140, every text says who really answered.** The asking step's prompt and the plan check's and final
   review's `planning_answers` already printed `The {answered_by} answered`, so they now say "The orchestrator
   answered"; `factory show` the same. The dialogue's transcript (and so the run's record) says "Answered by the
   operator:" or "Answered by the orchestrator:" in place of "Answered:". A merged duplicate is printed as merged,
   naming the question it was answered under, without its answer again (run 98's retro read the repeated answer as
   the operator asked three times); its stored answer stays, for the agent that asked it. The retro's
   `operator_feedback` takes only `answered_by == "operator"`. `records.attempts_counted` (FR-105) leaves out a run
   that asked a question the operator *or the orchestrator* answered (see below).
3. **FR-141, the failing tests, from the test report.** New setting `test_report`: a JUnit XML file the test command
   writes. `checks._tests_judged` removes an old one before the tests run (as it does the coverage report), and
   `checks._failing` reads the new one with `xml.etree`: every `testcase` with a `failure` or `error` child, as
   `classname::name` and its message (one line, 300 characters), the first 20 kept with the count of all, on the
   check's result as `failing`. A missing or unreadable report is no report. `run_record._result`: a row whose
   check failed reads `check: tests_pass (failed: a, b, … and N more)` (five named); with no report, `check:
   tests_pass (<the check's message, one line, 160 characters>)`, with `|` escaped. `driver._failure` (what the
   builder's next attempt is given) names every failing test kept, with its message. The first build, a text parser
   of pytest's `FAILED` lines, was replaced by this at the operator's word.
4. **FR-142, the final tests reach the writers.** `run_record.measured` begins with what the last run of the tests
   after the build said (the last step with the `tests_pass` check): which step and attempt, passed or failed with
   the failing tests and their messages, and the test command's own last line, which carries its counts; the
   factory reads no counts itself. The documenter already had `measured`; the retro is given it now (`tables.py`,
   `prompts/retro.md`). `document.md` adds "whether they passed" to the claims it may make only from those facts.
5. **FR-143, three prompt lines.** `prompts/fragments/dialogue.md` (every speaker): each question stands alone,
   restating its setup and naming its referents. `prompts/dialogue_check.md`: each default or derived value the plan
   introduces, would a wrong one fail loudly or silently; raise a silent one (B6), with run 98's lock key built from
   a value's session-dependent text form. `personas/planner.md` (the plain planner and the dialogue's): cite a
   backlog entry by quoting its text, never by its line number.
6. **FR-144, the architect owns the backlog.** New settings `backlog_file` (`docs/backlog.md`) and
   `backlog_done_file` (`docs/backlog-done.md`), and the inputs of the same names. New scope `docs_but_backlog`: the
   documentation paths except those two files; the documenter has it, so `changes_allowed` undoes a change of its to
   the backlog as a guard and the run stops needs-me. `architecture_review.md` names both files from the settings,
   the run's name (`run_name` is now its input), and says to close every entry answered, the plan's named ones among
   them, since no later step will. `document.md` says the files are the architect's. `personas/planner.md` and
   `prompts/fragments/dialogue.md`: a plan names the entries its run answers, by quoted text, for the architect.

**Mechanics chosen in the build, for the operator to confirm**

- **FR-105 reads the orchestrator's answer as an outside answer.** The brief said the send-back logic should take
  only the operator's answers. That function is the attempt count, not a send-back, and FR-105 was written for run
  68, where an answered *measurement* (the orchestrator's) had used up the planner's attempts. Counting the
  orchestrator's answers now would bring that back the moment answers are honestly attributed. So a question the
  operator or the orchestrator answered does not count; only the lead's still does.
- **The batch marker** is `answer (orchestrator):` / `answer (operator):`, a variant of `answer:` so a batch written
  before still reads, and the editor's header says so. `factory answer --by` takes the same two names; argparse does
  not list them (the presentation layer holds no rules), the operation refuses anything else.
- **The budget question** answered `--by orchestrator` is recorded as the orchestrator's. It is the operator's
  decision (spec 006); the factory records who gave it rather than refusing.
- **The retro may still write the backlog** (its scope is `docs`): it is told to write one note. A tidy-code run has
  no architect and may change the backlog (`not_tests`), as before.
- **Test ids** are JUnit's `classname::name` (pytest: `tests.test_hello::test_greets`), not pytest's node id.
- `tests/test_size.py`'s tripwire is raised from 4,300 to 4,400 lines; the factory went from 4,248 to about 4,340.

**For bttr_erp, not changed here.** Its `.factory.toml` would need `--junitxml=test-report.xml` added to its
`test_command`, the line `test_report = "test-report.xml"`, and `test-report.xml` in its `.gitignore`.

**Not in this change**

- A send-back (`factory revise`) the orchestrator writes is still recorded as the operator's (run 91's case).
- Who answered is not shown in `factory questions`' batch before it is answered: nothing has answered yet.

Tests: `tests/test_who_answered.py` (new, 33 cases); the suite went from 619 to 654 passed. Each new case failed
first for the reason it names, except the JUnit cases of FR-141, written after the coordinator changed the approach
from a text parser (their predecessors had failed first). Followed by existing tests: `tests/test_dialogue.py`'s
batch test reads `parse_batch`'s answers as `Answer`s; `tests/test_cycle.py`'s FR-103 row ends with the check's
message; `tests/test_step_shape.py` gains the `docs_but_backlog` scope's rows; `tests/test_operations.py` expects a
check's `failing`; `tests/test_sprint_cycle.py` finds the closed-entries file as `{{backlog_done_file}}`;
`tests/test_size.py`'s limit.
