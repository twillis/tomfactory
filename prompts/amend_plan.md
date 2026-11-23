# Task: amend the plan from the plan check's findings

You wrote the plan below. A reviewer has checked it and found the things listed under the findings. Amend the
plan once, before the operator reads it. Change no file. You may read the codebase in the current directory.

## The request

{{request}}

## Your plan

{{plan}}

## What the plan check found

{{plan_findings}}

## What was asked and answered while this was planned

{{planning_answers}}

An answer is established; where the request and an answer disagree, the answer stands.

## Where each later step may write

The test writer may write only under: {{test_paths}}. The documenter and the architect only under:
{{docs_paths}}. The builder anywhere except the test paths.

## What to do

Take each finding that is right: make the change it asks for, and only that. Decline a finding that is wrong,
and say why, from the codebase, the request or a measured answer, in one sentence. Do not take a finding by
weakening a test or dropping a requirement. Change nothing the findings do not touch: the operator has not
seen this plan yet, and what you return is what he reads.

A finding that turns on how the database or a tool behaves, which neither the codebase nor a measured answer
settles, is not left as a step for whoever drives the run: ask for it to be measured (below) instead of
returning the plan. You are run again with the answer, and amend then.

## If your last reply was not accepted

{{failure}}

In your reply's JSON object:

- `plan`: the whole plan, amended
- `taken`: each finding you took, and what you changed, one sentence each
- `declined`: each finding you declined, and why, one sentence each; empty if none
- `ideals_addressed`: how the amended plan follows each ideal, as before
- `conflicts`: any ideal the amended plan conflicts with, and why; empty if none
