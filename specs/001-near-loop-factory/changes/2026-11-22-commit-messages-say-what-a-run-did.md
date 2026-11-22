# Change record: a run's commits say what they hold (2026-11-22)

Made outside spec kit, for spec kit to review later.

**The operator, 2026-11-22:** "some feedback on the factory, the commit messages suck, :) should be a
summary of the run", and, asked which: "meaning the commits it produces as part of a run". Until then a
run's branch read `factory: approved plan (run 62)`, `factory: red (run 62)`, `factory: test (run 62)`,
`factory: architecture_review (run 62)` and so on: the step's name, which says nothing about the change.

**Changed**

- **FR-103, `run_record.py`.** One place writes every message a run's commit carries:
  `step_message`, `approved_message`, `resumed_message` and `ended_message`, with `title` (the approved
  plan's heading or first line, else the request's) and `_shorten` (one line, cut at a word to 72
  characters, with an ellipsis). The subject says what the commit holds, in the words of the agent
  that wrote it: `Plan: <title>`, `Tests: <the test writer's summary>` at `red`, `Build: <the
  builder's summary>` at `test`, `Backlog:`, `Docs:`, `Retro:`, and `Accepted: <title>` (or `Rejected:`, `Needs me:`) for the
  finished record. The record's body gives the outcome's reason, the review's verdict and reasons, and
  the time and cost. Every body names the run and the request's first line, and ends with the
  trailers `Factory-Run:` and `Factory-Step:`.
- **`driver.py`, `operations.py`.** The four places that wrote `factory: … (run n)` ask `run_record`.
- `README.md` and `spec.md` say so.

**Not changed.** `factory: set aside`, written by `workspace.py` when a spec kit run returns to
planning, and `factory: new target codebase`, written by `init-target`; neither is a run's work.
Squashing a run into one commit was not done: the commits after `red` and after `test` are how the
factory, and a reader, see the tests before the build and the build alone.

Tests: `tests/test_cycle.py::test_each_commit_says_what_it_holds_and_which_run_made_it` (FR-103), and the
subjects expected by `test_the_happy_path_from_an_empty_target`,
`test_a_run_leaves_its_record_with_the_code_from_approval_to_its_end` and
`tests/test_sprint_cycle.py::test_a_resumed_step_is_told_why_it_stopped_and_the_record_is_written_again`,
all of which failed before the change. The whole suite: see the count in `README.md`.
