# Feature Specification: Planning Is a Dialogue from an Ask to an Executable Plan

**Created**: 2026-11-24

**Status**: The need is agreed (the operator, 2026-11-24: "Yes the statement of need for planning is correct"). Nothing
is designed. The open questions below are to be worked through with the operator before any design, by this spec's own
rule. Not run through spec kit. No requirement here carries an FR number until it is built (constitution S8).

## The need

Planning **is** the work of turning an ask into an executable plan, done with the asker. An ask is the beginning of
working on the plan, never a directive. The asker has a desired outcome in mind but does not necessarily know how to get
there. The agents can know how, because they have every artifact (the codebase, its requirements and rulings, its
backlog, its run records, the prior art in `knowledge/`) and can make sense of them. So the factory, not the asker and
not whoever orchestrates, carries the work of understanding the artifacts; and a short back-and-forth between the asker
and the agents aligns the two before anything is built.

**How we would know it is met**

- No plan is written straight from an ask; every plan traces to an outcome the asker has confirmed in that dialogue.
- An ask in plain words, with no mechanism and no knowledge of the artifacts, is enough to start.
- A mechanism in an ask is weighed as one candidate way, never taken as the task.
- The asker is asked only what the asker can answer; what the artifacts or a measurement can settle, the agents settle.

## In the operator's words (2026-11-24)

- "So we aren't able to interrupt the plan with our findings? Or something else?"
- "Also impl details submitted as requirements are dangerous most of the time. I've had product owners that would say
  'we need a table' and that was the task instead of 'user needs to be able to and I think this table should do it' and
  then engineering could discuss whether that is the best way to meet the need or not."
- "I don't even know how to write good requirements but I know what bad requirements are. So even now I give you a
  requirement just by talking about it and right away you implement it or plan to implement it when that is not the
  requirement I am expressing a need and a possible way of meeting that need it still needs to be vetted"
- "The request might not have a possible way. I guess the point is is that there needs to be something between the
  middle of the ask and the plan. Ask is not the plan the ask is the beginning of working on the plan."
- "Ideally I would like it to be an agent in the factory so that from the command line when you put in your ask the
  refinement process can be kicked off to ensure a good executable plan"
- "Okay so the input to the process should be treated as an ask and not a directive. There needs to be an agent that can
  analyze the ask and the code base and the current requirements and all that s*** to work with the asker to get a solid
  [executable] plan. I feel like this is what the planning process should be not input into the planning process. Like
  [planning] is the most expensive part of this process and I am now realizing that it's not doing what it should be
  doing. It's leaning on the operator too much for what it's being asked to do. Which doesn't even help the person
  asking. The person asking if it's a human cannot process all of the artifacts and make sense of all of the stuff to
  know what they need to ask in order for it to be successful so help through agents is necessary"
- "Yes the statement of need for planning is correct and that [the] asker [has] a desired outcome in mind but doesn't
  know necessarily how to get there. The agents will know how to get there because they have all the artifacts and [are]
  smart but there needs to be a dialogue of some back and forth for a little bit to achieve alignment between the
  [asker] and the agent team"

(Words in brackets correct dictation; nothing else is changed.)

## What the bttr_erp runs of 2026-11-24 showed (runs 86 to 94)

- **The orchestrator did the refinement by hand, outside the factory.** Its requests were long and carried measured
  facts, because a bare ask was not enough for the planner. Another orchestrator, or the operator directly, could not
  have written them.
- **A mechanism in a request became the task.** Run 94's request named `learn(forms=...)`, the orchestrator copying
  Clojure's load-at-boot shape; the plan followed it, and the plan check, which reads the plan against the request, passed
  it. The architect, reviewing the code against the plan, did not flag it either. By the time anyone reviewed, the shape
  was the premise.
- **Refinement happened late and one fact at a time.** The planners of runs 90, 91 and 92 asked for measurements
  mid-planning; runs 90 and 91 cost the most of the day ($18.97, $10.62) largely on send-backs and those rounds.
- **The operator was pulled in for what the agents should have worked out**, and was the one who caught the shape
  problems: the version as a hash of the row, colander against JSON Schema, `learn(forms=)`, rules a client might send.
- **The orchestrator made the same mistake in conversation**, turning "how do we make it part of the factory" into a
  four-layer build plan before the need was stated.

## Open questions (to work through with the operator; none answered here)

1. **The shape of the dialogue.** One conversation or several rounds? Who speaks first: the agent with its reading of
   the ask and its questions, or the asker? How does the asker answer from the command line, and from Claude Code?
2. **What the dialogue produces, and what the asker confirms.** The outcome and how we would know; what is out of scope;
   the candidate ways with their trade-offs; the chosen way and why? Is there one confirmation, or one for the outcome
   and one for the plan?
3. **Unknowns.** When the agents meet something only a running system can tell (a measurement) or only an experiment can
   (a spike), how does the dialogue use them: ask for a measurement, start a spike, or say what it would need?
4. **The agent team.** Which personas take part (the analyst the spec-kit cycle already has, the planner, the architect,
   the plan check), in what order, and who speaks to the asker?
5. **What becomes of today's steps.** `plan`, `check_plan`, `amend_plan`, the proposed `architect_plan`, and the single
   approval: kept, folded in, or replaced?
6. **Who the asker is.** The operator, another person, an orchestrating agent: does the dialogue differ?
7. **When it is light.** A tidy ("same behaviour, better shape") or a small follow-up: a shorter dialogue, or none?
8. **Cost.** What a dialogue may cost against what a misunderstood plan costs today, and how that is measured
   (spec 003's scorecard).

## Out of scope until the questions are answered

Any design, any step entry, any prompt. The queued factory changes that touch planning (an `architect_plan` step, the
planner treating a mechanism as a suggestion, a structured request) wait for this spec's answers, since each may be
folded into the dialogue.
