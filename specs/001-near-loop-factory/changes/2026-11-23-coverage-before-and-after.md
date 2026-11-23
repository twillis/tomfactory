# Change record: coverage before and after each run, and a smell when it falls (2026-11-23)

Made outside spec kit, for spec kit to review later.

**Asked for by the operator.** "Maybe running the coverage report on merge and including it in the commit msg. Seems
simple so cheap model/token wise. Then woukd want a to warning threshold for if it dips below x%". On the proposal
(the factory measures at its baseline and after the build; a smell below a floor of 90% or on a drop of more than 1
point): "Sounds good". bttr_erp was at 95% (branches counted) after run 80.

**Changed**

- **FR-110, `config.py`.** `coverage_report`, `coverage_floor`, `coverage_drop`; none set, nothing is measured.
- **`workflow.py`.** `CheckResult.measured`: what a test run measured beside passing.
- **`checks.py`.** `_tests_judged` removes a stale report before the tests and reads the new one after
  (`_coverage`); `coverage_holds`, a smell, compares the first coverage the run measured with the current one.
  `CheckContext.store` lets a smell read the run's earlier steps.
- **`tables.py`.** The test step names `coverage_holds` among its smells.
- **`run_record.py`.** A "Coverage" section, and a coverage line in the last commit's body (`coverage_line`).
- **`driver.py`.** The store is given to the checks.

No model reads or writes any of it: the test command measures, and code compares.

Tests: `tests/test_coverage.py` (new, FR-110; all six failed before the change); the check key set in
`tests/test_operations.py` gains `measured`.
