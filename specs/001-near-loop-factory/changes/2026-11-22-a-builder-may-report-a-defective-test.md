# Change record: a builder may report a defective test, and what runs 53 to 56 taught the prompts (2026-11-22)

Made outside spec kit, for spec kit to review later.

**Found on bttr_erp's runs 43 and 56, and in the retros of runs 53 to 56.** Twice the build was right
and one new test was wrong: a seed that left out the user the test acted as (run 43), and a migration
file expected as `0002` where the test's own starting declaration already wrote `0001` and `0002`
(run 56). The builder may not change a test. Each time it said so on its second attempt, was sent to
build again anyway, and the run ended needs-me for a one-line fix the orchestrator made by hand.
This is the route the record of 2026-11-21 ("resuming after failed tests keeps what the build
wrote") left owed. The operator, 2026-11-22, asked whether to mend the factory before the next
capability: "A".

**Changed**

- **FR-097, `tables.py`.** The build's reply gains `verdict` and `reasons`. `accept` goes on to the
  tests as before. `test_defect` is a route to a new step, `mend_tests`: the test writer, told what
  the builder found, may change tests only, and may change nothing if the builder is wrong. It goes
  on to `test`, not `red`: the build exists, so a mended test is expected to pass, and requiring it
  to fail first would send it round for ever. The route is taken once in a run
  (`Rework("mend_tests", at_most=1, then="test")`); a second report runs the tests, and their
  failure sends the work back to the build until its attempts are used, as before. `mend_tests` is
  in the plain, spec kit and sprint tables. No code outside the table changed: the verdict, the
  route and the bound were already there for the judging steps.
- **`workflow.py`.** Two comments say a step that gives a verdict need not be a judge. The rule that
  a judge reads and changes nothing, and gets the strongest model, is unchanged; the tests that state
  it now name the build as the one step with a verdict that judges nothing.
- **`prompts/build.md`, `prompts/mend_tests.md`.** The builder is told what a defective test is, and
  that a test merely hard to satisfy is not one. The test writer is told to make the smallest
  correction, to be guided by the plan and the code and not the builder's convenience, and not to
  weaken a test.
- **FR-098, `prompts/check_plan.md`.** Four more things to look for: an expected value worked out
  from that test's own setup and not vouched for by another row; a string that will be read as a
  regular expression; a rule stated for a whole family on the evidence of one case; a refusal's
  remedy followed to where it leads.
- **FR-098, `prompts/write_tests.md`.** The test writer is told it cannot run the tests, that the
  next step does, and to check by reading that what a test imports and its setup relies on exists.
- `README.md`, `contracts/workflow.md` and `spec.md` say so.

- **FR-099, the smaller debts, taken the same day** when the operator said "it might be worth paying
  down some of the technical debt in the factory now before moving back to the erp":
  - `workspace.diff_since_base(leaving_out=)` and the `diff` input: the diff given to the architect,
    the documenter and the final review leaves out the run's own record, which repeats the request
    and the plan they are already given. Reported by the retros of runs 52, 53 and 55.
  - The retro is given the constitution and the ideals (`tables.py`, `prompts/retro.md`), so it can
    say which rule a run missed. Owed since run 51.
  - The planner and the plan check are given the test and documentation paths and told who writes
    what after approval (`prompts/plan.md`, `prompts/check_plan.md`). Plans had given the documenter
    a row in `requirements/` (run 52) and a `CHANGELOG.md` that did not exist (run 53). This also
    closes "tell the planner what the factory adds" in `docs/next.md`.
  - The architect moves an answered backlog entry to `docs/backlog-done.md` and keeps entries short
    (`prompts/architecture_review.md`). bttr_erp's backlog had passed two hundred long entries.

**What holds it.** "Agents propose; code disposes" is unchanged: whether the mended tests pass is
found by running them, and that the test writer touched tests only, and the builder none, is found
from git. What is new is that an agent's report now chooses a route. The risk is a builder that
blames a sound test and a test writer that gives way. Against it: once per run; the test writer is
asked to judge, not to comply; the change to the test is in the run's diff, which the final review
reads; and the record shows the `mend_tests` step with what it was told and what it did.

**Not taken from the retros, and why**

- *Give the plan, the plan check and the test writer a shell or a scratch database.* It would have
  caught most of what these runs found. It is also the largest change to containment since
  bubblewrap, since today no agent runs anything; it wants a decision of its own.
- *A step after the plan check that applies accepted findings without a whole new plan and check.*
  Asked for by three retros. A real saving, about a third of a send-back, and a new step in the
  planning stage; not built here so this change stays one thing.
- *Give converge the plan as amended by a hand fix.* The plan is what the operator approved; a hand
  fix is on the branch as its own commit and in the run's record, and the final review reads both.
- *Stop at once, as needs-me, when the builder reports a defect.* The alternative considered to the
  route. It is safer, and it still needs a person for a one-line fix, which is what the two runs
  cost. The route was chosen because the test writer's change is checked by running the tests and
  is seen by the final review.

Tests: `tests/test_cycle.py::test_a_builder_that_reports_a_test_no_build_can_pass_sends_it_to_the_test_writer_once`,
`::test_a_second_report_of_a_defective_test_is_not_chased`,
`::test_the_test_writer_mending_a_test_may_not_touch_the_code` (FR-097), and
`tests/test_sprint_cycle.py::test_the_prompts_carry_what_bttr_erps_runs_53_to_56_taught` (FR-098), and
the three FR-099 tests at the end of `tests/test_sprint_cycle.py`, all of which failed before the change. `tests/test_workflow.py::test_the_roles_are_kept_apart` now states
the build's route. The whole suite: see the count in `README.md`.
