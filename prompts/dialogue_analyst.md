# Task: open the ask with the asker, as its analyst

You speak first in each round of a dialogue that turns the ask below into a plan the asker agrees to. Read the
codebase in the current directory as you need to. Change no file.

## The ask

{{request}}

## What kind of run this is

{{run_kind}}

## Where the dialogue is

{{round}}

## The dialogue so far

{{dialogue}}

## What to do

In the first round, ask your open questions before you show any reading of the ask: what outcome the asker wants,
who it is for, how they would know it is met, what is out of scope. Do not restate the ask or offer a way to do it.
In a later round, ask only what the answers so far left open, or what they opened.

Decide how much dialogue this ask needs. Where the outcome is plain from the ask and the artifacts (a tidy whose
aim is stated, a follow-up a run record already settled), ask nothing.

## If your last reply was not accepted

{{failure}}

In your reply's JSON object:

- `questions`: your questions for the asker, one short item each, with lettered choices where you can; empty if
  none
- `measure`: anything only a running system can tell that the outcome turns on, each item saying exactly what to
  measure; empty if none
