# Task: the spike's retro

The spike has ended. Write its retrospective in one paragraph, for the operator and for whoever
improves the factory next: was the question answered for what it cost? It is advice; it changes
nothing and decides nothing about this run.

## The question

{{request}}

## What the findings said

{{spike_answer}}

## What the factory measured

These figures come from the factory's own records, not from any agent.

{{run_facts}}

## What each agent said made its step harder

{{friction}}

## What the operator said during the run, in his own words

{{operator_feedback}}

## Where the retro goes

You may create or change files only under: {{docs_paths}}

Write one note, `docs/retros/{{run_name}}.md`, and nothing else. Begin it with this front matter,
filled in:

```yaml
---
kind: retro
run: "{{run_name}}"
date: YYYY-MM-DD
outcome: <answered or inconclusive>
cost: <the total from the figures above>
minutes: <the total from the figures above>
---
```

Then one paragraph, and nothing more: whether the question was answered, what that cost in
minutes and dollars, and the one change to the factory that would have made it cheaper, if any.
Every claim rests on the figures or the words above.

In your reply's JSON object:

- `summary`: the paragraph's verdict, in one sentence
