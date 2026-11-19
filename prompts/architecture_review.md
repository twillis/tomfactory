# Task: review the change as an architect

The tests pass. Review the change below for how well it will bear maintenance and future
change. You may read the whole codebase in the current directory. Your review is advice:
it does not decide whether the change is accepted.

## The request

{{request}}

## The approved plan

{{plan}}

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

In your reply's JSON object:

- `summary`: your overall view of the change, in a sentence or two
- `suggestions`: things that would make the code better; empty if none
- `warnings`: things that will cause trouble if left; empty if none
