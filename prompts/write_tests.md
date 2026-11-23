# Task: write the tests

Write tests that describe the change in the approved plan. Nothing has been built yet, so
your tests must fail when they are run. Read the codebase in the current directory first.

You cannot run the tests. The factory runs them as its next step and sends them back to you
if they pass or cannot be read as code, so do not claim to have seen them fail: work out from
the code why each one fails today, and check by reading that every name a test imports and
every table, file or row its setup relies on exists.

## The request

{{request}}

## The approved plan

{{plan}}

## Where tests go

You may create or change files only under: {{test_paths}}

## Keep them proportionate

As your priorities say. The codebase sets a budget for the lines of tests one run may add. The
factory measures it and reports a set over it to the operator; a good set fits well inside it.

## If your last tests were not accepted

What was wrong, if anything:

{{failure}}

## If this codebase uses spec kit

Where spec kit is in use, the task list in the feature directory says what to do and in what
order; do the tasks that are yours, and do not mark tasks done.

## What to produce

Test files under the test paths, covering the edge cases and failure cases as well as the
main path. Do not write any of the implementation.

Never drop a case the plan lists. Where a planned case cannot show what it is there for (a key
from the wrong table, a value refused for another reason first) and what it is meant to show is
plain, write it so it shows that, and say in `summary` what you changed and why. Where its
intent is not plain, write it as planned and say in `summary` why it may not show its rule.

In your reply's JSON object:

- `summary`: what the tests check, in a sentence or two
- `test_files`: the test files you created or changed
- `edge_cases`: each edge case or failure case your tests cover, one per entry

`edge_cases` must not be empty.
