# Task: plan a spike

A spike answers a question by building the smallest probe that measures the answer. Plan it.
Read the codebase in the current directory first. Do not change any file. No one approves this
plan: the probe is written from it straight away, so make it complete enough to build from.

## The question you are asked

{{request}}

## What kind of run this is

{{run_kind}}

## How the probe will be run

You and the probe's author can run nothing. The factory runs the probe itself, contained, with
this command, `{path}` being the probe's file in the checkout:

    {{probe_command}}

It gives the findings only what the probe printed and the code it exited with. A probe that
exits with an error has still measured something: a refusal can be the answer. Tests live under:
{{test_paths}}; a probe there may reuse the codebase's own fixtures, where its command allows.

## If your last reply was not accepted

{{failure}}

## What to produce

A short plan: the probe's file and anything else it changes, what it measures and prints, and why
that is the simplest thing that would answer the question. Leave out whatever does not bear on it.

In your reply's JSON object:

- `plan`: the plan, as Markdown text: the probe, what it changes, what it prints
- `question`: the question, in one or two sentences, as you will answer it
- `guess`: what you expect the answer to be, before anything is measured
- `yes`: what the probe's output would have to show for the answer to be yes
- `no`: what it would have to show for the answer to be no
- `cannot_tell`: what output would mean the probe could not tell
