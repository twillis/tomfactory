# Change record: the planner amends its plan from the check, and smaller lessons of runs 58 to 63 (2026-11-22)

Made outside spec kit, for spec kit to review later.

**Found on bttr_erp's runs 58 to 63.** On nearly every run the plan check passed with findings and the
orchestrator sent the plan back by hand, most often with "take the plan check's findings as written;
nothing else changes", and the whole plan and check ran again. Run 63's retro: "a check that has findings
should end as 'check' and go back to the planner automatically. A 'passed' outcome that the operator must
then send back costs him a round trip." Three earlier retros asked for the same in other words. The
operator, 2026-11-22, after run 63: "Merge, push and then factory batch and then erp tech debt".

**Changed**

- **FR-104, `tables.py`, `checks.py`, `driver.py`.** `check_plan` gives a verdict: `accept` when it found
  nothing, `amend` when it found something, which routes to a new step, `amend_plan`. The planner is given
  its plan and the findings (a new input, `plan_findings`), takes each finding that is right and declines,
  with its reason, each that is not, and the run waits. The operator is shown the amended plan, the
  findings, what was taken and what was declined, and still approves or sends it back; sending it back
  returns to `plan`. The amendment is not checked again: a second check is what the old round trip cost.
  The plan check's verdict joins the existing route machinery; `verdict`'s note now includes `findings`.
  `check_plan` keeps the standard model: like the build's verdict, it routes work, and judges none.
- **FR-104, `checks.py`.** `plan_lines_within_length`, on `plan` and `amend_plan`: a plan whose fenced code
  has a line over the codebase's `line_length` is written again before it is checked. The builder copies a
  plan's code; run 61's plan carried a 137-column line that its check had to find by eye.
- **FR-104, `prompts/check_plan.md`.** Three more things to look for: what makes each planned test fail
  before the build (run 62 planned two that already passed); what a table missing from a new list does, and
  whether that is silent (run 62's `WRITABLE_USER_COLUMNS` had no fallback); whether every module docstring
  and comment of a changed file stays true (run 58).
- **FR-104, `run_record.py`, `prompts/document.md`.** The run's record keeps the documenter's account, under
  "What changed", from its summary; the documenter is told docs/runs/ is the factory's. Run 62's account was
  overwritten when the record was rewritten. The "How it went" table says which check sent a step back
  (`check: tests_pass`), where it said only `check`.
- **FR-103, `run_record.py`.** A commit after a step sent back is named by what the step first did: run 63's
  build commit was labelled with its second attempt's summary, "Rewrapped the over-long docstring line".
- **`orchestrator/playbook.md`.** The request-writing lessons of runs 58 to 63.
- `README.md` and `spec.md` say so.

**Not taken, and why**

- *A shell or database for an agent.* Still a change to containment; the measurement route has carried it.
- *A mechanical check that each parametrised case has its id on its own row.* That is one codebase's
  convention, not the factory's; the plan check is told, which has worked.
- *One persona alone amends backlog entries; a second review pass told it is a second pass.* Small, and not
  what cost these runs.

Tests: `tests/test_sprint_cycle.py::test_a_finding_the_planner_declines_is_shown_with_its_reason`,
`::test_the_prompts_carry_what_runs_58_to_63_taught`, and the changed
`::test_a_sprints_plan_is_checked_before_the_one_approval_and_the_check_is_not_a_gate`,
`::test_what_the_operator_approves_is_the_planners_plan_with_the_checks_findings` and
`::test_the_sprint_waits_once_and_ends_with_the_sprint_review_and_the_retro` (FR-104);
`tests/test_cycle.py::test_a_plan_whose_code_is_longer_than_the_codebase_allows_is_written_again` (FR-104) and
`::test_a_build_sent_back_is_named_by_what_it_built_and_the_record_says_why` (FR-103, FR-104). All failed
before the change. The whole suite: see the count in `README.md`.
