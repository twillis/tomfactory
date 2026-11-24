# Feature Specification: The Factory Maintains Itself

**Created**: 2026-11-24

**Status**: A need, agreed. Nothing designed. Worked through with the operator one question at a time, as spec 005 was.

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

## Open questions (to work through with the operator; none answered)

1. Fallback: how does a broken merged change get undone when the factory itself is what is broken (a pinned known-good
   install, a tag, a second clone)?
2. Approval: the factory reviewing its own change: is the operator's approval enough, or is an extra gate needed?
3. Which changes go through it: all factory changes, or not the ones to its own gates and guards?
4. Tests: the factory's suite gates its own runs (`uv run pytest`), contained; does anything differ from a target's?
5. The retro loop: does a retro's suggestion become an ask to the factory automatically, or only by the operator?
