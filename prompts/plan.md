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

## If this codebase uses spec kit

Spec kit's instructions for this step, if the codebase uses spec kit:

{{speckit_instructions}}

What the factory has already set up for you:

{{speckit_context}}

If instructions are given above, follow them, with these differences. The scripts they
mention have already been run by the factory, and their results are what is listed above;
do not try to run anything. Write the specification and the plan, and the other documents
the plan instructions call for, at the paths given, inside the feature directory. You
cannot ask the operator questions: where the instructions say to ask, make an informed
assumption and record it in the document. Skip any step about hooks or branches. In your
envelope's `plan`, give a short summary and name the files you wrote, so those who build
from the plan can find them.

If nothing is given above, ignore this section and change no file.

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
