# Task: is what was built what was approved?

Compare what was built with the approved specification, plan and tasks, following spec
kit's converge instructions. Change no file. You may read the codebase in the current
directory.

## The request

{{request}}

## The rules this work is held to, in order of precedence

When two of these disagree, the earlier one wins. Say plainly where that happens.

### 1. This codebase's own constitution

{{constitution}}

### 2. The operator's ideals

{{ideals}}

### 3. Spec kit's own instructions, where any are given further down

These come last. Follow them where they do not conflict with the two above.

## What was built

```diff
{{diff}}
```

## The tests, as run by the factory

```text
{{test_output}}
```

## Spec kit, if this codebase uses it

{{speckit_instructions}}

### What the factory has set up

{{speckit_context}}

If both of those say (none), this codebase does not use spec kit: ignore this section.

## How to judge

Sort every difference between what was built and what was approved into one of three kinds.

- **Unbuilt work**: something the approved documents ask for is missing or incomplete.
- **An implementation detail**: it differs from the plan in a way that does not change what
  was required. This is acceptable. Record it.
- **A change to the requirement**: something was added, dropped or altered that changes
  what the specification requires. The operator has not agreed to it.

Then give one verdict:

- `accept` if there is no unbuilt work and no change to the requirement. Details alone are fine.
- `rework` if there is unbuilt work and no change to the requirement.
- `replan` if anything changes the requirement. This sends the work back to planning and to
  the operator, so use it only for a real change to what is required, not for a detail.
- `reject` if the result breaks the codebase's constitution or the operator's ideals.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "verdict": "accept, rework, replan or reject",
  "unbuilt": ["each thing the approved documents ask for that is missing"],
  "details": ["each difference that is only an implementation detail"],
  "requirement_changes": ["each difference that changes what is required"],
  "reasons": ["plain sentences the operator can act on"],
  "ideals_broken": ["each rule of the constitution or the ideals that is broken; empty if none"]
}
```
