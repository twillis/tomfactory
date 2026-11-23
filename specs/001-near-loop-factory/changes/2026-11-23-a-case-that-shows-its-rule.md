# Change record: a planned case must be able to show its rule, and is never dropped (2026-11-23)

Made outside spec kit, for spec kit to review later.

**Found on bttr_erp's run 69** (run 6's first step, traversal). The plan listed a case,
`/parent/<P1>/child/<Q's key>`, meant to show that another tenant's row in a row's position is not found. Q is
a parent, so the case was not found whatever the scope did. The plan check passed it; the test writer saw the
fault and dropped the case, so the only test of its kind was lost and could only be raised at merge (the
orchestrator measured the intended case by hand: not found, nothing changed). The same run reworded "holds
tenants' rows" in one package and left it in another, because the check read only the files the plan touched.
The operator, 2026-11-23, on the retro's points: "3 factory fixes".

**Changed**

- **FR-106, `prompts/check_plan.md`.** Two lessons: a planned case that would still pass with the rule it names
  broken, worked out from where each of its values comes from; and a reworded phrase searched for across the
  whole package.
- **FR-106, `prompts/write_tests.md`.** Never drop a case the plan lists: write it so it shows its rule where
  the intent is plain, otherwise as planned, and say which in `summary`.
- `spec.md` says so; `README.md` gives the new test count.

**Not taken from the retro: letting a step edit the run-order rows a plan names.** The run order holds the
operator's rulings, quoted, and the orchestrator records them at merge after checking each attribution
(the playbook's "Recording his rulings"); an agent writing there is how a ruling once came to be filed under
his name. The rewording takes the orchestrator a minute at merge. The operator was told and may overrule.

Tests: `tests/test_sprint_cycle.py::test_the_prompts_carry_what_run_69_taught`, three cases, each of which
failed before the change. The whole suite: see the count in `README.md`.
