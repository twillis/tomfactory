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

## Where documentation goes

You may create or change files only under: {{docs_paths}}

## What to produce

A short written account of the change in the documentation paths. Do not change code or tests.

In your reply's JSON object:

- `summary`: one paragraph for the operator: what this run changed
- `files_changed`: the documentation files you created or changed
