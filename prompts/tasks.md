# Task: write the task list

Break the approved plan into an ordered list of tasks, following spec kit's tasks
instructions. Tests come before the code they cover.

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

The task list, at the path the factory has set up.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "summary": "how many tasks, in what order, and anything the operator should know"
}
```
