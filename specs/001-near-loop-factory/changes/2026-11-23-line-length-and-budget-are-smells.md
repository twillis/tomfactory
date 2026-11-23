# Change record: the line length and the test budget are smells (2026-11-23)

Made outside spec kit, for spec kit to review later.

**Asked for by the operator.** The operator, 2026-11-23: "Maybe docstring limits should be smells that don't stop the build from now on. I'm beginning to think the same about the test lines count budget." And: "By build I mean run".

**The record, across bttr_erp's runs:** the line check sent work back seven times, plus once on a plan, which ended
run 68 as needs-me for a one-line wrap; run 77's build used all three attempts on it. The test budget never sent
anything back. The two tidy steps were not measured, so run 78's 147-character docstring line reached the final
review, which rejected it because the orchestrator's request had said "keep to the line length of 120".

**Changed**

- **FR-107, `workflow.py`, `driver.py`.** A step entry may name `smells=`, checks run after its own checks pass. Each
  result is kept with the step marked `smell`, and never fails it. `validate` refuses a smell that is not registered.
- **`tables.py`.** `lines_within_length` (write_tests, build, mend_tests, and now tidy_tests and tidy_code),
  `plan_lines_within_length` (plan, amend_plan) and `tests_within_budget` (write_tests, mend_tests) move from
  `checks=` to `smells=`.
- **`checks.py`.** The three notes no longer tell an agent what to do, since an agent is no longer sent them.
- **`run_record.py`.** A "Smells" section lists what each smell found, or "none".
- **`prompts/review.md`, `converge.md`.** A smell is not a reason to reject, nor unbuilt work, even where a request
  asks for it. **`prompts/write_tests.md`**: the budget is measured and reported, no longer "enforced".
- FR-065, FR-101 and FR-104's line-length clause now report in place of sending back; `README.md` says so.

**Not changed:** the test writer's persona still names the budget, as guidance. The orchestrator stops writing "keep
to the line length" in requests (playbook, below).

Tests: in `tests/test_cycle.py`, the three tests of the old send-backs now show the run goes on and the smell is
reported (FR-101, FR-104, FR-065); `test_a_tidys_long_line_is_a_smell_too` and
`test_the_judges_are_told_a_smell_is_no_reason_to_reject` are new (FR-107), and all five failed before the change.
`test_each_send_back_gives_the_planner_its_attempts_again` (FR-105) burns its attempts with a reply that has no plan,
in place of a long plan. `test_show_returns_the_whole_run_as_typed_records` expects the check record's new `smell`
key. The suite: 435 tests, run as two groups of files (the whole-suite run is refused by spec 003's untested
requirements, as before).
