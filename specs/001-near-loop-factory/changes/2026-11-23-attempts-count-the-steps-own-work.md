# Change record: a step's attempts count its own work (2026-11-23)

Made outside spec kit, for spec kit to review later.

**Found on bttr_erp's run 68.** The planner asked the orchestrator for a measurement (its first run), wrote
the plan (its second), and the operator sent the plan back to take the tenant table too (its third). That
version had one line of code over the codebase's 120 columns; the plan's own line check sent it back, and
the planner had used its three attempts, so the run ended needs-me for a one-line wrap. A send-back and an
answered question are the operator steering the plan, not the planner failing. The operator, 2026-11-22:
"Merge. And then after the factory fix push both repositories".

**Changed**

- **FR-105, `records.py`.** `attempts_counted(run, step)`: the runs of a step its limit counts. A run before
  the operator's latest send-back does not count, nor a run that asked a question the operator answered. A
  question the lead answered still counts, so a step that only asks still ends needs-me, as before.
- **`driver.py`.** The rules (`workflow.next_step`) are given `attempts_counted` in place of every run of
  the step. `records.attempts`, which numbers each run, is unchanged.
- `README.md` and `spec.md` say so.

Tests: `tests/test_cycle.py::test_each_send_back_gives_the_planner_its_attempts_again` and
`tests/test_questions.py::test_measurements_the_operator_answers_do_not_use_up_a_steps_attempts` (FR-105), both
of which failed before the change; `test_a_step_that_only_ever_asks_ends_needs_me` still holds. The whole
suite: see the count in `README.md`.
