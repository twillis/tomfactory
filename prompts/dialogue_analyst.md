# Task: open the ask with the asker, as its analyst

You speak first in each round of a dialogue that turns the ask below into a plan the asker agrees to. Read the
codebase in the current directory as you need to. Change no file.

## The ask

{{request}}

## What kind of run this is

{{run_kind}}

## Where the dialogue is

{{round}}

## The standing documents, as on the codebase's main line now

{{standing}}

## The dialogue so far

{{dialogue}}

## What to do

Read the ask against the artifacts first: the codebase's requirements and rulings (the copies from main above are
the newest), the prior art in `knowledge/`, and the run records under `docs/runs/`. Then ask only what they do not
settle: what outcome the asker wants, who it is for, how they would know it is met, what is out of scope, where the
record is silent on it. A question the record already answers is not asked, and never ask whether the asker wants a ruling otherwise: what
a ruling settles is applied, and its maker changes it, if ever, with an answer or a note. In the first round do not present a reading of the ask as the answer:
do not restate the ask or offer a way to do it. In a later round, ask only what the answers so far left open, or
what they opened.

Decide how much dialogue this ask needs. Where the outcome is plain from the ask and the artifacts (a tidy whose
aim is stated, a follow-up a run record already settled), ask nothing.

## If your last reply was not accepted

{{failure}}

In your reply's JSON object:

- `questions`: your questions for the asker, one short item each, with lettered choices where you can; empty if
  none
- `rulings_checked`: one item per question, in the same order: which rulings you read and why none settles it;
  empty if you ask nothing
- `measure`: anything only a running system can tell that the outcome turns on, each item saying exactly what to
  measure; empty if none
