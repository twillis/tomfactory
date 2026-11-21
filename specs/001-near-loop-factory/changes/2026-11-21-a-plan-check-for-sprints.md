# Change record: a plan check before the sprint's one approval (2026-11-21)

Agreed by the operator ("yeah a plan check should happen for future sprints"), for spec kit to review
later. Built 2026-11-21 after run 28 ended, tests first: FR-095, with the red and green output written into every record by the factory and two duties added to the plan prompt.

**Why.** Of spec kit's stages, the one that earned its keep was `analyze`: before any code was written
it found the raw-text tenant leak and the subquery gap in run 23, the error kinds contradicting D13,
and run 27's extra read. The sprint cycle (FR-093) has no check before the build. Run 28, the first
sprint without spec kit, planned in one step for $3.25 and 9.6 minutes, and its plan reached the
operator checked only by claude-dev reading it.

**To build**

- A step after `plan` in `SPRINT_STEPS`, on the standard model and the reviewer persona, that changes
  nothing and is not a gate. It reads the plan against the request, `requirements/`, the constitution,
  the binding decisions and `knowledge/`, and lists what it finds: contradictions, a requirement or
  ruling the plan misses, a test expectation the plan's own design would not meet (run 27's failure),
  and anything that cannot pass as planned.
- Its findings are shown with the plan when the operator is asked to approve. The approval stays the
  one wait. Sending it back returns to `plan`, as now.
- It must not re-raise what the operator has ruled out of scope (guards against a module author's own
  code), and it says "nothing found" when there is nothing.

**From** the sprint after run 28.

**Fixed the same day, on its first use (run 29).** The check was handed "(none)" for the plan: the
`plan` input read only plans already shown to the operator, and none had been. It now reads the
planner's own reply until a plan is approved. The tests had used a fake check that ignored its input;
`test_the_plan_check_is_shown_the_plan_it_checks` now asserts the plan is in the check's prompt. Run 29
was abandoned at the operator's word and run again.
