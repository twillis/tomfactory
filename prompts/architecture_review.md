# Task: review the change as an architect

The tests pass. Review the change below for how well it will bear maintenance and future
change. You may read the whole codebase in the current directory. Your review is advice:
it does not decide whether the change is accepted.

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

## The change

```diff
{{diff}}
```

## Where the backlog goes

You may create or change files only under: {{docs_paths}}

Keep the backlog in `docs/backlog.md`. If the file exists, read it and add to it; do not
repeat what is already there. Give each entry one line: what to do, in which file, and
whether it is a suggestion or a warning. If you have nothing to add, change nothing.

## What to produce

Your suggestions and warnings, each as one plain sentence, added to the backlog.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "summary": "your overall view of the change, in a sentence or two",
  "suggestions": ["things that would make the code better; empty if none"],
  "warnings": ["things that will cause trouble if left; empty if none"]
}
```
