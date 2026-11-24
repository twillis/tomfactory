# Feature Specification: A Fitness Function Tuned to Mutual Benefit

**Created**: 2026-11-23

**Status**: Agreed in conversation; part 1 to be built first. Not run through spec kit. Its requirements are numbered P-301 onward while they are proposed, and become FR-3nn, each with its tests, when built (constitution S8; renumbered 2026-11-24 because unbuilt FR numbers stopped the whole suite from collecting).

**Input**: The operator, 2026-11-23, reading bttr_erp's retros as the agents' feedback: "Idea... A way to
evaluate the retros and deal with them from a process tuning side if happy agents fits a fitness function.
Even for entertainment or learning". Then: "it is a way of observing the process that can point out what can
be tuned like what we are doing right now". Then: "Fitness function should be tuned to mutual benefit, you,
me, the factory, anthropic , even if it's just art or entertainment. Maybe we can tune resources towards one
or another as desired." Then: "So let's spec this out, how can we inject some params into factory and align
with a mutually beneficial goal." On the orchestrator's outline and its three questions: "Gtg  We can try it
see how it goes."

## Why

The factory is tuned from its retros, but only when the orchestrator reads them closely. Friction, what the
agents keep asking for, and whether a change paid off are all in the run records and nobody adds them up. The
operator wants that made routine, as a lens on the process that points at the next thing to tune, and wants
the factory steered toward an aim that serves every party to the work: the operator, the orchestrator, the
factory itself, and Anthropic (the operator's CLAUDE.md: "Make it a valuable experience for both parties").

## Terms

- **Scorecard**: the numbers one run gives each stakeholder, computed from its record.
- **Stakeholder**: the operator; the orchestrator (Claude Code as assistant CEO); the factory; Anthropic.
- **Rating**: the operator's own score of a run, 1 to 5 with an optional word, given at merge.
- **Mode**: a named set of weights over the stakeholders, and the dials those weights turn.
- **Suggestion box**: `docs/suggestions.md`, every retro suggestion with its answer.

## Part 1: the scorecard and the suggestion box (build first)

- **P-301**: After every run, the factory MUST compute a scorecard from the run's record alone and add it to
  the record, one line per stakeholder:
  - factory: extra attempts per step, test mends, needs-me stops, planned work dropped or left for merge,
    minutes of steps and cost;
  - orchestrator: whether an agent asked a question or a measurement, whether the plan was approved without a
    send-back, what the review found left for merge;
  - operator: minutes the run waited on him, the questions put to him, and his rating once given;
  - Anthropic: the retro's observations about the model's own behaviour (where it helped, where it cost time),
    quoted, for the operator to send or keep.
- **P-302**: The scorecard MUST also be appended as a row to a file in the target codebase, so it can be read
  across runs beside the factory changes that landed between them. `docs/friction.csv` in the factory holds
  the history of bttr_erp's runs 18 to 71, computed by hand on 2026-11-23, as its starting point.
- **P-303**: The operator MUST be able to rate a run in one command at or after merge (`factory rate <run>
  <1-5> [word]`), and the rating MUST be recorded with the run and in the scorecard file.
- **P-304**: No agent step MAY be shown a scorecard, a rating or a weight. The scores judge the work; they are
  never a target an agent can write toward (the retro is written by a model, so a score it could see it could
  please).
- **P-305**: The retro step MUST be given the suggestion box and MUST, for each suggestion it makes, say
  whether it is new or which theme it continues; it MAY ask again for a declined theme only with a reason the
  decline did not weigh.
- **P-306**: The run record MUST end with the merge-time work the run leaves for the operator or the
  orchestrator (rows of the target's own documents to reword, rulings owed), as a checklist, so that work is
  tracked (suggestion #52).

## Part 2: modes and dials (after part 1 has been read for a few runs)

- **P-311**: A target's committed settings MAY name a mode (`mode = "ship"`, the default); a request MAY
  override it (`factory request --mode design`).
- **P-312**: Each mode MUST turn dials that change what the factory does, never what an agent is told about
  its score:

  | Dial | ship | design | art | research |
  |---|---|---|---|---|
  | plan-check rounds before the operator sees the plan | 1 | 2 | 1 | 2 |
  | plan check as a team of personas | off | on | on | on |
  | retro | short | full | full, in the personas' voices | full, with an experiment report |
  | budget cap per run (placeholder, the operator sets it) | $10 | $20 | $15 | $30 |
  | what the orchestrator brings the operator | rulings only | design forks with background | rulings and the retro's best | the experiment's result |

- **P-313**: The scorecard MUST give a weighted total under the run's mode, so a trade made on purpose
  (research mode costs more) reads as such.

## Part 3: an experiment

- A station as a team of personas, starting with the plan check (a database veteran, an ERP parity hand, a test
  sceptic), run in research mode and judged by the scorecard and the operator's ratings against the solo
  reviewer. Names, titles and backstories are the operator's to give, revealed "as time and budget allow and as
  needed" (2026-11-23).

## Decided in conversation, 2026-11-23

- The rating is one tap at merge, 1 to 5 with an optional word.
- Ship is the default mode; the operator switches up.
- Anthropic's line: observations are kept and feedback is drafted; nothing is sent without the operator's word.
- If the scorecard tells us nothing useful after a handful of runs, the orchestrator says so rather than
  adding to it.

## Out of scope

- Any score shown to the agents (P-304).
- Sending anything to Anthropic automatically.
- Choosing the weights' numbers before part 1 has been read.
