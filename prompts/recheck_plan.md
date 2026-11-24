# Task: re-check an agreed plan against the codebase as it is now

The plan below was agreed with the asker in a dialogue and has just been approved. Since the dialogue read the
codebase, the codebase has moved: what changed is listed below. Before anything is built, read the plan against
the codebase as it is now, in the current directory, and say what has gone stale. Change no file.

## The ask

{{request}}

## The approved plan

{{plan}}

## What the codebase gained since the dialogue read it

{{codebase_moved}}

## What to look for

- A file the plan adds that now exists, or one it changes that has moved, been renamed or been rewritten.
- A requirement, ruling or record the plan rests on that has changed.
- Work that was merged meanwhile and does part of what the plan does, or does it another way.
- A planned test whose expectation the new code makes wrong, or one that now passes before the build.
- A step given a file it may not write: the test writer only under {{test_paths}}; the documenter and the architect
  only under {{docs_paths}}.

What changed and does not touch the plan is not stale. Do not raise matters of taste, or anything the dialogue
settled.

## If your last reply was not accepted

{{failure}}

In your reply's JSON object:

- `verdict`: `accept` when the plan still holds against the codebase as it is now; `stale` when something has gone
  stale, which takes the plan back to the dialogue with your findings
- `findings`: each thing that has gone stale, and what the plan would have to change; empty if none
