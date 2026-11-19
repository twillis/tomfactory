# Task: write a plan

Write a plan for the request below. Read the codebase in the current directory first.
Do not change any file.

## The request

{{request}}

## What kind of run this is

{{run_kind}}

## The rules this work is held to, in order of precedence

When two of these disagree, the earlier one wins. Say plainly where that happens.

### 1. This codebase's own constitution

{{constitution}}

### 2. The operator's ideals

{{ideals}}

### 3. Spec kit's own instructions, where any are given further down

These come last. Follow them where they do not conflict with the two above.

## If this is a revision

An earlier plan was sent back. The earlier plan, if there was one:

{{previous_plan}}

The operator's comment on it, if there was one:

{{comment}}

Address the comment. Keep what was right in the earlier plan.

## If your last reply was not accepted

What was wrong with it, if anything:

{{failure}}

## Spec kit, if this codebase uses it

{{speckit_instructions}}

### What the factory has set up

{{speckit_context}}

If both of those say (none), this codebase does not use spec kit: ignore this section.

Where spec kit is in use, your envelope's `plan` is a short summary that names the files you
wrote, so those who build from the plan can find them. Where it is not, change no file.

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
