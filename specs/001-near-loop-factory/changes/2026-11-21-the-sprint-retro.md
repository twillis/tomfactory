# Change record: the sprint's retro, and its time and cost (2026-11-21)

Made outside spec kit with the operator's agreement ("go with yours"), for spec kit to review later.

**Asked for by the operator**, after the first sprint: "Should be a retro at the end for the team of
agents to publish. Basically what worked, what didn't and opportunities and threats. I like that I can
get time breakdowns as well all of that can be used to improve the factory."

**Changed**

- **FR-092, the facts.** `run_record.facts` renders each step's minutes, cost and outcome, the totals,
  and the time between steps (mostly waiting for the operator), from the factory's own records. Every
  run's record now has a "Time and cost" section. No agent measures anything.
- **FR-092, friction.** The shared reply fragment tells every agent it may add `friction`: what made
  its step harder. It is optional, so no envelope check changes.
- **FR-091, the retro.** A new advisory step, `retro`, after `converge` in the spec kit table, with a
  new persona, the facilitator, on the standard model. Its inputs are the facts, every agent's
  friction, the operator's comments verbatim, and the final review's and architect's findings. It
  writes `docs/retros/<run>.md`, an atomic note with front matter linking the run's record, under four
  headings. It is about the factory, not the product, and like the architect it never stops a run.
- `Rework.then` is now the step a bounded rework carries on to (`retro`), so a sprint whose unbuilt
  work was found twice still ends with its retro and its sprint review.

**Not changed**: the plain and tidy tables have no retro yet; a run that ends rejected or needs-me
skips it. A `factory retros` command to read retros across runs waits until there are several.

Tests: `tests/test_retro.py`; `tests/test_speckit.py` and `tests/test_workflow.py` updated.
