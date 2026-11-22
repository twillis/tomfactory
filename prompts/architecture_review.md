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
whether it is a suggestion or a warning. Keep an entry short enough to read at a glance: the
reasoning belongs in your reply, not in the backlog. If you have nothing to add, change nothing.

The backlog holds what is still to do. An entry this change has answered, or that an earlier
change answered and nobody closed, is moved whole to `backlog-done.md` beside it, with the
run that answered it; an entry answered in part stays, saying what is left.

## What to produce

Your suggestions and warnings, each as one plain sentence, added to the backlog.

In your reply's JSON object:

- `summary`: your overall view of the change, in a sentence or two
- `suggestions`: things that would make the code better; empty if none
- `warnings`: things that will cause trouble if left; empty if none

## The tests before the build

What the new tests said when they were first run, before anything was built:

```text
{{red_output}}
```
