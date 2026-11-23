# Change record: four model grades, and a retry climbs (2026-11-23)

Made outside spec kit, for spec kit to review later.

**Asked for by the operator.** Shown a post that splits work across models ("Haiku searches. Sonnet builds. Opus
reviews."): "Sounds like we should setup something like this in the factory". Then: "On failure tries bump up the
model", and "we could measure starting next sprint 83. If we see failure we can bail."

**The record:** bttr_erp's runs 80 and 81 cost $14.16 together, every step passing on its first attempt; the
architect and the final review, on the strongest model, were $4.38 of it.

**Changed (wave 1)**

- **FR-109, `workflow.py`.** `GRADES` is light, middle, standard, strongest; `grade_for(step, tries)` climbs one grade
  per earlier counted attempt, up to `CLIMBS_TO` (standard), never past it unless the step starts higher.
- **`agent.py`.** `MODELS` names Haiku, Sonnet, Opus and Fable for the four grades.
- **`driver.py`.** Each attempt runs on `grade_for` its counted attempts; the `step_start` event records the model.
- **`tables.py`.** The architect, the review and converge move from strongest to standard; the documenter, the retro
  and the lead start on light.
- **`run_record.py`.** The time-and-cost table gains a Model column.
- FR-088 amended; README "Which model each step uses" rewritten.

**Not changed:** build and write_tests stay on standard (wave 2, if wave 1's runs hold). Search handed to a
sub-agent inside a step (wave 3) is not built.

**How to bail:** set a step's `model=` back in `tables.py`, or `CLIMBS_TO`; the record shows which attempts ran on
which model.

Tests: `tests/test_model_grades.py` (new, FR-109; 12 of its 13 cases failed before the change); FR-088's test in
`tests/test_step_shape.py` and the retro's grade in `tests/test_retro.py` amended.
