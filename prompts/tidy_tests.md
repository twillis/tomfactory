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

## How to tidy

- Each behaviour should be tested once, at the level where it lives. Where the same rule is
  asserted at several levels, keep it at the lowest one and leave a single test at the outer
  level that proves the levels are joined up.
- Fold variations of one rule into one parametrised test.
- Where several helpers build nearly the same thing, keep one that takes arguments.
- Remove a test only when another test still catches the same mistake. Do not remove the
  only test of a behaviour.
- Do not change what any remaining test asserts.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "summary": "what you changed, with the number of tests and lines before and after",
  "removed": ["each kind of test you removed, and which remaining test still covers it"],
  "kept": ["each behaviour that is still tested, in a phrase"]
}
```
