# Task: tidy the tests

Make the tests smaller and clearer without losing what they protect. The code does not
change in this run and must not: you may only change files under the test paths. Every
test must still pass when you finish; the factory runs them.

## The request

{{request}}

## The approved plan

{{plan}}

## Where tests are

{{test_paths}}

## If the tests failed after your last attempt

{{failure}}

## The budget does not apply here

A codebase's `test_budget_lines` limits the *new* tests a normal run may add. It does not
apply to a tidy. Write whatever parametrised tables and shared helpers the tidy needs; what
matters is that the file ends up smaller and nothing that was protected is left unprotected.

## How to tidy

- Bring the tests to what your priorities ask: each behaviour once, at its lowest level, with
  one outer test showing the levels are joined up.
- Fold variations into tables; do not delete them. A case that was worth testing is a row.
- Where several helpers build nearly the same thing, keep one that takes arguments.
- Remove a test only when another test still catches the same mistake. Do not remove the
  only test of a behaviour.
- Do not change what any remaining test asserts.

In your reply's JSON object:

- `summary`: what you changed, with the number of tests and lines before and after
- `removed`: each kind of test you removed, and which remaining test still covers it
- `kept`: each behaviour that is still tested, in a phrase
