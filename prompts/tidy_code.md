# Task: tidy the code

Improve the code without changing what it does. The tests do not change in this run and
must not: you may not change anything under the test paths. Every test must still pass
when you finish; the factory runs them.

## The request

{{request}}

## The approved plan

{{plan}}

## The rules this work is held to, in order of precedence

When two of these disagree, the earlier one wins.

### 1. This codebase's own constitution

{{constitution}}

### 2. The operator's ideals

{{ideals}}

## If the tests failed after your last attempt

{{failure}}

## What to produce

The tidied code. Behaviour as seen by the tests and by anyone using the code stays the same.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "summary": "what you changed and why it is better",
  "files_changed": ["the files you changed"]
}
```
