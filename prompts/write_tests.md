# Task: write the tests

Write tests that describe the change in the approved plan. Nothing has been built yet, so
your tests must fail when they are run. Read the codebase in the current directory first.

## The request

{{request}}

## The approved plan

{{plan}}

## Where tests go

You may create or change files only under: {{test_paths}}

## Keep them proportionate

As your priorities say. The codebase's budget for the lines of tests one run may add is
enforced: a set over it is sent back.

## If your last tests were not accepted

What was wrong, if anything:

{{failure}}

## If this codebase uses spec kit

Where spec kit is in use, the task list in the feature directory says what to do and in what
order; do the tasks that are yours, and do not mark tasks done.

## What to produce

Test files under the test paths, covering the edge cases and failure cases as well as the
main path. Do not write any of the implementation.

In your reply's JSON object:

- `summary`: what the tests check, in a sentence or two
- `test_files`: the test files you created or changed
- `edge_cases`: each edge case or failure case your tests cover, one per entry

`edge_cases` must not be empty.
