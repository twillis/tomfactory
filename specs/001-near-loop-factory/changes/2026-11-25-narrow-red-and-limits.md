# Change record: red runs the run's own tests; the writers know the limits up front (2026-11-25)

Made outside spec kit, for spec kit to review later. Built as FR-152 and FR-153.

**Asked for by bttr_erp's retros of runs 100 and 101, agreed by the operator.** Baseline, red and the test step after
the build each ran the whole suite, about five and a half minutes each on bttr_erp. Red's job is only to show the run's
new tests fail before the build. And the writers met the line length and the test budget only as smells, after they
had written (theme #71).

**How red judged before, and still does.** `tests_fail_first` passes when the test command exits non-zero and not with
`no_tests_exit_code`. It never judged each new test: one failing test anywhere is red, a new case that already passes
beside it is not noticed. That is kept exactly. What changes is only which run decides it, where a codebase says how
to run a subset.

**Changed**

1. **`factory/config.py`**: the setting `red_command` ("" by default: the whole suite as before), and `red_argv`,
   which replaces the word `{paths}` with the run's test files, one word each, as `probe_argv` does `{path}`. A red
   command without `{paths}` as a word, or without a `test_report`, is refused when the settings are read.
2. **`factory/checks.py`**: `tests_fail_first`, after the readability check (unchanged, FR-089), runs the codebase's
   red command on the run's test files first (`_run_alone`). That settles red only when it exits failing and its test
   report names a failing test, or when it timed out; anything else (the files pass, nothing collected, an exit with no
   failing test named, no test file left to run) goes to the whole suite, judged as before. `_judged_red` is the
   judgement, now named once for both runs. `_tests_judged` takes the command to run. `run_test_files`: the files under
   the test paths the run added or changed since it started and has not deleted.
3. **`factory/driver.py`**: the input `limits` (FR-153): the codebase's `line_length` and `test_budget_lines`, or that
   it sets none, and that they are measured after and never send work back. `test_files` now uses `run_test_files`,
   so the builder is no longer listed a test file the run deleted. An unused import removed.
4. **`factory/tables.py`**: `limits` among the inputs of `write_tests`, `build`, `mend_tests`, `tidy_tests` and
   `tidy_code`. Their smells are unchanged.
5. **`prompts/write_tests.md`, `build.md`, `mend_tests.md`, `tidy_tests.md`, `tidy_code.md`**: a section showing
   `{{limits}}`. The builder and code tidy are told the budget is the test writer's; the test tidy, that the budget
   does not apply to it (as its prompt already said) and the longest line does.
6. **`README.md`**: the run table's `red` row; a section, "Red runs the run's own tests, if the codebase says how";
   the budget and line-length sections say the writers are told up front; `limits` among the inputs.
7. **`specs/001-near-loop-factory/spec.md`**: FR-152 and FR-153.
8. **`specs/001-near-loop-factory/contracts/workflow.md`**: `tests_fail_first`'s row, the `limits` input, and the
   inputs of `write_tests`, `build` and `mend_tests`.
9. **`docs/suggestions.md`**: the two asks in the runs 99 to 101 entry marked taken.
10. **`tests/test_narrow_red.py`**: the tests for FR-152 and FR-153, written first: 14 of the 16 failed before the
    code (the two that passed guard what must not change: red without the setting, and the limits staying smells).

**Decided in the build, for the operator to confirm**

- **The test report settles a narrowed red, not the exit code alone.** Pytest given a file it cannot collect (a
  fixture's JSON the test writer added) exits 4 having run nothing, so a red command judged by its exit code would call
  passing tests red. Requiring a `test_report` costs bttr_erp nothing (it names one) and keeps the factory
  language-neutral: JUnit XML is what it already reads (FR-141).
- **A narrowed run that does not show a failing test is confirmed by the whole suite**, not taken as the answer. So a
  helper the run changed that breaks another test still counts as red, as before; the cost, the narrowed run plus the
  whole suite, falls only on the path that was going back to the test writer anyway.
- **"The run's tests" are files, not cases.** An edited file runs whole: its old cases run beside the new ones, which
  is what the whole suite did too.
- **One known difference**: a new test that fails alone but passes in the whole suite (one that depends on another
  file's test running first) is red now and was not before. Tests that depend on order are a defect in themselves.
- **The narrowed run's coverage report, if the red command writes one, is on red's record** as the whole suite's
  was; the record's "before" is the baseline's, the first measured, so nothing reads it. A red command without
  coverage is quicker.
- **One input, `limits`, carries both numbers to every writer.** The builder and the code tidy are told the budget
  is not theirs, rather than the input being made different for each step.

**Measured on bttr_erp** (a scratch clone, uncontained, at each run's `Tests:` commit, before its build): the whole
suite with its coverage, as red ran it, 335 seconds (run 101: 23 failed, 2,737 passed). The run's own files alone,
without coverage: run 101 (one file) 7 seconds; run 100 (two files) 20 seconds; the eleven files of commit ad48a14, `conftest.py`
among them, 86 seconds. Each failed with its new tests named in the report, so each would have settled red.

The suite: 760 passed before, 776 after (16 new, counting each parametrised case), with the one warning as before: the
factory's own figures.
