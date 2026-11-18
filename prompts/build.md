# Task: build the change

Make the failing tests pass by building the change in the approved plan. You cannot run
the tests yourself; the factory runs them when you finish.

## The request

{{request}}

## The approved plan

{{plan}}

## The rules this work is held to, in order of precedence

When two of these disagree, the earlier one wins. Say plainly where that happens.

### 1. This codebase's own constitution

{{constitution}}

### 2. The operator's ideals

{{ideals}}

### 3. Spec kit's own instructions, where any are given further down

These come last. Follow them where they do not conflict with the two above.

## The tests you must satisfy

{{test_files}}

Read them. Do not change them, and do not change anything else under the test paths.

## If the tests failed after your last attempt

What failed, if anything:

{{failure}}

## What to produce

The code that makes the tests pass, following the plan and the ideals.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "summary": "what you changed and why, in a sentence or two",
  "files_changed": ["the files you created or changed"]
}
```
