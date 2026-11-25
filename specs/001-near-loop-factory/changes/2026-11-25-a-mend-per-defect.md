# Change record: a mend for each defect the builder finds in the tests (2026-11-25)

Made outside spec kit, for spec kit to review later. Built as FR-150, amending FR-097.

**Asked for by the orchestrator, from bttr_erp's run 99; the operator: "exactly".** The builder may report
`test_defect`, naming tests it believes no build can pass, and the test writer gets one mend (`mend_tests`). On run
99 the first report (a statement-counting test) was mended correctly. The builder then found a second, different
defect: two cases that read under DateStyle 'SQL, DMY', which psycopg cannot parse. It diagnosed it exactly, twice,
but the route was `Rework("mend_tests", at_most=1, then="test")`: the one mend was spent, the report was ignored, the
build's attempts ran out and the run ended needs-me. Wanted: a report that names tests not already reported in the
run gets a mend of its own; a repeat report naming only tests already reported is not chased (the old rule's reason:
no going back and forth); and a cap, so a run cannot mend for ever.

**How the builder named the tests before.** Only in `reasons`, free text ("each such test: its name, what it expects,
and what the plan or the codebase says instead"). The factory could not compare two reports from that, so the reply
gains a list of the tests' ids.

**Changed**

1. **`factory/workflow.py`**: `DEFECTIVE_TESTS`, the reply's key for the tests reported. `StepResult.named`, the
   tests a verdict names. `Rework.once_per_test`: such a route is taken only for a report naming a test no earlier
   report named; a report naming none only if it is the first (as before FR-150). `next_step` takes `reports`, the
   tests each earlier report named, and decides through `_taken`, which also holds the existing `at_most` rule.
   `comparable_name` reads a runner's `tests/test_x.py::TestY::test_z` and a JUnit report's
   `tests.test_x.TestY::test_z` as one test, keeping a parametrised case's bracketed id whole. Still pure: no new
   import (the purity test allows `dataclasses` and `pathlib` only, so the split is done with `str` methods, not `re`).
2. **`factory/tables.py`**: the build's route is `Rework("mend_tests", at_most=2, then="test", once_per_test=True)`
   and its envelope requires `defective_tests` (a list, empty unless the verdict is `test_defect`); `mend_tests` is
   given two new inputs, `defective_tests` and `failing_tests`. Every table reuses the plain build and mend, so spec
   kit's and the sprint's change with it.
3. **`factory/records.py`**: `defect_reports`, the tests each report named in the run, oldest first, since the
   operator last sent the work back (as the attempt counts are). A report is a reply naming `defective_tests` whose
   verdict sent the run on its route (`failure == "check"`); a reply refused for its shape or a guard was never acted
   on, so it is not one.
4. **`factory/driver.py`**: `advance` passes `next_step` the earlier reports (all but the reply just recorded);
   `verify` sets `named` beside `verdict`. Two inputs: `defective_tests` (this report's tests, and each earlier
   report's) and `failing_tests` (what the latest test run's report named as failing, each with its message, FR-141,
   or that there is no report to read).
5. **`factory/checks.py`**: `TEST_RUNS`, the three checks that run the codebase's tests, so `failing_tests` reads the
   latest of them and never a stale report from an earlier run.
6. **`prompts/build.md`**: the builder names each defective test in `defective_tests`, as the test report names it
   (or as the runner would), and is told each test is mended once, so to report a new one as soon as it finds it.
7. **`prompts/mend_tests.md`**: "The tests it names" and "What the tests last reported", beside the builder's report.
8. **`README.md`**: the `test_defect` paragraph says a mend per defect, the repeat rule and why, the two-mend cap and
   how a codebase raises it; the resume paragraph no longer speaks of "one chance"; the two new inputs are listed
   among the inputs a prompt can use.
9. **`specs/001-near-loop-factory/spec.md`**: FR-097's "second report" sentence now says a report naming only tests
   reported before; FR-150 added.
10. **`specs/001-near-loop-factory/contracts/workflow.md`**: the build's route, the mend's inputs, the build's
    envelope and what `Rework`'s `at_most` and `once_per_test` mean.
11. **`docs/suggestions.md`**: the run-99 entry marked taken.
12. **`tests/test_mend_per_defect.py`**: the tests for FR-150, written first and seen to fail (17 of them): the
    table's route and inputs; nine cases of the rule over `next_step`; five of `comparable_name`; a whole run with two
    different defects each mended, the second mend told the report's failing test and message and the earlier
    report's test; and a run with no test report, whose mend is told there was none.
13. **`tests/conftest.py`, `tests/test_cycle.py`, `tests/test_workflow.py`**: the scripted build replies carry
    `defective_tests`; FR-097's repeat test names its test, and is marked FR-150 too; the roles test no longer
    restates the route's arguments, which FR-150's test owns.

**Decided in the build, for the operator to confirm**

- **The cap is two mends in a run** (`at_most=2`, counted as runs of `mend_tests`, as `at_most` always is). One more
  than before, which is what run 99 needed. Each mend follows a build attempt that reported it, and the build has three
  attempts by default, so a third different defect would come on its last attempt; three different broken tests in
  one run's tests say the tests, not the build, need the operator's eye. A mend that had to be asked again (its reply
  malformed) uses up a run of `mend_tests`, so it can leave one mend, not two. A codebase may raise the cap with
  `rework_at_most` on `[steps.build]` (FR-112), which already applied to this route.
- **"Already mended" is "named by an earlier report".** A report the factory did not chase named either only tests
  reported before, or came after the cap, so counting every earlier report gives the same answer as counting only the
  mended ones, without the factory having to work out which records a mend followed.
- **A report naming no test is mended only if it is the first**, which is FR-097's behaviour; the prompt asks for the
  names, but a builder that leaves them out is not stranded.
- **Names are compared loosely, not exactly**: the builder names a test from reading it before any test report
  exists, and later copies the report's spelling, so `tests/test_x.py::test_z` and `tests.test_x::test_z` must match.
  A file named without a test is a different name from a test in it.

The suite: 738 passed before, 755 after (17 new, counting each parametrised case), with the one warning as before: the
factory's own figures.
