# Change record: a step keeps its work across a question (2026-11-23)

Made outside spec kit, for spec kit to review later.

**Asked for by the operator.** The operator, 2026-11-23, after run 79's stop: "the more that we can interrupt the
process and recover from it and the cheaper we can make it the more agile we can be that is a competitive advantage
you should focus on"; then "Go with factory fix". Suggestions 61 and 62.

**The record:** bttr_erp's run 79. write_tests wrote its tests and asked for a measurement; the orchestrator
answered. Attempt 2 kept the tests as written and failed `tests_added` ("no test file was written under tests/"),
since each attempt read `dirty_before` afresh. Attempt 3 was told the same and spent itself checking existing work;
the run ended needs-me, and `factory resume` threw the draft away for attempt 4 to write again: 2.8 minutes and
$1.34 lost, and an hour of waiting. The same run's builder found `[2026-01-01,` read as a date and left it in a test
comment; amend_plan left a measurement to the orchestrator; the plan had measured a cast it did not send.

**Changed**

- **FR-108, `driver.py`.** `counted_from` gives the head and the files as they stood when the run came to the
  step: the `step_start` event now records both, and an attempt that follows a failed attempt of the same step, at the
  same head, takes the earlier reading. The lead answering in between does not break the row. `_failure` shows an
  answered question as nothing, since the answer is already given with the questions.
- **`prompts/amend_plan.md`, `build.md`, `mend_tests.md`.** A finding about how the database or a tool behaves is
  asked for as a measurement, not left in a comment or to the orchestrator.
- **`prompts/check_plan.md`.** A measured answer that measured another statement than the plan sends is a finding.

**Not changed:** `factory resume` still puts back what a stopped agent left (a resume moves the head, so the next
attempt counts afresh). Letting `abandon` end a needs-me run, and letting resume keep work, are left for later.

Tests: in `tests/test_questions.py`, four new tests (FR-108); the three of the driver failed before the change.
