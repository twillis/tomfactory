# Change record: a step's effort, set per codebase (2026-11-26)

Made outside spec kit, for spec kit to review later. The evidence is bttr_erp's run 105 (capability 9b), whose four
planning speakers ran on the strongest grade as a trial approved by the operator ("Yes go for it"). Its planning cost
about $40 over seven rounds, against run 104's $21 on the standard grade, and the operator's five-hour usage limit ran
out during its plan check, ending the run needs-me. Built as FR-158.

**Asked for by the operator, through the orchestrator.** "Considering that fable burned through my 5hr limit in way
less than 5 hrs I'm inclined to think escalating to fable is not a great idea. Perhaps setting the effort instead of
using biggest model." On the orchestrator's proposal: "I think the effort setting is a good idea".

**Changed**

1. `factory/workflow.py`: `EFFORTS` (low, medium, high, xhigh, max, the agent program's own levels) and
   `Step.effort`, None by default; an effort outside the list, or on a code step, is refused.
2. `factory/tables.py`: `effort` joins the fields a project's `[steps.<name>]` may set (FR-112), checked the same way.
3. `factory/agent.py`: `run_agent(effort=)` adds `--effort <level>`; with none, nothing is added.
4. `factory/driver.py`: the step's effort is passed to the agent and recorded in its `step_start` event beside the
   model.
5. `factory/cli.py`: `factory table` shows a step's effort.
6. Tests: `tests/test_agent.py` (each level reaches the program's argv; none by default),
   `tests/test_overrides.py` (applied; refused with its words; a driven run gives the set step its effort and the
   others none), and the fakes in `tests/fake_agent.py` and `tests/test_cli.py` take `effort`.
7. `README.md`, "A project's own settings for its steps", and FR-112's wording name `effort`.

**Not changed.** No step's default effort: every step still runs at the agent program's default until a codebase sets
one, so nothing changes for a codebase that sets none. Reporting a run's tokens beside its dollars, proposed with this,
is left for the next factory batch.
