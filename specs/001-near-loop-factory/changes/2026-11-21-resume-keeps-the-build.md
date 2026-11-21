# Change record: resuming after failed tests keeps what the build wrote (2026-11-21)

Made outside spec kit, for spec kit to review later.

**Found on bttr_erp's run 43** (run 3b, first step). The build was right and one new test was wrong:
its seed left out the user it acted as. The builder may not change tests, said so on its second and
third attempts, and the run ended needs-me at the test step. On the operator's word ("Fix and
resume") the orchestrator mended the test, committed it in the run's checkout and resumed. `resume`
began by undoing everything uncommitted, which was the build's whole work, because a failed test
step never commits. The tests failed again, the build had no attempts left, and the run ended
needs-me a second time. The work was restored from a copy the orchestrator had taken first.

**Changed**

- **FR-067, `operations.resume`.** It undoes the checkout only when the step that stopped is an
  agent's, whose half-done files are what the undo is for. A code step writes nothing of its own:
  what is uncommitted when one stops is the work it was checking, and it is kept for the resumed step
  to check again.
- `README.md` says so under "A run, start to finish".

**Not changed, and owed.** The retro of run 43 asks for the larger fix: a builder that reports a
defective test should be able to send the work back to the test writer once, instead of spending its
attempts. That is a new route in the tables and a new key in the builder's reply, and it waits for
the operator's word. Until then the way through is the one above: mend the test by hand, commit,
resume.

Tests: `tests/test_cycle.py::test_resuming_after_failed_tests_keeps_what_the_build_wrote` (FR-067),
which failed before the change. The whole suite: 388 passed.
