# Task: check the specification, plan and tasks against each other

Before anything is built, check that the specification, the plan and the task list agree
with each other and with the rules below, following spec kit's analyze and checklist
instructions. Change no file.

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

## If your last reply was not accepted

{{failure}}

## Spec kit, if this codebase uses it

{{speckit_instructions}}

### What the factory has set up

{{speckit_context}}

If both of those say (none), this codebase does not use spec kit: ignore this section.

## What to produce

The operator reads your summary to decide whether to approve the plan and tasks, so say
plainly what the plan is, what the tasks are, and anything that does not agree.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "plan": "a summary of the plan and tasks for the operator, naming the files they are in",
  "findings": ["each inconsistency, gap or broken rule you found, most serious first; empty if none"]
}
```
