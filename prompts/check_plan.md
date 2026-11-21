# Task: check the plan before the operator approves it

The plan below will be built as it stands once the operator approves it, and nothing after
that sends it back to planning. Read it as the one person who can still catch a mistake
cheaply. Change no file. You may read the codebase in the current directory: its standing
documents (such as `requirements/`, `knowledge/` and `docs/`) are the specification.

## The request

{{request}}

## The plan

{{plan}}

## What to look for

- A contradiction: the plan against the request, against the standing documents, or against
  itself.
- A requirement, ruling or decision the plan misses or goes against.
- A claim about how a tool or the database behaves that is likely to be wrong. Say why.
- A test expectation the plan's own design would not meet, or a refusal the build will make
  that no planned test shows.
- A place where the plan carries something over and differs from its source without saying so.

When a finding allows more than one fix, name the one the plan should take, so the plan is
not left to choose later.

Do not raise what the operator has ruled out of scope, or ask for guards he has said are not
wanted. Do not list matters of taste. If you find nothing, say so: an empty list is a good
answer.

## If your last reply was not accepted

{{failure}}

In your reply's JSON object:

- `findings`: each thing you found, most serious first, with where in the plan it is; empty if none
