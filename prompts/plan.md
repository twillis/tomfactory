# Task: write a plan

Write a plan for the request below. Read the codebase in the current directory first.
Do not change any file.

## The request

{{request}}

## The operator's ideals

{{ideals}}

## If this is a revision

An earlier plan was sent back. The earlier plan, if there was one:

{{previous_plan}}

The operator's comment on it, if there was one:

{{comment}}

Address the comment. Keep what was right in the earlier plan.

## If your last reply was not accepted

What was wrong with it, if anything:

{{failure}}

## What to produce

A plan that a builder can follow without asking questions: which files to add or change,
what each will contain, and how tests could show it works. Keep it as short as it can be
while still being complete.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "plan": "the plan, as Markdown text",
  "ideals_addressed": ["one sentence per ideal that applies, saying how the plan follows it"],
  "conflicts": ["one sentence for each place the request conflicts with an ideal; empty if none"]
}
```
