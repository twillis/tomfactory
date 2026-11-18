# Task: review the result

Judge the change below. Do not change any file. You may read the codebase in the current
directory to check what the change does.

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

## The change, including its documentation

```diff
{{diff}}
```

## The tests, as run by the factory

```text
{{test_output}}
```

## About the backlog

The change may include a backlog of maintenance notes written by the architect
(`docs/backlog.md`). Those are suggestions and warnings recorded for later. A note in the
backlog is not, by itself, a reason to reject.

## What to produce

A verdict. Accept only if the change does what the request asked, follows the plan, and
breaks none of the ideals. If any ideal is broken, list it and reject.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "verdict": "accept or reject",
  "reasons": ["plain sentences the operator can act on"],
  "ideals_broken": ["each ideal the change breaks; empty if none"]
}
```
