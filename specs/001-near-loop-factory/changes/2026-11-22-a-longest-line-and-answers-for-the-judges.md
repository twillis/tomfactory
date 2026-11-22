# Change record: a longest line measured by code, and the planner's answers given to the judges (2026-11-22)

Made outside spec kit, for spec kit to review later.

**Found on bttr_erp's run 60** (the repo layer serves a period fact), the largest run of the day at
38 minutes and $16.60. Two of its rounds were the factory's doing, not the work's.

- The planner asked for a measurement, and the answer corrected a fact in the request. The plan check
  was shown the request and the plan, not the answer, so it reported the corrected plan as
  contradicting the request, and a revision was spent telling the planner to copy the facts into the
  plan so the next check could see them. The retro: "check_plan never saw the orchestrator's
  measurements. So its first finding was wrong."
- The request asked for docstrings wrapped at 100 columns. Nothing measured it. The final review
  found five lines over and sent the finished build back through build, test, architect, documenter
  and review: "The 100-column limit cost a whole rework pass: $4.32 and 5.5 minutes."

The operator, 2026-11-22: "yeah do the factory fixes and then continue on erp".

**Changed**

- **FR-102, `driver.py`, `tables.py`.** A new input, `planning_answers`: every question asked in the
  run that has its answer, with who asked, at which step, and who answered. `check_plan` and
  `converge` are given it. `prompts/check_plan.md` and `prompts/converge.md` say an answer is
  established, that where the request and an answer disagree the answer stands, and not to report a
  plan for following the answer. The builder and the test writer are not given it: the plan carries
  what they need.
- **FR-101, `config.py`, `workspace.py`, `checks.py`, `tables.py`.** A target setting, `line_length`
  (0, the default, is no limit). A check, `lines_within_length`, on the steps that write code or
  tests (`write_tests`, `build`, `mend_tests`): `Workspace.long_lines_added` reads the lines the step
  added from a zero-context diff, or the whole of a new file, and the check names each one over the
  limit as `file:line (length)`. The work goes back to the step that wrote it, before the tests are
  run. Lines already there are not measured, nor is anything under the documentation paths. The
  build step gains `on_fail=Rework("build")`, since it now has a check of its own.
- `README.md` and `spec.md` say so.

**Not taken from run 60's retro, and why**

- *Tell a second review pass it is a second pass, and give it the diff since the last.* Real: the
  architect re-derived findings it had already written and left a stale backlog entry. With the
  line length measured before the tests, the rework pass that exposed it should be rarer; left until
  it costs again.
- *One persona alone amends existing backlog entries.* A prompt change for the architect and the
  documenter; small, and not what cost this run.
- *The plan check tests each ruling of a request against the constitution's rule that covers it.* It
  would have caught the request's conflict with B3 before the build. Worth doing; it wants the
  constitution's rules indexed by subject, which is the target's document, not the factory's.

Tests: `tests/test_cycle.py::test_a_line_longer_than_the_codebase_allows_is_sent_back_naming_it`,
`::test_no_line_length_is_asked_of_a_codebase_that_sets_none` (FR-101), and
`tests/test_sprint_cycle.py::test_what_was_asked_and_answered_in_planning_reaches_the_plan_check_and_the_final_review`,
`::test_the_judges_are_told_a_measured_answer_outranks_the_request` (FR-102). All but the second
failed before the change; the second pins that the default asks nothing. The whole suite: see the
count in `README.md`.
