# Task: document the change

Write an account of what this run changed, for the operator.

## The request

{{request}}

## The approved plan

{{plan}}

## The change

```diff
{{diff}}
```

## What the factory measured

{{measured}}

State a number or a claim about the tests (how many lines were added, whether any was cut), the test budget, the
smells or the coverage only from these facts, never from the plan's hopes or its estimate. Where a fact you would
state is not here, leave the claim out.

## Where documentation goes

You may create or change files only under: {{docs_paths}}

## What to produce

A short written account of the change in the documentation paths. Do not change code or tests. Write nothing
under docs/runs/: that is the run's record, which the factory writes and rewrites; your `summary` is put in it,
under "What changed".

In your reply's JSON object:

- `summary`: one paragraph for the operator: what this run changed
- `files_changed`: the documentation files you created or changed
