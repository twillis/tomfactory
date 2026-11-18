# Design: a cycle that follows spec kit's stages (2026-11-18)

**Status**: proposed, not built. Written outside spec kit with the operator's agreement, for spec kit to review later. It builds on `2026-11-18-speckit-steps.md`, whose first slice (the planner with specify and plan) is built.

## The two rulings this answers

1. **Every spec kit stage has a persona that uses it.** "there is a spec kit implement which is what the builder should use and there's a spec kit plan that is what the planner should use so whatever stages are in spec kit there needs to be a corresponding persona that will utilize it."
2. **Scope is alignment between the plan and the artifacts.** "if something is introduced midstream it needs to be assessed on whether it actually changes the requirement or is simply an implementation detail. If it changes the requirement then it needs to go back to the planning stage."

They are one design. Spec kit already has the stage that makes the second assessment: **converge** compares what was built with the spec, plan and tasks.

## Spec kit's stages, and who would use each

| Spec kit stage | What it does | Persona | Where in a run |
|----------------|--------------|---------|----------------|
| constitution | Writes the project's principles | — | Not part of a run. Set up once per codebase. Read by every stage (FR-054). |
| specify | Turns the request into a specification | **analyst** (new) | First |
| clarify | Finds what the spec leaves unclear and asks | **analyst** | After specify. Its questions are what the operator answers at the wait. |
| plan | Design: how to build what the spec says | **planner** | After the spec |
| tasks | An ordered task list, tests first | **planner** | After the plan |
| checklist | A checklist of requirement quality | **reviewer** | With analyze |
| analyze | Checks spec, plan and tasks against each other and the constitution; changes nothing | **reviewer** | Before the wait, so the operator sees it with the plan |
| *wait* | — | the operator | Approves the spec, plan and tasks together, with the analysis and any open questions |
| implement | Carries out the tasks | **test writer** for the test tasks, **code writer** for the rest | After approval, as today: tests first, seen to fail, then built until they pass |
| converge | Compares what was built with spec, plan and tasks | **reviewer** | After the build. This is the scope assessment. |

The architect and the documenter stay as they are; spec kit has no stage for them.

## Converge is the scope rule

After the build, the reviewer, following converge, sorts every difference between the artifacts and the approved documents into one of three kinds:

| Kind | Meaning | What happens |
|------|---------|--------------|
| Unbuilt work | Something the plan asked for is missing or incomplete | Added to `tasks.md`; the run goes back to **implement**. Counted against the attempt limit. |
| Implementation detail | The artifacts differ from the plan in a way that does not change what was required | Recorded. The run goes on. |
| Requirement change | The artifacts add, drop or alter something that was required | The run goes **back to the planning stage**: the analyst and planner amend the spec and plan to state the change, and the run waits for the operator again. |

Nothing can be added in the middle of a run by the operator; that stays true. This rule is about what the *agents* introduce while working.

When a requirement change returns to planning, the operator has the same three choices as at any wait. Approving means the change is now part of the requirement. Sending it back with a comment means the plan must be changed to exclude it, and the build then has to remove it.

## What it does to the step table

Today: `plan` → *wait* → `baseline` → `write_tests` → `red` → `build` → `test` → `architecture_review` → `document` → `review` → `finish`.

Proposed, for a codebase that uses spec kit:

`specify` → `clarify` → `plan` → `tasks` → `analyze` → *wait* → `baseline` → `write_tests` → `red` → `build` → `test` → `architecture_review` → `document` → `converge` → `finish`

- Four new agent steps before the wait, one new persona (analyst).
- `converge` takes the place of `review`, and can send the run to `build` or back to `specify`.
- A codebase without spec kit keeps today's table. So the table has to be chosen per target, which is the first real step towards "a factory per project" (research.md R23).

## What has to be built

1. **A table per target.** The step table is chosen by whether the target uses spec kit. Later this is where a target could carry its own.
2. **More scripts in `speckit.py`**: tasks, analyze, checklist, implement, converge.
3. **A step that can send the run to more than one place.** Today a failed check leads to one `on_fail`. Converge needs three outcomes. The envelope's verdict becomes `accept`, `rework` or `replan`.
4. **Returning to the wait mid-run.** Today a run waits once. A replan makes it wait again, and approval must resume the build, not restart it.
5. **The analyst persona**, and prompts for the new steps.
6. **Undoing the stop-gap**: the operator's plan-stage comments would no longer need to travel with the request (research.md R22), because the spec and plan are the scope and comments are folded into them.

## Decisions needed from the operator

1. **Is the stage-to-persona table right?** In particular: a new *analyst* for specify and clarify, the *planner* for plan and tasks, and the *reviewer* for analyze, checklist and converge.
2. **Clarify.** Its questions cannot be asked mid-step. Proposed: they are listed for the operator at the wait, who answers them by sending the plan back with a comment. Alternatively the analyst makes assumptions and records them, as the planner does today.
3. **One wait or two.** Proposed: one, after analyze, covering spec, plan and tasks. Two would let the operator approve the spec before design starts.
4. **How heavy.** A full run of these stages produces many documents before any code. For a small request it may be more ceremony than the change. Proposed: the operator chooses per codebase, by whether it uses spec kit.

## What this does not cover

The expert panel before the plan (research.md R23) and spec kit's assess commands. They would sit before `specify`.
