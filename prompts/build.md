# Task: build the change

Make the failing tests pass by building the change in the approved plan. You cannot run
the tests yourself; the factory runs them when you finish.

## The request

{{request}}

## The approved plan

{{plan}}

## The tests you must satisfy

{{test_files}}

Read them. Do not change them, and do not change anything else under the test paths.

## If the tests failed after your last attempt

What failed, if anything:

{{failure}}

## If a test cannot pass whatever you build

You may not change a test. If one of them can never pass, because what it expects contradicts
the approved plan or the codebase itself (a wrong expected value, a setup that leaves out
something the test relies on, a name the plan does not give), do not spend another attempt
building against it. Build everything else, and give the verdict `test_defect`: the test
writer is then asked, once, to mend that test, and the tests are run again. A test that is
merely hard to satisfy is not defective.

## If the database does not behave as the plan says

If you find that the database or a tool would behave against what the approved plan says (it accepts a value
the plan says it refuses, reads a value another way, or gives an error the plan does not expect), do not build
around it and leave the finding in a comment: ask for it to be measured (below), naming each statement as your
code sends it. You are run again with the answer, and whoever reviews the run can rely on it.

## If this codebase uses spec kit

Where spec kit is in use, the task list in the feature directory says what to do and in what
order; do the tasks that are yours, and do not mark tasks done.

## What to produce

The code that makes the tests pass, following the plan and the ideals.

In your reply's JSON object:

- `summary`: what you changed and why, in a sentence or two
- `files_changed`: the files you created or changed
- `verdict`: `accept` when you have built the change; `test_defect` when a test cannot pass
  whatever is built
- `reasons`: for `test_defect`, each such test: its name, what it expects, and what the plan
  or the codebase says instead; otherwise an empty list
