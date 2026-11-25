# Feature Specification: The Factory Maintains Itself

**Created**: 2026-11-24

**Status**: A need, agreed; the five questions answered by the operator the same day, one at a time; two design
decisions taken (D1, D2, below). Nothing built.

## The need

Changes to the factory go through the factory's own process (an ask, the dialogue, an agreed plan, tests first, the
build, review, the retro) instead of being built by hand around it. On 2026-11-24 three factory changes (spikes,
planning as a dialogue, tuning the dialogue) were built by the orchestrator's agents in side worktrees, outside every
gate the factory gives a target codebase.

**How we would know it is met**

- A factory change is requested, planned in a dialogue, built, reviewed and recorded like any target's change, with a
  run record in tomfactory's own `docs/runs/`.
- A broken factory change cannot leave the factory unable to fix itself.

## In the operator's words (2026-11-24)

- "speaking of self improving, if the factory could be maintained by the factory process that would be really sweet
  LOOP!!"
- "i didnt watch the meta factory video but my guess is thats where it was heading."
- Earlier the same day, on self-improving agents: "even though I feel like thats what we got going on here".

## What is already known

- A run works in its own checkout of the target and the factory guards only its running copy (`config.factory_paths`),
  so a run targeting tomfactory changes a copy; the change takes effect only after it is merged.
- tomfactory has no committed `.factory.toml` yet.

## The questions

1. Fallback: how does a broken merged change get undone when the factory itself is what is broken (a pinned known-good
   install, a tag, a second clone)?
2. Approval: the factory reviewing its own change: is the operator's approval enough, or is an extra gate needed?
3. Which changes go through it: all factory changes, or not the ones to its own gates and guards?
4. Tests: the factory's suite gates its own runs (`uv run pytest`), contained; does anything differ from a target's?
5. The retro loop: does a retro's suggestion become an ask to the factory automatically, or only by the operator?

## The answers (the operator, 2026-11-24, one at a time)

1. **Fallback (A).** A pinned known-good copy of the factory, installed separately, is used to repair the main one when
   a merged change breaks it.
2. **Approval (B).** The operator's approval is not enough alone: before a factory change is merged, the known-good copy
   runs its own tests against the change.
3. **Which changes (B).** All factory changes go through the factory except changes to its own gates and guards, which
   stay hand-built and reviewed by the operator.
4. **Tests (A).** The fake-agent suite gates a factory run, as for any change; the live tests are not run.
5. **The retro loop (C).** A retro's suggestion for the factory is queued as a proposed ask; the operator approves which
   ones start.

## Design decisions (the operator, 2026-11-24)

- **D1. Trusting a change and trusting the factory.** Before merge, the new code's own tests are run by the currently
  installed, trusted factory (as every run already does). After merge, a canary: the known-good copy drives the new
  factory through one complete tiny run on a scratch codebase with the fake agent (ask, dialogue, build, tests,
  finish); if it fails, the known-good copy rolls the factory back to itself and says so; once it passes, the known-good
  copy advances to the new version. The operator asked the orchestrator for a suggestion and took it ("a"). (Not the
  old tests against new code: a change often updates tests on purpose.)
- **D2. Gates and guards, hand-built and reviewed by the operator.** For now ("b for now"): containment (`sandbox.py`),
  the factory's protection of its own files, the checks on what a step may change, the canary and rollback, and also
  the rules and step tables (`workflow.py`, `tables.py`).
- **Mechanics (the orchestrator).** Retro suggestions queue in `docs/suggestions.md`, listed by `factory proposals`, the
  operator choosing which start; tomfactory gets a committed `.factory.toml` on the sprint cycle.
- **Order.** The bootstrap (known-good install, canary, rollback) is a gate, so it is hand-built first; 8e on bttr_erp
  runs before it (the operator: "b").

## Next

Design, then build, by the factory's own process where the answers allow; the gates and guards that the build itself
needs (question 3) are hand-built.
