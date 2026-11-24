# Feature Specification: Planning Is a Dialogue from an Ask to an Executable Plan

**Created**: 2026-11-24

**Status**: The need is agreed (the operator, 2026-11-24: "Yes the statement of need for planning is correct"). The
eight open questions were answered by the operator the same day, one at a time, from his phone (below). Nothing is
designed yet. Not run through spec kit. No requirement here carries an FR number until it is built (constitution S8).

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

## The questions (answered below)

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

## The answers (the operator, 2026-11-24, one question at a time)

1. **The shape of the dialogue.**
   - Who speaks first: the agents ask open questions first, before showing any reading of the ask (B).
   - Rounds, asynchronous: the agents ask, the asker answers when able, the agents follow up (A), "and it should be an
     agreement between that alignment is there": alignment is reached when both the asker and the agents agree it is,
     not when one side says so.
   - Where the asker answers: both the command line and Claude Code (C).
   - Found while answering, from his phone: a long, multi-part message cannot be answered from a phone's reply box
     ("I can't be scrolling back through that massive wall of text"). The dialogue asks one short question at a time,
     answerable in a word, with lettered choices where it can.
2. **What is agreed, and approval.**
   - The outcome and the way: the plan itself is agreed in the dialogue (B), "it also implies the amount of work and
     money that it will take to achieve the outcome": the agreement carries an estimate of the work and the cost.
   - Agreement is not approval to build; approval is a separate decision (B), "cuz that is a question of timing. It may
     be something that after the plan is finished we put it in the backlog to reintroduce at another time that is
     better". An agreed plan may wait in the backlog.
3. **Unknowns.** The agents ask for a measurement, as now (A), "and in order to get that measurements the orchestrator
   might do a spike or research or anything that is required to get the measurement".
4. **The agent team.** Each agent speaks to the asker directly (B): the planner, the architect and the plan check each
   raise their own points.
5. **Today's steps.** The dialogue replaces `check_plan` and `amend_plan` (A): the checker and the architect raise their
   points in the dialogue, not in separate steps after it. The proposed `architect_plan` step is not built; the
   architect is a voice in the dialogue.
6. **Who the asker is.** The same dialogue for everyone: the operator, another person, an orchestrating agent (A).
7. **When it is light.** The agents decide how much dialogue a change needs, and say so (C).
8. **Cost.** A budget per dialogue, as a spike has (B). At the budget the dialogue asks the asker whether to spend more
   (B), rather than stopping.

## Design decisions (the operator, 2026-11-24, one question at a time)

- **D1. How questions come.** Each agent sends its questions together, one batch per agent (B). The operator: "I
  assume when you the orchestrator receives it that you can walk me through them and gather the answers and send it
  back that should cut down on cost": whoever orchestrates walks the asker through a batch one question at a time and
  returns the answers as one batch, so each agent pays one turn per round, not one per question.
- **D2. Order.** All the agents speak in each round, side by side (B), not in turn.
- **D3. Alignment.** The agents propose "aligned", with the plan and its estimate; the asker agrees or does not (A).
- **D4. The estimate.** The agents' own judgement of the work and the money, shown beside similar past runs from the
  factory's own records (C).
- **D5. The budget.** Set per codebase, starting at $10 (C); at the budget the dialogue asks whether to spend more
  (answer 8).
- **D6. An agreed plan that waits.** It stays a run waiting for approval in the factory, approved whenever (A).
- **D7. Waiting blocks other work.** Yes, one run at a time, as today (B): "only because I know they will probably
  require a whole rethink of how this all works". Several plans waiting at once is a later rethink.
- **D8. A plan approved after waiting.** The agents re-check it against the codebase first and say what has gone stale
  (A).
- **D9. Answering at the command line, without an orchestrator.** `factory answer` opens the batch in the asker's
  editor, the asker writes each answer under its question (B).
- **D10. The record.** The whole dialogue, every question, answer and the agreed plan with its estimate, is kept in the
  run's record in the codebase (A).

## Next

The questions are answered and the design decisions made; next is the build, tests first, with the requirements
numbered into the factory's series as they are built. Until
then: no step entry or prompt changes. The queued factory changes that touch planning (an `architect_plan` step, the
planner treating a mechanism as a suggestion, a structured request) wait for this spec's answers, since each may be
folded into the dialogue.
