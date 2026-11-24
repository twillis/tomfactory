# Feature Specification: Spikes, a Lightweight Kind of Run for R&D

**Created**: 2026-11-23

**Status**: Agreed in conversation, 2026-11-23; to be built after bttr_erp's run 7. Not run through spec kit.
The requirements are numbered R1 to R12 and are renumbered into the factory's own series when they are built, with
their tests (constitution S8). Built 2026-11-24 as FR-113 to FR-118 (`specs/001-near-loop-factory/spec.md`): R1 to
R3 are FR-113, R4 is FR-114 with R8's mend, R5 and R6 are FR-115, R7 and R9 are FR-116, R8's budget is FR-117, R11
and R12 are FR-118. R9's review and R10 are the orchestrator's (`orchestrator/playbook.md`); R12's scoring waits for
specification 003.

**Input**: The operator, 2026-11-23: "I wonder how we could fit r and d into this? Like as a lightweight spike."
On the orchestrator's outline: "2 things. Spike outcome not necessarily feeds into the next thing but it should be
filed with the code somewhere. And maybe we prioritize where and if it fits into the current running plan. And yeah
that person tree would be an excellent test of this. Goals to deliver the simplest thing that gets the answer. You
and I review against the plan."

## Why

The factory builds what is already decided. A question whose answer is not known ("what would a third network
cost?", "how does the reference behave here?", "which of two shapes is smaller?") is answered today by argument in a
plan, or by the orchestrator measuring by hand on a scratch database. A spike lets the factory find out, cheaply,
without the rules that exist to protect code that will be kept.

## Terms

- **Spike**: one run whose product is an answer, not a change.
- **Question**: what the spike is asked, in one or two sentences, with what would count as an answer.
- **Probe**: the throwaway code and the script that measures. It is never merged.
- **Findings**: one note saying what was asked, what was built, what was measured and what it means.

## Requirements

- **R1**: `factory request --kind spike "<question>" --target <codebase>` starts a spike. One run at a time, as now.
- **R2**: The spike's plan states the question, the guess, the simplest probe that would answer it, and what result
  means yes, no or cannot tell. The operator's goal governs it: "the simplest thing that gets the answer".
- **R3**: The probe step may change anything in the run's own checkout. None of the change cycle's gates apply to it:
  no test that fails first, no test budget, no line length, no architect, no documenter.
- **R4**: The factory runs the probe's script itself, contained, as it runs a codebase's tests. No agent runs
  anything. The script's output is given to the findings step.
- **R5**: The findings step writes one note, as a narrative a person reads top to bottom with the code in it: what was
  asked; then, in the order it happened, each thing that was tried, the code that tried it (the probe's own lines,
  quoted in the note, not only named), and what the script printed; then what surprised, what it would take to build
  properly, and what it did not find out. The operator: "I would like to see the code while reading the outcome of
  the spike sort of like as a narrative".
- **R6**: The findings are filed with the code. The note is committed on the spike's own branch, in the target's
  documentation paths (`docs/spikes/<run name>.md`, the run name being the branch's, as a run record's is), and
  names the branch that holds the whole probe. The probe's branch is kept and is never merged (the operator: "a
  branch with the code would be the easiest thing"). The note reaches the main line through the orchestrator, at
  the review (R9), never through the factory, which merges nothing; the spike's record says so. Every line of code
  the note quotes is checked by the factory's own code to be on that branch as quoted. *(Amended 2026-11-24 by the
  operator: "Findings reach main through the orchestrator, not the factory.")*
- **R7**: A spike ends as **answered** or **inconclusive**, with a reason. It is never accepted or rejected, and its
  record says plainly that nothing it built is in the codebase.
- **R8**: A spike is boxed: one attempt at the probe, one mend if the script cannot run, and a budget cap per run
  (placeholder: $5; the operator sets it). At the cap it ends inconclusive and says what it had.
- **R9**: A spike's findings do not feed the next request by themselves. After a spike, the operator and the
  orchestrator review the findings, decide what to do next, and document it (the operator: "Should just be we review
  and decide what to do next and document it"). The decision is added to the findings note, in his words, and to the
  target's run order where it schedules or drops work.
- **R10**: A request for a later run may name a findings note in its reading list, as it names any record.
- **R11**: A spike has its own persona, hired for it (see `docs/roster.md`): someone who builds the ugliest thing
  that answers the question and reports what surprised them.
- **R12**: A spike is scored like any run (specification 003) and has a retro of one paragraph: was the question
  answered for what it cost.

## Decided in conversation, 2026-11-23

- A spike's plan does not wait for approval; the orchestrator shows the operator the question before it starts
  ("Agreed").
- The probe's code lives on a kept branch, and the findings note quotes it as it tells what happened (R5, R6).
- The review is the two of them deciding what comes next and writing it down (R9).

## Decided by the operator, 2026-11-24

- Findings reach the main line through the orchestrator, not the factory (R6, amended above).
- The probe is run by a `probe_command` in the target's committed `.factory.toml`, with `{path}` the probe's file
  (for bttr_erp, `.venv/bin/python -m pytest -q -s -p no:cacheprovider {path}`, so a probe is a pytest file that
  reuses the target's fixtures), contained as the tests are. A non-zero exit is not a failure by itself: a probe may
  measure a refusal. A spike on a target with no `probe_command` is refused when it is requested.
- The budget cap is per spike, $5.00 by default, settable per target (`spike_budget_dollars`).

## The first spike

A third network beside `/tenant` and `/ref`: a tree of people. On bttr_erp, the question: what is the simplest
root for a person that spans tenants, what does its containment policy have to say, what breaks in the two roots
that exist, and how much code is it. The operator: "that person tree would be an excellent test of this."

## Out of scope

- A spike that changes the factory itself.
- Running more than one spike at a time, or a spike beside a run.
- Deciding anything from a spike without the review of R9.
