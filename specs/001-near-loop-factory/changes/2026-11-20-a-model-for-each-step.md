# Change record: a model for each step (2026-11-20)

Made outside spec kit with the operator's agreement, for spec kit to review later.

**Found during run 18**, the first run on `bttr_erp`. The operator: "I hope the factory is not running
on Fable otherwise the quota is going to get blown pretty soon." It was. The factory never named a
model, so every agent step ran on the agent program's default, which was the strongest and costliest
one. The run's own logs showed it, and so did the logs of the viewer's runs 12 and 17. `Step.model`
existed and was marked "unused in this stage"; choosing a model per step was listed as out of scope.

**What it cost.** Run 18's planning (ten agent steps, two of them send-backs) came to about $13.22 of
estimated agent cost on the strongest model. The rest of the run (tests, build, architect, documents,
final review) was switched to the standard model through the `ANTHROPIC_MODEL` environment variable,
without touching the factory mid-run, and came to $2.85. It was accepted.

**Changed, FR-088.** An agent step's entry names a grade, `standard` or `strongest`
(`workflow.GRADES`), and `standard` is the default. `agent.MODELS` is the one place that says which
model a grade is, as FR-041 requires. The operator's ruling: the strongest for the architect's review
and the final review (`review` in the plain and tidy tables, `converge` in the spec kit table), the
standard one for everything else, including all of planning.

**Not changed**: a target codebase cannot choose its own models, and nothing reports cost by grade.

Tests: `tests/test_step_shape.py` (every agent step of every table), `tests/test_agent.py`.
