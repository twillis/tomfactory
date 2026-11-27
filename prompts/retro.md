# Task: the sprint's retro

The sprint has ended. Write its retrospective, for the operator and for whoever improves the
factory next. It is advice; it changes nothing and does not decide anything about this run.

## The request

{{request}}

## What the factory measured

These figures come from the factory's own records, not from any agent.

{{run_facts}}

What the factory measured of the tests, among them what the tests after the build said:

{{measured}}

## What each agent said made its step harder

{{friction}}

## What the operator said during the run, in his own words

{{operator_feedback}}

## What the planning dialogue asked

Refinement happens before a request reaches the factory: the operator and the orchestrator settle what is wanted,
record it as rulings, list what the change depends on, and measure what they can. Each question the planning
dialogue still asked is evidence about that refinement.

{{asked}}

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

Then a title, a link to the run's record as `[[{{run_name}}]]`, and five headings:
**What worked**, **What did not**, **The refinement**, **Opportunities**, **Threats**. Under each,
a few short points, each resting on evidence above.

Under **The refinement**: how many questions the planning dialogue asked, and how many of them
were measurements. For each that refinement could have settled before the run, say which and
how: a ruling already said it, two rulings disagreed, something the change depends on was
missing from the request's list, or a fact could have been measured first. Then say whether the
request's list of what the change depends on was complete, naming anything the plan had to add.
Where there was nothing to say, say "none" plainly; a run with no planning dialogue says so.

In your reply's JSON object:

- `summary`: the sprint in one sentence
- `worked`, `did_not`, `refinement`, `opportunities`, `threats`: the same points as in the note
