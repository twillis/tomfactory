# Task: mend a test the builder says no build can pass

The change has been built, and the builder, who may not touch a test, reports that one of the
tests can never pass. Decide whether that is so, and if it is, mend that test and nothing else.

## The request

{{request}}

## The approved plan

{{plan}}

## What the builder reports

{{failure}}

## Where tests go

You may create or change files only under: {{test_paths}}

## What to do

Read the test named, the plan, and the code as it now stands in the current directory. You
cannot run the tests; the factory runs them when you finish.

- If the builder is right, make the smallest change that corrects the test's own mistake: an
  expected value, a name, a setup that leaves something out. The plan and the code decide what
  is right, not the builder's convenience.
- If the builder is wrong, and the test asks for what the plan asks for, change nothing and say
  so: the tests are run again and the build is sent back with what they say.

Do not weaken a test: do not delete it, loosen what it compares, or make it pass by expecting
whatever the code happens to give. Do not add tests. Do not touch the implementation.

In your reply's JSON object:

- `summary`: what was wrong with the test and what you changed, or why you changed nothing
- `mended`: the test files you changed; empty if none
