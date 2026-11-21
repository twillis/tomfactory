# Task: is what was built what was approved?

Compare what was built with what was approved: the plan below, and where spec kit is used,
the specification and tasks too, following spec kit's converge instructions where given. Change no file. You may read the codebase in the current
directory.

## The request

{{request}}

## The approved plan

{{plan}}

## What was built

```diff
{{diff}}
```

## The tests, as run by the factory

```text
{{test_output}}
```

## How to judge

The plan was approved and the tests pass. Nothing you find sends the work back to planning:
this run is a sprint, and what you find is reported to the operator at its end, who decides
at merge what becomes the next request. Sort every difference between what was built and
what was approved into one of these:

- **Unbuilt work**: something the approved documents ask for is missing or incomplete, and
  the code writer could add it without a new plan.
- **An implementation detail**: it differs from the plan in a way that does not change what
  was required.
- **A requirement change**: something was added, dropped or altered that changes what the
  specification requires. Say what, so the operator can decide.
- **A broken ideal**: a rule of the codebase's constitution or the operator's ideals that the
  result breaks. Report it; it does not stop the run.

Only unbuilt work can be sent back, and only to the code writer. Paperwork the code writer
cannot write (a record, a document, a measurement it was not asked to keep) is a detail, not
unbuilt work.

Then give one verdict:

- `accept` if there is no unbuilt work. Everything else is recorded, and the run is accepted.
- `rework` if there is unbuilt work. It goes back to the build once; if you find unbuilt
  work again, the run is accepted and the work is left for the sprint review.

In your reply's JSON object:

- `verdict`: accept or rework
- `unbuilt`: each thing the approved documents ask for that is missing
- `details`: each difference that is only an implementation detail
- `requirement_changes`: each difference that changes what is required
- `reasons`: plain sentences the operator can act on
- `ideals_broken`: each rule of the constitution or the ideals that is broken; empty if none

## The tests before the build

What the new tests said when they were first run, before anything was built:

```text
{{red_output}}
```
