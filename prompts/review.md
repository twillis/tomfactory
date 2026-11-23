# Task: review the result

Judge the change below. Do not change any file. You may read the codebase in the current
directory to check what the change does.

## The request

{{request}}

## What kind of run this is

{{run_kind}}

## The approved plan

{{plan}}

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

## Smells

The factory measures line length and the lines of tests a run adds itself, and reports what it finds as smells in the run's record. A line over the codebase's length, or tests over its budget, is not a reason to reject, and not unbuilt work, even where the request asks for them.

## What to produce

A verdict. Accept only if the change does what the request asked, follows the plan, and
breaks none of the ideals. If any ideal is broken, list it and reject.

In your reply's JSON object:

- `verdict`: accept or reject
- `reasons`: plain sentences the operator can act on
- `ideals_broken`: each ideal the change breaks; empty if none
