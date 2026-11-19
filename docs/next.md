# What's next for the factory

Queued 2026-11-19. Each item names where its thinking already lives. Items are for the
factory itself; work the factory does on a target codebase (the viewer) is not listed here.

## 0. The architect's review of the factory — done (2026-11-19)

`docs/backlog.md`: all 44 entries addressed. Change record: `specs/001-near-loop-factory/changes/2026-11-19-architect-backlog.md`.

## 1. Small fixes found by real runs

No design needed. A few hours, no quota beyond a check run.

- **Tick tasks off in code.** On a spec kit codebase nobody marks `tasks.md` done, because
  the writers are told not to, so an agent cannot claim work is finished. The factory's code
  could tick a task when the tests that cover it pass. (`changes/2026-11-18-spec-kit-cycle.md`)
- **Tell the planner what the factory adds.** The planner writes "no documentation" into
  plans, then the architect and documenter add a backlog and a changelog, and converge has
  to excuse it. One paragraph in the plan prompt.
- **Retire the comments-travel stop-gap** on the plain cycle, now that the scope rule is
  settled. (research.md R22)

- **Tell the planner what kind of run it is planning.** Found on run 15 (2026-11-19): in a
  `--tidy code` run the planner planned new tests, which the code writer may not write, so the
  review rejected a correct change three times. The planner, and the reviewer, should be
  given the run's kind and what it holds still.

## 2. Cost: a model per step

The quickest lever on usage. A real run costs about $6; most of it is the planner, the test
writer and the architect reading the codebase. A cheaper model for the documenter, and
probably the code writer, would cut that without touching the judgement steps.

- The seam exists: step entries already have a `model` field, always empty, and the adapter
  passes `--model`. What is missing is choosing it, and showing cost per step so the choice
  can be judged.
- Pairs naturally with an API key as an alternative to the subscription.
- Next-stage list in spec.md; `contracts/agent-adapter.md`.

## 3. The operator's ideas, needing design first

- **An expert panel before planning.** An optional first stage where a set of personas must
  align on the requirements; for a bare idea, a validation step (will it make money, which
  features first). Spec kit's assess commands and the operator's existing board personas in
  Hive are both candidates. (research.md R23)
- **A factory per project.** A target codebase carries its own step table, personas and
  conditions. Nearly true already: the table is data and personas are files; what is missing
  is reading them from the target. Prerequisite for the panel being per project. (R23)
- **The architect in planning.** Advise the planner, or review the plan before the operator
  sees it. Open question for the operator: alongside the plan, or folded in? (R21)
- **Backlog to request.** The architect's findings sit in `docs/backlog.md`. A command that
  turns an entry into a `--kind tidy-code` request would close that loop.

## 4. Safety: a sandbox — phase 1 done (2026-11-19)

Phase 1 (feature 002): the test command runs in bubblewrap. Phase 2: contain the agent
program itself, which needs a network allowlist, so `srt` and an AppArmor profile for its
helper (research 002 R3). Also open: a per-codebase list of extra tool folders.

The original note:


The largest gap. Agents have no shell and are confined to their checkout, but the test
command runs code and tests that agents wrote, with the operator's permissions, and nothing
limits what that code does. A container or a throwaway user for the test step is the
obvious shape. Listed in the README under "What this proof of concept does not protect you
from".

## 5. Housekeeping

- **The factory's own tests**, against constitution S9: mostly not parametrised; perhaps
  15–20% could go, mainly in `test_cycle.py` and `test_speckit.py`. Deferred by the operator
  on 2026-11-18 ("leave it for now").
- **The completion report** in the workspace (`artifacts/technical/2026-11-18-…`) describes
  the factory as it stood on the first day; it predates the gateway, the spec kit cycle,
  questions, tidy runs and resume.
- **No remote.** The repository exists only on this machine.

## Recommended order

**Revised 2026-11-19 by the operator:** the sandbox (4) comes first — "I am more concerned
about the sandbox and isolation aspects" — and the expert panel is deferred ("I would defer
the expert panel stuff for now"). Then 1 and 2.
