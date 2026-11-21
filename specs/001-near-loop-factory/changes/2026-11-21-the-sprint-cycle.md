# Change record: a sprint cycle without spec kit, and three fixes from the first retro (2026-11-21)

Made outside spec kit with the operator's agreement ("Merge and yes"), for spec kit to review later.

**Why.** On `bttr_erp` the specification already exists (`requirements/system.md`, the run order,
`knowledge/`, and the operator's rulings), and spec kit re-derived one from a paragraph every run.
Over runs 18 to 24 planning was 68% of agent time and 61% of cost, and twice a plan shipped test
expectations that contradicted itself. The operator: "we are bulding an erp, thats not small and
spec kit isnt working for it, what would it work for lol", and after run 27, "another strike for
speckit".

**Changed**

- **FR-093.** `.factory.toml` gains `cycle`, `auto` (as before) or `sprint`. A sprint uses
  `SPRINT_STEPS`: the plain `plan` and one approval, the build, the architect, the documenter, the
  spec kit table's `converge` without its spec kit stage, `retro`, `finish`. Tidy runs are unchanged.
- **FR-094, from run 27's retro.** (1) A step run again after the agent program failed is told the
  cause the program gave (run 27's analyze retry was told only "error" after a usage limit). (2) The
  architect and the final review get `red_output`, the new tests' first run, beside the green one
  (run 27's converge could judge "each test fails for its own reason" only from the test file). (3)
  Resuming a run writes its record again (run 27's later steps read a record frozen at "needs-me").

**Not taken, from the same retro**: asking one question when instructions collide, and the analyze
step's checklist clash, are spec kit's own stages, which a sprint does not run.

Tests: `tests/test_sprint_cycle.py`.
