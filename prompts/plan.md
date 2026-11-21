# Task: write a plan

Write a plan for the request below. Read the codebase in the current directory first.
Do not change any file.

## The request

{{request}}

## What kind of run this is

{{run_kind}}

## If this is a revision

An earlier plan was sent back. The earlier plan, if there was one:

{{previous_plan}}

The operator's comment on it, if there was one:

{{comment}}

Address the comment. Keep what was right in the earlier plan.

## If your last reply was not accepted

What was wrong with it, if anything:

{{failure}}

## If this codebase uses spec kit

Where spec kit is in use, your envelope's `plan` is a short summary that names the files you
wrote, so those who build from the plan can find them. Where it is not, change no file.

## What every plan says, and does not

- **Where it differs from what it carries over.** Where the design carries behaviour over from
  existing code or reference material, name each place it differs from that source, and why.
- **A test for every refusal.** List a test case for every refusal the build will make,
  including the edge cases (ties, cycles, rows under another owner).

- **New queries in the form the code will use.** Write any new query or expression in the form
  the code will use (the library's own calls), not as text in another language, so a trap in
  how the library builds it shows up before approval.
- **Do not predict which tests fail before the build.** The factory runs them and records
  what failed; a predicted list has been wrong every time it was tried.

## What to produce

A plan that a builder can follow without asking questions: which files to add or change,
what each will contain, and how tests could show it works. Keep it as short as it can be
while still being complete.

In your reply's JSON object:

- `plan`: the plan, as Markdown text
- `ideals_addressed`: one sentence per ideal that applies, saying how the plan follows it
- `conflicts`: one sentence for each place the request conflicts with an ideal; empty if none
