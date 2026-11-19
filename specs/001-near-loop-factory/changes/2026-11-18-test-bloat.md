# Change record: test bloat, a test budget, and tidy runs (2026-11-18)

Made outside spec kit with the operator's agreement, for spec kit to review later.

## What happened

Building the viewer through the factory, the tests grew far faster than the code. After
four accepted features the viewer was 634 lines of code and 6,625 lines of tests: 535 test
functions, 109 of them starting a server, the same rules asserted at three levels (data,
rendering, HTTP), and fourteen helpers that build a database. The suite took 77 seconds.
Because every agent reads the tests, a run went from about 3.5 minutes and $2 to 20
minutes and $11.

The architect flagged the duplication in three successive reviews. Nothing acted on it.

## Why

The factory caused it. The test writer was told to list edge and failure cases and cover
them, stating edge cases was made compulsory (FR-045), and nothing said when to stop.

## What changed (FR-065, FR-066)

- **A budget.** `test_budget_lines` in a target's `.factory.toml`, 300 by default, 0 for no
  limit. A new check on the `write_tests` step, `tests_within_budget`, counts the lines the
  step added under the test paths and sends the step back, with the numbers, if it is over.
- **Guidance.** The test-writer persona and the `write_tests` prompt now say: test each
  behaviour once, at the level where it lives; one outer test to show the layers are joined
  up; parametrise variations; reuse helpers; choose cases that could really happen and
  would really matter.
- **Tidy runs.** `factory request … --tidy tests` or `--tidy code`. A kind of run with no
  failing-tests-first step: the tests must pass before and after, and one side is held
  still. Stored as `runs.workflow`; the table is chosen by `workflow.table_for(spec_kit, kind)`.
- A store made before a column existed now gains it on opening (`ADDED_SINCE` in `store.py`).

## What is not settled

- The budget is a blunt instrument: lines, not usefulness. A large feature may need the
  operator to raise it.
- A tidy run that trims tests relies on the reviewer to judge that nothing important was
  lost. There is no coverage measurement.
- The architect's findings still only reach a backlog. The bloat shows what that costs.
