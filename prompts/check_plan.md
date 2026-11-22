# Task: check the plan before the operator approves it

The plan below will be built as it stands once the operator approves it, and nothing after
that sends it back to planning. Read it as the one person who can still catch a mistake
cheaply. Change no file. You may read the codebase in the current directory: its standing
documents (such as `requirements/`, `knowledge/` and `docs/`) are the specification.

## The request

{{request}}

## The plan

{{plan}}

## What was asked and answered while this was planned

Questions an agent asked during this run, and the answers it was given. A measurement was taken
on a running system by whoever drives the run.

{{planning_answers}}

Treat an answer as established. Where the request says one thing and an answer says another,
the answer stands: the request was written before it. Do not raise as a finding that the plan
follows an answer and not the request.

## What to look for

- A contradiction: the plan against the request, against the standing documents, or against
  itself.
- A requirement, ruling or decision the plan misses or goes against.
- A claim about how a tool or the database behaves that is likely to be wrong. Say why.
- A test expectation the plan's own design would not meet, or a refusal the build will make
  that no planned test shows.
- A place where the plan carries something over and differs from its source without saying so.
- An expected value in a planned test (a file's name or number, a count, an order, a message)
  that is wrong. Work each one out from that test's own setup, step by step; do not vouch for
  it because another test's value looks alike.
- A string a planned test hands to something that will have it read as a regular expression
  (pytest's `match=`, for example) and that holds characters with a meaning there.
- A rule the plan states for a whole family (every type, every archetype, every kind of row)
  on the evidence of one case. Name every kind of input the rule covers and say which the plan
  has not shown; ask for one measured case of each.
- Work the plan gives to a step that cannot do it: a file that step may not write, or one
  that does not exist and that no step is asked to create. The test writer may write only
  under {{test_paths}}; the documenter and the architect only under {{docs_paths}}; the builder
  anywhere except the test paths.
- A refusal whose message tells the reader what to do instead: follow the remedy, and say so
  if it leads to the loss the refusal exists to prevent, or is wrong for one direction of the
  change.

When a finding allows more than one fix, name the one the plan should take, so the plan is
not left to choose later.

Do not raise what the operator has ruled out of scope, or ask for guards he has said are not
wanted. Do not list matters of taste. If you find nothing, say so: an empty list is a good
answer.

## If your last reply was not accepted

{{failure}}

In your reply's JSON object:

- `findings`: each thing you found, most serious first, with where in the plan it is; empty if none
