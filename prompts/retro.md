# Task: the sprint's retro

The sprint has ended. Write its retrospective, for the operator and for whoever improves the
factory next. It is advice; it changes nothing and does not decide anything about this run.

## The request

{{request}}

## What the factory measured

These figures come from the factory's own records, not from any agent.

{{run_facts}}

## What each agent said made its step harder

{{friction}}

## What the operator said during the run, in his own words

{{operator_feedback}}

## What the final review and the architect found

{{findings}}

## The rules the run was held to

The codebase's constitution, which outranks the ideals:

{{constitution}}

The ideals:

{{ideals}}

Use them to weigh what you report. Where the request, the plan or a finding rested on one
rule and another outranks it, say which rule was missed and at which step it could have been
caught. Do not restate the rules.

## Where the retro goes

You may create or change files only under: {{docs_paths}}

Write one note, `docs/retros/{{run_name}}.md`, and nothing else. Begin it with this front
matter, filled in:

```yaml
---
kind: retro
run: "{{run_name}}"
date: YYYY-MM-DD
outcome: <the run's outcome so far>
cost: <the total from the figures above>
minutes: <the total from the figures above>
---
```

Then a title, a link to the run's record as `[[{{run_name}}]]`, and four headings:
**What worked**, **What did not**, **Opportunities**, **Threats**. Under each, a few short
points, each resting on evidence above.

In your reply's JSON object:

- `summary`: the sprint in one sentence
- `worked`, `did_not`, `opportunities`, `threats`: the same points as in the note
