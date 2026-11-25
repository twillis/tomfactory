# tomfactory

A small software factory you run on your own machine, so you can work *near* the loop
instead of *in* it.

You hand it a short written request for a change to a codebase. It writes a plan and stops.
(On a codebase that chooses the sprint cycle, the request is an ask: the agents talk it through
with you, a few short questions at a time, until you and they agree on a plan.)
You read the plan and approve it, or send it back with a comment. Once you approve, it does
the rest on its own — writes failing tests, builds until they pass, has an architect look
it over, documents the change, reviews the whole result — and notifies you when it has finished. You are not needed in between.

This is a proof of concept. It is meant to be read, used, and changed.

## How this was built, and why

I wanted to work *near* the loop with AI coding agents instead of *in* it: hand over a
request, read and approve a plan, and be told when it is done, without supervising every
step. Most "agentic" setups let the agent decide what happens next. This one does not.
**Agents propose; code disposes.** A plain Python script owns the order of steps, runs the
tests itself, and checks every result; the agents have no shell.

It was built in two days, by me working with Claude Code, in the same way it now works:

- **Specification first.** [spec kit](https://github.com/github/spec-kit) for the
  specification, plan and task list (`specs/`), and an independent analysis pass before any
  code was written, which found 39 problems, 8 of them critical, that were fixed in the
  documents first.
- **A constitution the work is held to** (`.specify/memory/constitution.md`). Among its
  rules: every requirement has tests that fail before it is built (78 requirements, each
  named by a test, enforced when the tests are collected), and "the most functionality for
  the least code, impeccably organised".
- **Personas per step.** A test writer who is not the code writer, a reviewer who may change
  nothing, an architect whose review is advice for a backlog, and a lead who answers the
  other agents' questions before they reach me (`personas/`).
- **Measured, not assumed.** Before containing agent-written tests, a harmless stand-in test
  showed they could read `~/.ssh`, reach the network and the docker socket, and outlive
  their step. Three ways to contain them were measured; the one chosen (bubblewrap) closes
  every hole, and the stand-in test is now a permanent check.
- **The factory reviewed itself.** Its own architect persona was run over its code and
  found 44 things to improve; all 44 were addressed, with the tests green after each.

Then it was used: **17 real runs** built [tomfactory-viewer](https://github.com/twillis/tomfactory-viewer),
a small web app for watching the factory's runs. Three consecutive requests were accepted
first time at about 7 minutes and $6 each. Along the way the runs exposed real problems: a
test writer producing ten lines of tests per line of code, a review that could reject but
not guide, no way to tidy without a failing test first, and work lost to a usage limit. Each
became a change to the factory, made test first. The record of each is in
`specs/001-near-loop-factory/changes/`.

Then it was used on something bigger: **thirteen runs (18 to 30)** built the first layers of
bttr_erp, a schema-driven, multi-tenant system like an ERP, in Python, from a specification the
operator wrote first. Its first package needed SQLAlchemy, Pyramid and a PostgreSQL driver, and
containment let in none of them, so a codebase can now name its tools and a setup command. The
runs on Opus and Fable showed planning took two-thirds of the time, so a run now waits once, at
the plan, and then goes to the end as a sprint, reporting what deviated instead of going back to
planning. Every run ends with a retro by the agents and a time-and-cost table, and the retros
drove most of what followed: a plan check before the approval, the tests before and after the
build in every record, and a `sprint` cycle for a codebase whose specification already exists,
since spec kit re-derived one every run. Each is in `specs/001-near-loop-factory/changes/`.

About 4,350 lines of Python, 654 tests, standard library plus pytest. What is next is in
`docs/next.md`.

## Driving it from Claude Code: `/factory`

You can run the factory by hand with the commands below. Or let Claude Code drive it for you:
write the requests, prepare what the agents need, watch the runs, read every plan and result,
and bring you only the decisions that are yours. That is the `/factory` command, and it is how
the bttr_erp runs (18 to 30) were done.

It is two files in `orchestrator/`:

- `playbook.md` is what the orchestrator does: starting a session, writing a request, what to
  do at the approval and when a run ends, improving the factory between runs, recording your
  rulings, and how to talk to you. It is the lessons of those thirteen runs, written down.
- `factory.md` is the command itself, which loads the playbook.

To install it on a machine, after the steps under "What it needs" below:

```bash
git clone https://github.com/twillis/tomfactory.git
cd tomfactory
uv sync
uv run python -m factory doctor
orchestrator/install.sh              # /factory in every project, as ~/.claude/commands/factory.md
orchestrator/install.sh ~/my-app     # or in one project only, as ~/my-app/.claude/commands/factory.md
```

The installer writes the command with this clone's path filled in; run it again if you move the
clone. Then, in Claude Code, in the codebase you want built:

```text
/factory status
/factory the next capability in the run order
/factory retro
```

The orchestrator approves nothing and merges nothing without your word. When you change how you
want it to work, change `orchestrator/playbook.md`.

## How a run flows

A run is one attempt to carry out one request. It goes through ten steps. Six are done
by an agent, each with its own persona. Four are done by plain code.

| # | Step | Done by | What it does | What it may change |
|---|------|---------|--------------|--------------------|
| 1 | `plan` | agent: planner | Reads the request, your ideals and the codebase; writes a plan | nothing — or, where the target uses spec kit, its specification and plan documents |
| — | *wait* | you | Approve, send back with a comment, or abandon | — |
| 2 | `baseline` | code | Runs the existing tests before anything changes | nothing |
| 3 | `write_tests` | agent: test writer | Writes tests that describe the change, edge cases first | test files only |
| 4 | `red` | code | Runs the tests: only the run's own test files, where the codebase says how. They must **fail** | nothing |
| 5 | `build` | agent: code writer | Makes the tests pass | anything except tests |
| 6 | `test` | code | Runs the tests. They must **pass** | nothing |
| 7 | `architecture_review` | agent: architect | Reviews the change for maintainability; adds suggestions and warnings to a backlog. **Advisory**: it never fails the run | documentation only |
| 8 | `document` | agent: documenter | Writes an account of what changed, stating figures only from what the factory measured (the record's "What the factory measured") | documentation only |
| 9 | `review` | agent: reviewer | Judges the whole result against the request, the plan and your ideals | nothing |
| 10 | `finish` | code | Ends the run as accepted | nothing |

On a codebase that chooses the sprint cycle (below), step 1 is a dialogue instead: rounds of `dialogue_analyst`,
`dialogue_planner`, `dialogue_architect` and `dialogue_check`, each asking you its own few short questions, until the
planner proposes a plan you agree to; then your approval; then, if the codebase moved meanwhile, `recheck_plan`.
See "Planning is a dialogue".

The idea underneath is **agents propose, code disposes**. An agent is only ever asked to
think and to write files. Whether the tests pass is found out by running them, never by
asking an agent. Whether an agent stayed inside what it was allowed to change is found out
from git, never from what the agent says it did.

### What happens after each step

Eight rules, applied in this order:

1. The step changed something it may not → the change is undone, the run ends, **needs-me**.
2. The step is advisory and failed in any other way → the failure is recorded and the run carries on.
3. The agent asked a question instead of finishing → the lead answers if it can, otherwise you are asked.
4. The step ran past its time limit → **needs-me**.
5. The agent program failed, or refused to let the agent work in its own checkout → **needs-me**.
6. An agent's reply did not end with the JSON it was asked for → that step runs again.
7. One of the step's own checks failed → what the step's entry says. Failing tests send the
   work back to `build`. Tests that do not fail first send it back to `write_tests`. A
   judging step's verdict chooses its route: the review's reject ends the run **rejected**
   (in a tidy, it sends the work back); a judge that contradicts itself is asked again.
8. Everything passed → the next step.

One more route, off the usual path. The builder may not change a test, so a test that can
never pass (a wrong expected value, a setup that leaves something out) used to cost it every
attempt. Now the builder says so, with the verdict `test_defect`, naming each such test in
`defective_tests`, and the `mend_tests` step asks the test writer to correct those tests and
nothing else; the tests are then run again. It goes on to `test`, not back to `red`, because the
build is already there. The test writer is given the builder's reasons, the tests it names (and
those earlier reports named), and what the last test run's report named as failing, each with
its message, where the codebase names a `test_report`. It may find the builder wrong and change
nothing.

Each defect gets its own mend: a later report that names a test no earlier report named is
mended too, so a builder that finds a second, different mistake in the tests is not left to spend
its attempts repeating it. A report that names only tests reported before is not chased (the
test writer has had its say on them, and asking again would only go back and forth): the tests
are run and their failure takes its usual course. A runner's `tests/test_x.py::test_z` and a test
report's `tests.test_x::test_z` count as the same test. There are at most two mends in a run: a
third different defect in one run's tests is for you to look at. A codebase can raise that with
`rework_at_most` on `[steps.build]` (below).

No step runs more than three times in one run (you can change the number per request). What counts is the
step's own work: a run that asked a question you answered does not count, and sending a plan back gives
the planner its attempts again. A question the lead answered still counts, so a step that only asks still ends.
When a step has used its attempts, the run ends as **needs-me** and tells you what failed.

### How a run ends

Every run ends in exactly one of three outcomes, with a reason you can read:

- **accepted** — the tests pass and the review found the result matches the request, the
  plan and your ideals. The work is on a branch, waiting for you to merge it.
- **rejected** — the review found a mismatch, or you abandoned the request.
- **needs-me** — the factory could not finish on its own.

A spike, whose product is an answer and not a change, ends instead as **answered** or
**inconclusive**, and only a spike ends so (see "Spikes" below); it can also end needs-me.

### Where the work goes

Each run works in its own checkout of the target codebase, on its own branch
(`factory/<when it was requested>-<first words of the request>`, for example
`factory/20261119-145203-add-a-greeting`). Your own working copy is never touched. An
accepted run leaves up to six commits on its branch: the plan you approved, the tests, the
change, the architect's backlog notes if it had any, the documentation, and the run's record.
Each commit says what it holds, in at most 72 characters: `Plan: <the plan's title>`,
`Tests: …`, `Build: …`, `Backlog: …`, `Docs: …` and `Retro: …` in the words of the agent that
wrote them, and `Accepted: <the plan's title>` (or `Rejected:`, `Needs me:`) for the record at the end, whose body gives
the outcome's reason, the review and the time and cost. Every body names the run and its request
and ends with the trailers `Factory-Run:` and `Factory-Step:`, so `git log --grep "Factory-Run: 62"`
finds a run's commits. The record is one file under `docs/runs/`, with the branch's own name. Neither is named by the
run's number, which is counted on your machine alone, so two people working on one codebase do
not collide. It is written when you approve the
plan (the request, anything you sent it back with, the plan) and completed when the run ends,
whatever the outcome (every step, the outcome and why, the review, the commits; a step a check failed says why, naming
the failing tests where the test command's output names them), so the reason
for a change, and how it was made, travel with it. On a spec kit codebase spec kit's own
documents under `specs/` hold the plan, and the record is written at the end only.
**You merge the branch yourself.** The factory never merges.

## Using the factory

Commands are run from this folder as `uv run python -m factory <command>`, or from any directory as
`uv run --project /path/to/tomfactory python -m factory <command>`: `uv sync` installs the factory into
its own environment. Below they are
written `factory <command>` for short; an alias makes that literal:

```bash
alias factory='uv run --project /path/to/tomfactory python -m factory'
```

### What it needs

It was built and tested on Linux (Ubuntu 26.04). The versions it was tested with are in
brackets.

| Needed | For | Install |
|--------|-----|---------|
| Python 3.13 and [uv](https://docs.astral.sh/uv/) | running the factory | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (uv 0.11) |
| git | each run's own checkout and branch | your distribution's package (git 2.x) |
| [Claude Code](https://docs.claude.com/en/docs/claude-code), signed in | the agents; it runs on your Claude subscription | `npm install -g @anthropic-ai/claude-code`, then run `claude` once to sign in (2.1) |
| bubblewrap | running a codebase's tests contained; without it the factory refuses to run them | `sudo apt install bubblewrap` (0.11) |
| notify-send | the desktop notification when a run needs you or has finished; optional | `sudo apt install libnotify-bin` |
| [spec kit](https://github.com/github/spec-kit)'s `specify` command | only for a codebase made with `--spec-kit`; the plain cycle does not use it | `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git` (1.3.3) |

Then, from this directory:

```bash
uv sync                             # pytest and complexipy, for the factory's own tests; the factory needs nothing else
uv run python -m factory doctor     # checks git, the agent, notifications, its home and containment
```

### Before the first run

```bash
factory doctor                      # is everything it needs installed and working?
factory init-target ../my-app       # make a new, empty codebase for it to work on
factory ideals --edit               # optional: state the ideals every run is held to
```

`factory init-target` creates a git repository with a small settings file, `.factory.toml`,
that says how to run that codebase's tests and where its tests and documentation live. To
use the factory on a codebase you already have, commit a `.factory.toml` to it by hand; the
one `init-target` writes is the example to copy.

### A run, start to finish

```bash
factory request "Add a page that says hello." --target ../my-app
```

On a sprint codebase this starts a dialogue, not a plan: the agents ask before they plan, and you answer, agree to
the plan they propose, and then approve it, as "Planning is a dialogue" below describes:

```bash
factory questions                   # the agents' questions, each agent's on its own
factory answer                      # opens them in your editor; write each answer under its question, save
factory answer --file answers.md    # or the same text from a file (or - for standard input)
factory answer --by orchestrator    # recorded as the orchestrator's, not yours (operator is the default)
factory note "Ruling: ..."          # a ruling or fact every agent reads from its next round on
factory plan                        # the plan they propose, with its estimate
factory agree                       # agree to it: this is not yet approval
factory approve                     # now build it
```

Add `--kind tidy-tests` or `--kind tidy-code` for a change that must not alter behaviour, or `--kind spike`
for a question to be answered by a throwaway probe; see below.

This returns at once. A plan is written in the background, and a desktop notification tells
you when it is ready.

```bash
factory plan                        # read the plan
factory approve                     # go ahead: the rest is unattended
factory revise "Also show the time."    # or: send it back with a comment
factory abandon                     # or: give up on the request
factory answer "..."                # if it stopped to ask you something
```

After `factory approve` you are not needed until the notification that the run has ended.

```bash
factory status                      # what is it doing now?
factory watch                       # follow it as it happens
factory show                        # the whole run: every step, what it was asked, what it produced
factory show --step 12              # one step in full, with everything the agent did
factory stop                        # stop a run; nothing it started is left running
factory resume                      # carry on a run that stopped as needs-me, from where it stopped
```

Resuming puts back whatever a stopped agent left half-done. Where the step that stopped is the factory's
own (the tests failing after the build used its attempts), the build's work is kept: mend what was
wrong, commit it in the run's checkout, and the resumed step checks the work again.
That is the way through when the test writer's mends (`mend_tests`, above) did not settle it.

Every command that takes a run works on the most recent run unless you give its number:
`factory show 3`. `factory plan`, `factory status` and `factory show` take `--json`.

`factory status` and `factory show` take `--read-only`, for a reader such as the viewer (FR-146). Every other command
first tidies the home: a run whose driver has died is ended as needs-me, "interrupted", and an older database is
brought up to date. With `--read-only` nothing is changed: the database is opened read-only, no run is ended and no
process stopped, and a home with no database, or one of another version than this factory reads, is refused, saying
so. (SQLite may still keep its own `factory.db-shm` beside the database.)

`factory status --brief` prints, as JSON, what a board needs of each recent run and nothing more (FR-147):

```json
{"id": 99, "state": "planning", "outcome": null, "request_words": "Ask (from the operator, ... first twenty words …",
 "current_step": "dialogue_planner", "stages": [...]}
```

No step's prompt or what it produced is in it, so it does not grow with them; `factory status --json` has them all.
`factory status --limit 30` gives the 30 most recent runs, in either form (10 by default).

`factory show --json`, and each run in `factory status --json`, carries `stages`: the run's progress, for a reader
such as the viewer to draw without a copy of the tables (FR-145). It is the main path of the run's own table, left to
right: from its first step, each step's next on passing, and past a wait to where approval leads. Your waits are
stages too, after the step that waits: `answers`, `agreement` and `approval` in a planning dialogue, `approval`
elsewhere; a spike has none. A step off the main path that the run took (`mend_tests`, `recheck_plan`) is shown
before the step it leads to. Each stage is:

```json
{"name": "build", "by": "code_writer", "group": "building", "state": "done", "tries": 2}
```

- `by`: the step's persona, `code` for a code step, `operator` for one of your waits.
- `group`: `planning`, `waiting`, `building` or `reviewing` (`tables.STAGE_GROUPS`; the waits are `waiting`).
- `state`: `done`; `current`, the step it is on or the wait it waits at (a step whose question waits for your
  answer is current); `to-come`; `failed`, where an ended run stopped short (rejected, abandoned, stopped, boxed), or
  an advisory step whose latest attempt failed and which the run carried on past; `skipped`, what an ended run never
  reached, a step it never ran, or a dialogue's `answers` when no question was asked.
- `tries`: how many times the step ran; 0 for a wait. A done stage with more than one was sent back and done again.

A dialogue goes round: in its second round its speakers before the current one are done and the rest, your answers
among them, are to come again. A run whose codebase can no longer be read at its starting commit, or that took a step
its table no longer has (it ran before the table changed), has `"stages": []`.

### When it has finished

```bash
cd ../my-app
git log --oneline factory/7-add-a-page-that-says   # what the run did
git merge factory/7-add-a-page-that-says           # take it, if you want it
```

### Spec kit, if the codebase uses it

Create a codebase with `factory init-target --spec-kit ../my-app` and spec kit is set up in
it. A run on that codebase follows spec kit's own stages, each carried out by a persona
following that stage's instructions from the codebase itself:

| Stage | Persona | What it produces |
|-------|---------|------------------|
| `specify`, `clarify` | analyst | `spec.md` |
| `plan`, `tasks` | planner | `plan.md` and its companions, `tasks.md` |
| `analyze` (with spec kit's checklist) | reviewer | A check that spec, plan and tasks agree; changes nothing |
| *wait* | you | **The one approval: specification, plan and tasks, with analyze's findings as notes** |
| `write_tests`, `build` | test writer, code writer | Following spec kit's implement stage, tests first |
| `architecture_review`, `document` | architect, documenter | As in the plain cycle |
| `converge` | reviewer | Is what was built what you approved? |
| `retro` | facilitator | The sprint's retro, about the factory: advice, never a gate |

The documents are on the run's branch under `specs/<branch name>/`, for example
`specs/20261119-145203-add-a-greeting/`: named from when the run was requested, not counted, so
two people specifying at once never make the same folder. `factory plan` gives a
summary of whatever is waiting for you and names the files. Sending the work back returns
the run to the planner, who may change the specification too.

**After approval the run is a sprint.** Nothing returns to planning. After the build, the
reviewer sorts each difference between what was built and what you approved:

- *Unbuilt work* goes back to the build once. Found again, it is left for the sprint review.
- *An implementation detail*, *a proposed change to the requirement* and *a broken ideal* are
  recorded. None of them stops the run.

The run's record ends with a **sprint review**: every deviation the reviewer found and the
architect's warnings and suggestions. You decide at merge which become the next request.

**And with a retro.** The record also holds the run's **time and cost**, measured by the
factory's own code: each step's minutes, cost and outcome, the totals, and the time spent
waiting for you. Every agent may add `friction` to its reply: what made its step harder. Then
a facilitator writes `docs/retros/<run>.md`, an atomic note with front matter for an
Obsidian vault: what worked, what did not, the opportunities and the threats, for the factory
and not the product, quoting your comments in your own words. It is advice, like the
architect's, and never stops a run. Its inputs are `run_facts`, `measured` (among them what the tests
after the build said), `friction`, `operator_feedback` (the operator's own words only, never the
orchestrator's answers), `findings` and `run_name`.

**Whose rules win.** Where they disagree, the order is: the codebase's own constitution
(`.specify/memory/constitution.md` in it) first, then your ideals, then spec kit's generic
instructions. Agents are given all three and told that order. A codebase whose constitution
is still spec kit's blank template is treated as having none, so your ideals are the rules.

No agent runs anything to do this. Spec kit's scripts are run by the factory's own code,
and each persona is handed its stage's instructions and what the scripts set up. A codebase
without spec kit runs the plain cycle, exactly as before.

### The sprint cycle

A codebase whose specification already exists, in documents of its own, can choose a lighter
cycle in its committed `.factory.toml`, even where spec kit is set up:

```toml
cycle = "sprint"
```

A sprint is: a planning dialogue with you (below), in which the plan check reads each round's
plan for contradictions, missed rulings, wrong claims and untested refusals and the planner takes
or declines, with its reason, each point it raised; your agreement, then your one
approval, then the build, the tests, the architect, the documenter, `converge` (the
final review: unbuilt work goes back to the build once, everything else is recorded), `retro`
and `finish`. No spec kit stage runs. A tidy on a sprint codebase is planned in the dialogue too. The planner and
the plan check are told where each later
step may write, so a plan gives no step a file it may not touch; the diff the architect and the
final review are given leaves out the run's own record, which repeats the plan they already
have; and the retro is given the constitution and the ideals, so it can say which rule a run
missed. The record ends with the sprint review, what the new
tests said before the build and the tests after it, the time and cost, and the retro. `cycle = "auto"`, the default, picks spec kit where
it is set up and the plain cycle elsewhere.

### Planning is a dialogue

On a sprint codebase a request is an ask, the start of the work on a plan with you, never a directive. You know the
outcome you want; the agents have every artifact and can make sense of them. So the factory carries the work of
understanding the artifacts, and a short back-and-forth aligns you and the agents before anything is built
(specification 005).

**Rounds.** In each round four agents speak, one after another, each with its own batch: the analyst (who reads the
ask against the artifacts first and opens the first round with only what they do not settle, without leading with
a reading of the ask), the planner, the architect and the plan check (who both read the planner's plan of that
round). A batch holds questions for you, one short item each with lettered choices where it can, requests for a
measurement, and, from the architect and the plan check, points for the planner: **blocking** (it would make the
build fail or get stuck, or it contradicts a ruling, an answer or the ask) or **notes** (everything else, which the
planner takes or declines with a reason, and which never hold the dialogue open). In a dialogue the plan check is a
colleague at the planning table, not the assayer; it is exacting again in the final review. Each agent is told that
a mechanism in the ask is one candidate way, to ask you only what you alone can answer, and to settle what the
artifacts settle by reading them.

**What the agents read.** A run's checkout is frozen at the commit it started from; rulings committed to main
during a dialogue would be invisible in it. So before each speaker's turn the factory copies the codebase's
standing documents (`requirements/`, its constitution and `IDEALS.md`) as they are on its head now into
`.factory-main/` in the checkout, read-only and ignored by git (the folder's own `.gitignore` is `*`), and names the
commit and the files in the prompt (`standing`). What decides how the run is judged (`.factory.toml`, the table,
the checks) is still read from the starting commit.

**A note** (`factory note [run] "<text>"`, with `--by` to say who it is from) adds a ruling or a fact to a run while
it plans. Every speaker is given every note, with who added it and when, from its next round on; notes head the
transcript, and so the run's record. Refused on a run that has ended, or one not planning in a dialogue.

- Anyone asked something: the run waits for your answers, every agent's questions in one batch, each kept as its
  own. Where more than one agent asked, `merge_questions` (the facilitator, on the middle model) first merges
  questions from different agents that ask for the same decision, so you answer each once and the answer is
  recorded for each agent that asked; the transcript says what was merged into what. It judges what is decided,
  not how it is put: the same choice with its options in another order, under other letters or with one option more
  is one question; two on one subject where answering one leaves the other open stay apart. If the merge fails, or proposes one that
  does not hold, the batches come to you as they were asked. `factory questions` shows them; `factory answer` opens
  them in `$EDITOR`, each with `answer:` under it, and saving sends them all; `factory answer --file` takes the same text from a file or standard input.
  **Who answered** is recorded: `answer:` is the operator's (or whoever `--by` names), and `answer (orchestrator):` in
  its place marks one the orchestrator gave, a measurement above all; a merged question takes the answerer of the one
  it was merged into. The record, the plan check and the final review name who answered each; the retro's
  `operator_feedback` takes only the operator's. A batch with an
  answer missing is refused, naming it, and what you wrote is kept for next time. The next round is given every
  question and answer so far.
- Only blocking points for the planner: the agents go round again at once, without you. After as many rounds in a
  row as the run's attempt limit, the blocking points are put to you as a question.
- Nothing blocking and nothing asked: the planner has proposed **aligned**, with the whole plan and its estimate.
  Only the agents propose it, and only when no one else raised anything blocking that round; notes raised beside it
  are shown to you with the plan, under "Notes raised on this plan, not taken into it". You `factory agree`, or
  reply with `factory revise "..."`, which begins another round.

**Agreement is not approval.** An agreed plan waits as a run awaiting approval, approved whenever you choose; one run
at a time, as always. If the codebase's head has moved since the dialogue read it, `factory approve` starts the run's
checkout again from the head, and `recheck_plan` reads the plan against the codebase as it is now: still holding, the
build starts; gone stale, the plan is marked stale and the dialogue takes it up again.

**The estimate** is the planner's own judgement of the work and the money, shown beside the factory's own records:
the last five runs of the same kind on the same codebase that ended accepted, with their minutes and cost.

**A budget** keeps it short: `dialogue_budget_dollars` ($10.00 by default; 0 for none). A round that ends at or over
it, counted since you last said to spend more, adds the factory's own question to the batch: spend more, yes or no?
What the dialogue has cost is one sum, by allowance (from the start, then from each yes), and the run's record
shows it beside its time-and-cost table: the figure each question quoted, and the total of the speakers' rows.
No pauses the dialogue: the run waits, nothing lost. `factory status` says "paused at its budget", `factory questions`
shows every round so far and the planner's latest draft, and the run's record on its branch holds them. From there,
`factory answer yes` goes on to the next round with a fresh allowance, `factory agree` agrees to the latest draft, or
`factory abandon`.

**How much dialogue** a change needs is the agents' call, and the planner says it in every reply: a tidy whose aim
is stated may be aligned in its first round, with nothing asked. The whole dialogue, every round, question, answer,
measurement, point and plan proposed, is in the run's record under "The dialogue". `factory status`, `watch` and
`plan` say what the run is waiting for (answers, from which agents; agreement; approval), and `factory plan` never
shows a plan you replied to, or one found stale, as the current one.

### Tidying: a change that must not alter behaviour

The normal cycle insists on tests that fail first, which is right for a change and wrong
for a tidy-up: trimming tests or reshaping code should make nothing fail. For that:

```bash
factory request "Cut the duplicate tests." --target ../my-app --kind tidy-tests
factory request "Give the greeting text one home." --target ../my-app --kind tidy-code
```

A tidy run goes: plan, your approval, the existing tests (which must pass), the tidy step
(`tidy_tests` or `tidy_code`),
the tests again (which must still pass), review. One side is held still: tidying the tests
may not touch the code, and tidying the code may not touch the tests. The architect's
backlog is the natural source of tidy requests.

### Spikes: a question answered by a throwaway probe

A question whose answer is not known ("what would a third root cost?", "which of two shapes is
smaller?") is answered by a spike: a run whose product is an answer, not a change.

```bash
factory request "What is the simplest root for a person that spans tenants?" --target ../my-app --kind spike
```

A spike goes: `spike_plan` (the question, the guess, the simplest probe that would answer it, and
what result means yes, no or cannot tell), `probe` (builds it), `run_probe` (the factory runs it),
`write_findings`, `spike_retro` and `finish`. It does not wait for your approval: when Claude Code drives the factory,
the orchestrator shows you the question before it starts the spike. None of the change cycle's gates apply: no test that fails
first, no test budget, no line length, no architect, no documenter. Its plan, probe and findings are
carried out by its own persona, Juno Halloran, Prospector (`personas/spike.md`): the ugliest thing
that answers the question, and what surprised her.

- **The probe** may change anything in the run's checkout except what decides how a run is judged
  (`.factory.toml`, `.gitignore`, the ideals, the constitution). Its reply names its file, and it is
  committed at once, so the probe is on the branch whatever happens next.
- **The factory runs it**, contained exactly as it runs the tests (setup first, the codebase's tools,
  the network only where its tests have it), with the codebase's `probe_command`, `{path}` replaced by
  the probe's file. What it printed and how it exited go to the findings. Exiting non-zero is not a
  failure: a probe may measure a refusal. It **cannot run** when its file is not in the checkout, the
  setup fails, it does not finish in time, or it exits with a code in `probe_cannot_run_exit_codes`
  (`no_tests_exit_code` alone when that is empty; for pytest, `[2, 5]` adds a collection error); then
  the probe is mended once, and a second time ends the spike inconclusive. For pytest, a probe is a
  test file that reuses the codebase's fixtures.
- **The findings** are one note, `docs/spikes/<run name>.md` on the spike's branch: what was asked,
  each thing tried with the probe's own lines and what it printed, what surprised, what it would take
  to build properly, and what it did not find out. The factory's code checks every quote: each code
  block must be whole lines of a file on the branch the findings step did not write, and each block
  fenced as `text` must be what the probe printed. A note that is missing, or quotes what is not there,
  goes back once; a second time ends the spike inconclusive.
- **The retro** is one paragraph, `docs/retros/<run name>.md`, on the light grade, as advice: was the
  question answered for what it cost.
- **A budget** boxes it: `spike_budget_dollars` ($5.00 by default; 0 for none). Before each agent step
  the factory adds up what the run has cost, and at or over the budget the spike ends inconclusive,
  saying what it had done.

A spike ends **answered** or **inconclusive**, with the reason its findings give (abandoned at a
question, it is inconclusive; it is never accepted or rejected). Its commits are `Probe: …`,
`Findings: …`, `Retro: …` and `Answered: …` or `Inconclusive: …` for its record, which says plainly
that nothing it built is in the codebase. **The branch is kept and never merged, and the factory
copies the findings nowhere.** At the review you and the orchestrator decide what comes next; the note
is copied to the main line then, with your decision added to it in your words. A later request may
name the note in its reading list, as it names any record.

```toml
probe_command = ".venv/bin/python -m pytest -q -s -p no:cacheprovider {path}"   # "" (the default): no spikes
probe_cannot_run_exit_codes = [2, 5]   # pytest: a collection error, no tests; [] (the default): no_tests_exit_code
spike_budget_dollars = 5.0
```

A spike on a codebase with no `probe_command`, or one without `{path}`, or whose `docs_paths` do not
hold `docs/spikes/`, is refused when it is requested, naming the setting.

### Tests run contained

Every time the factory runs a codebase's tests, they run inside bubblewrap and can reach
nothing of yours beyond their own checkout. A codebase whose tests genuinely need the
network says so in its committed `.factory.toml`:

```toml
test_network = true     # off unless this line is here
```

`factory show --step <id>` on a test step shows `contained`, and whether the network was
allowed. `factory doctor` reports whether containment works on the machine. Tests that use
git fail contained.

### A codebase that needs things installed

The factory knows nothing about any language's packages. A codebase says what it needs, in
its committed `.factory.toml`, and the factory lets exactly that in:

```toml
tools = ["uv"]                      # programs on your PATH its commands may use, by name
setup_command = "uv sync"           # run before every test step: installs what it needs
test_command = ".venv/bin/python -m pytest -q -p no:cacheprovider"
```

- **`tools`** are let into containment read-only, each as that one program and nothing
  beside it. A tool is given by name, never by path, so the setting cannot be used to expose
  a folder of yours. A tool that is a launcher for something elsewhere in your home (a
  version manager's shim) will not work; name the real program.
- **`setup_command`** runs before the tests, every time the factory runs them. It is
  contained like the tests, with two differences: it has the network, because downloading is
  its job, and it can write to the codebase's own home.
- **The codebase's own home** is a folder the factory keeps for that codebase, under
  `codebases/` in the factory's home. Inside containment it stands in for your home
  directory, so an installer's cache lands there whatever the language, and the second
  setup is quick. The tests can read it and cannot change it. Nothing of yours is in it.

A Rust codebase would differ only in those three lines. What the setup command writes into
the checkout (a lock file) is committed with the step that ran it. If setup fails, the step
fails with what it last said, and the tests are not run. `factory show --step <id>` shows
that setup ran and had the network.

### Which model each step uses

Every agent step is given a model on purpose; none is left to the agent program's own
default. A step's entry names a grade, weakest first:

- **light** (Haiku), for the steps that summarise or answer from what is written: the
  documenter, the retro, the lead answering a question, and the merge of a dialogue's questions.
- **middle** (Sonnet), which no step starts on yet; a light step's second attempt runs on it.
- **standard** (Opus), for everything else, the architect's review and the final review
  included.
- **strongest** (Fable), which no step starts on: it is the operator's to choose.

**A retry climbs, when the work was wanting.** An attempt whose work was found wanting (a
check failed on it, its reply was the wrong shape, it changed what it may not, or a later step
sent it back) makes the next attempt run one grade higher, up to standard: a light step runs
again on middle, then on standard. An attempt that ended in a question or a timeout does not
climb: a stronger model would not have helped. A step never climbs to the strongest by itself. The run record's time-and-cost table says which model
each attempt ran on, so a cheaper grade can be judged by its first-attempt passes and its cost.

Which model each grade is, is written in one place, `MODELS` in `agent.py`. To give a step
another grade, set `model=` in its entry in `tables.py`.

### Tests that cannot be read are not failing tests

Before the new tests are run to see them fail, the factory runs the codebase's
`tests_readable_command` (by default `python -m compileall -q tests`), contained. A test file
with a syntax error fails every time whatever is built, and the builder may not touch tests,
so without this check it would use up its attempts on tests that can never run. When the
command fails, the work goes back to the test writer with what it said. Set it to `""` to
switch it off, or to your own language's equivalent.

### Red runs the run's own tests, if the codebase says how

Baseline, red and the test step after the build each ran the whole suite: on bttr_erp about five and a half minutes
each. Red's job is only to show that the run's new tests fail before the build, so a codebase may say how to run some
of its tests:

```toml
red_command = ".venv/bin/python -m pytest -q -p no:cacheprovider --junitxml=test-report.xml {paths}"
test_report = "test-report.xml"     # needed: red is settled by a test the report names as failing
```

Red then first runs that command, contained as the tests are, with `{paths}` (a word of its own) replaced by the files
under the test paths that the run added or changed and has not deleted: an edited file runs whole, its old cases beside
the new. A test among them failing, as the test report names, settles red. Anything else is settled by the whole suite,
as before: the files passing (a helper they changed may still break another test), the runner collecting nothing, or
exiting failing with no failing test named (pytest given a fixture's JSON exits 4 having run nothing). So what red
decides is what it decided before; it is quicker only when the new tests fail, which is the usual case. A
`red_command` without `{paths}` or without a `test_report` is refused. Baseline and the test step after the build
always run the whole suite. Without the setting, red runs the whole suite too.

### Keeping tests proportionate

Left alone, a test writer told to cover edge cases will keep finding more. Two things hold
it back. Its persona tells it to test each behaviour once, at the level where it lives. And
each codebase sets a budget, `test_budget_lines` in `.factory.toml` (300 by default; 0 for
no limit). The factory measures the lines a run's new tests add and, where they are over, reports it as a
smell in the run's record (below). Nothing is sent back for it. The test writer is told the budget up front, in its
prompt's `limits`, as a limit to write within.

### A longest line, if the codebase wants one

```toml
line_length = 120       # the longest line a step may add to code or tests; 0, the default, is no limit
```

Where it is set, the factory measures the lines each writing step added (the test writer, the
builder, a mended test, either tidy) and the code a plan gives, counting indentation, and reports
each line that is over, as `file:line (length)`. Lines already there are not measured, and
documentation is not: prose and tables run long. Each of those writers is told the limit before it writes, in its
prompt's `limits` (with the test budget, and that neither ever sends work back), so it writes within it from the start.

### Smells: measured and reported, never a reason to stop

The longest line, the test budget, coverage and readability are **smells**. A step entry names them under `smells=`,
beside its `checks=`: they are measured after the step's own checks pass, and what they find is
kept with the step and listed under "Smells" in the run's record, for the operator to tidy at
merge or in a later tidy. A smell never sends work back, never ends a run, and the final review
is told it is no reason to reject. On bttr_erp the line check had sent work back seven times and
once ended a run as needs-me for one line; the budget had never fired.

### Readability: functions hard to follow, flagged for the architect

A codebase may name a command that scores how hard each of its functions is to follow, and the
factory reports the functions a step added or changed that score over a limit. The measure is
**cognitive complexity** (SonarSource's: nesting and breaks in the flow cost more than length);
for Python, [complexipy](https://github.com/rohaquinlop/complexipy) computes it and writes JSON:

```toml
readability_command = ".venv/bin/complexipy src --isolated -q --output-format json --output readability.json"
readability_report = "readability.json"     # each function: path, function_name, complexity, line_start, line_end
readability_limit = 15                      # a smell over this; 15 is where SonarSource starts
```

After the builder and the code tidy, the factory runs the command contained, as it runs the tests
(it may use the codebase's `tools`, never the network), reads the report and removes it. Only a
function holding a line the step added is reported, as `file:function (score)`, so old code does
not shout every run. It is a smell: listed under "Smells" in the run's record and in what the
documenter and the retro are told was measured; it never sends work back. Any language's tool
will do whose output is put in that JSON shape; with no command, nothing is measured.

The score is a flag, not a verdict, and **a low score does not mean readable**: a dense one-liner
scores low and can read badly, and a flat dispatch can score high and read fine. So the architect
is given the flagged functions and judges them; one it finds hard to follow becomes a backlog
entry, a tidy-code run's natural source.

The factory measures its own code the same way. `tests/test_own_code.py` scores `factory/` with
complexipy (in the dev group) and reports, as a warning in pytest's summary, its non-blank lines
and its functions over 15. It never fails for them: a line limit raised four times in two days
stopped nothing, and the operator's first ideal is code a newcomer can follow, not less of it.

### A project's own settings for its steps

A codebase may tune the steps it already has, in its `.factory.toml`, without changing the
factory. Each `[steps.<name>]` table may set only `model` (a grade), `timeout` (seconds),
`smells` (added to the step's own, never removed) and `rework_at_most` (the cap on a step's
capped rework route); `climbs_to` sets how high a retried step climbs. Nothing that decides
what passing means can be set: not a step's checks, persona, prompt, inputs, where it may
write or where it leads. A setting that is not allowed is refused, naming it, when the
request is made, before anything is paid for.

```bash
factory table --target <codebase>      # the steps a run would go through, with its overrides
```

### Coverage: measured before and after, a smell when it falls

A codebase that names `coverage_report` in its `.factory.toml` (the coverage.py JSON its test
command writes) has its coverage kept each time its tests run. The run's record and its last
commit say what it was before the run and after it, and the test step reports a smell when it
ends below `coverage_floor` or fell by more than `coverage_drop` points, naming the files that
fell most. No model is involved: the test command measures, the factory compares.

### Which tests failed: read from the test report

A codebase whose test command writes a JUnit XML report (pytest: `--junitxml=<path>`; nearly every
test runner can) names it as `test_report` in its `.factory.toml`. Each time the tests run, the
factory removes the old report, then reads the new one with the standard library: the tests it names
as failing or in error, each with its message. A step a check failed says in the record's step list
which tests failed (the first five), the builder's next attempt is told every one with its message, and
the documenter and the retro are told what the tests after the build said. Without a report, the record
gives the check's message, shortened, as before.

```toml
test_command = ".venv/bin/python -m pytest -q -p no:cacheprovider --junitxml=test-report.xml"
test_report = "test-report.xml"     # and add it to .gitignore
```

### When an agent has a question

An agent that cannot go on without an answer may ask one question instead of finishing. It
does not come straight to you:

1. The question goes to the **lead**, a persona that answers from what is written: the
   request, the plan and other documents, the codebase's constitution, your ideals. If
   those settle it, the step that asked runs again with the answer and you are not involved.
2. If the lead cannot answer, the run waits and you are notified with the question.

```bash
factory status                      # shows "a question for you", or "a measurement is asked for"
factory show                        # the question, and who asked it
factory answer "Use spaces."        # the step that asked runs again with your answer
```

**Asking for a measurement.** No agent can run anything, so an agent whose work rests on how a
running system behaves (what a statement returns, which version is installed) may ask for that
to be measured, in place of guessing: its reply is `{"measure": "..."}`. The lead reads
documents and cannot measure, so it is not asked. The run waits, the notification says "a
measurement is asked for", and `factory answer` gives the result to the step, which runs again.
When Claude Code drives the factory (`/factory`), it does the measuring, on a scratch system,
and tells you afterwards; the playbook says how.

**The work before the question is kept.** A step that wrote files and then asked is run again
with its work still in the checkout, and what it wrote counts as its own: the next attempt may
keep it as it is. The same holds after a check sends a step back. Only a step the run comes to
from another one, or after its head has moved (a resume, your commit), counts afresh. The
planner amending, the builder and the test writer mending are all told to ask for a measurement
when they find the database behaving against the plan, not to leave it in a comment.

What was asked and answered travels with the run (in a dialogue, every round's too). The plan check and the final
review are given
every answered question, with who asked and who answered, and are told that where the request
and an answer disagree, the answer stands: the request was written first.

A run cannot be approved past a question that is still waiting. Every question, who asked
it, the answer and who answered (the lead, the operator, or the orchestrator, with
`factory answer --by orchestrator`) are kept with the run and shown by `factory show`. An agent
that keeps asking uses up its attempts like any other step.

### The architect and the backlog

After the tests pass, the architect reviews the change for how well it will bear being
maintained: repeated code, blurred boundaries, the wrong tool for the job. It is written to
think like a Lisp programmer — someone who knows every paradigm as a tool with strengths and
weaknesses. It does not change code and it cannot fail the run. What it finds is added, one
line each, to `docs/backlog.md` in the target codebase, and recorded on the run
(`factory show --step <id>` for the `architecture_review` step).

The backlog holds what is still to do. An entry a change has answered is moved by the architect
to `docs/backlog-done.md`, with the run that answered it, so the backlog stays short enough to
read. The architect is the backlog's one owner: a plan names the entries its run answers, by their
quoted text, and the architect closes them; the documenter may not change either file, and a change
to one is undone. A codebase that keeps them elsewhere says so with `backlog_file` and
`backlog_done_file` in its `.factory.toml`.

The backlog is yours to work through. Any entry can be handed back to the factory as a
request of its own.

### Your ideals

`factory ideals` shows where the ideals file is and what it says. It is free text in your
own words, for example:

> Well-defined layers with explicit interfaces between them, so the system can absorb
> change over time.

Every plan must say how it follows them. Every review checks the result against each one;
a result that breaks an ideal cannot be accepted. Editing the file takes effect on the next
run and needs no other change.

That file is yours alone. A codebase more than one person works on can state its ideals
itself, in a committed `IDEALS.md` at its root. Where it does, every run on it is held to
those instead, whoever makes the request, read from the commit the run starts at; no step
may change the file.

### Things worth knowing

- **One run at a time.** A second `factory request` is declined until the first has ended.
- **Do not edit the factory while a run is in progress.** The factory checks after every
  step that its own code, personas, prompts and your ideals have not changed, and puts them
  back if they have. If you were the one who changed them, the run stops as needs-me and
  your versions are kept in the run's folder so nothing is lost. Editing the ideals between
  runs is fine.
- **Where it keeps things.** `~/.tomfactory` (or wherever `TOMFACTORY_HOME` points): the
  record of every run in `factory.db`, your `ideals.md`, a folder of logs per run, and each
  run's checkout under `workspaces/`.
- **A real run takes minutes.** Each agent step is a real session that reads the codebase
  and writes files. Six of them, from twenty seconds to a couple of minutes each.
- **It runs on your Claude subscription.** No API key is needed or used.

## Adding a step

A step is one entry in a table in `factory/tables.py`.

**A code step** is a check. Say you want to refuse any change that adds a file over 500
lines. Write the check in `factory/checks.py`:

```python
@register("no_huge_files")
def no_huge_files(ctx) -> CheckResult:
    huge = [name for name in ctx.checkout.files_changed_since_base()
            if len((ctx.checkout.path / name).read_text().splitlines()) > 500]
    return CheckResult(not huge, f"over 500 lines: {', '.join(huge)}")      # the registry adds the name
```

Then add its entry to `STEPS` in `factory/tables.py`, after `test`, and point `test` at it:

```python
Step("test", "code", on_pass="no_huge_files", checks=("tests_pass",), on_fail=Rework("build"),
     commit_after=True),

Step("no_huge_files", "code", on_pass="document", checks=("no_huge_files",), on_fail=Rework("build")),
```

That is the whole change. The driver, the store and the command line are not touched: the
new step is run, recorded and shown like any other.

**An agent step** needs two more things: a prompt at `prompts/<step name>.md`, and a persona
(an existing one, or a new file). In its entry you say which inputs its prompt uses, what its
reply must contain, and what it may change. A step that judges gives a verdict, and its
routes say where each verdict other than accept leads:

```python
Step("security_review", "agent", persona="reviewer", on_pass="finish", on_fail=Rework("security_review"),
     inputs=("request", "diff"),
     envelope={"verdict": "verdict", "reasons": "list", "ideals_broken": "list"},
     routes={"reject": End("rejected")}),
```

The prompt says what the step is for and what each key of its reply holds. The factory adds
the rest: the rules in order of precedence (for a step given the constitution and the
ideals), spec kit's instructions (for a step that follows a spec kit command), how to ask a
question, and the exact shape of the reply, written from the entry's `envelope`. These shared
parts are in `prompts/fragments/`.

Before a run uses a table, the factory checks it: every step it leads to exists, every check
is registered, every input is defined, every persona and prompt file exists, and every prompt
uses only its entry's inputs and explains each key of its reply. A mistake is found then, not
after paid steps have run.

Add `advisory=True` to an entry and the step's failure is recorded without stopping the run,
which is how the architect's review works.

An entry that says nothing gets the most restrictive values: the agent may read but not
edit, and may change nothing. The safety checks — the factory itself is untouched, nothing
changed outside what the entry allows, the reply is well-formed — are applied to every step
whatever its entry says. A new step cannot leave them out.

**Deleting a file.** An agent has no tool that deletes a file. A step that may change files is told it may list
files under `delete` in its reply; the factory deletes them after the step and judges each deletion like any other
change, against what the step may change (a builder may delete code, never a test; a test writer only tests). A path
outside the checkout, in git's own folder or among the factory's own files is refused, nothing is deleted, and the
step fails as a guard (`deletions_inside`). A deletion is committed with the step's work.

The inputs a prompt can use, written `{{name}}` in the prompt file: `request`, `run_kind`,
`ideals`, `constitution`, `plan`, `previous_plan`, `comment`, `test_paths`, `docs_paths`, `backlog_file`, `backlog_done_file`,
`test_files`, `failure`, `question`, `diff`, `test_output`, `run_facts`, `friction`, `operator_feedback`, `findings`, `run_name`, `red_output`, `planning_answers`, for a dialogue `round`,
`dialogue`, `draft`, `similar_runs`, `standing`, `to_merge` and `codebase_moved`, for the documenter `measured`
(what the factory measured of the tests, budget, smells and coverage, the only figures it may state; the retro is
given it too), for the architect `readability` (the functions the readability smell flagged, to judge), for the
test writer mending `defective_tests` (the tests the builder's reports named) and `failing_tests` (what the last
test run's report named as failing, with messages), for each step that writes code or tests `limits` (the
codebase's line length and test budget, to write within),
and for a spike `branch`, `probe_command`, `probe_output` and `spike_answer`. Each is one entry in `INPUTS` in
`factory/driver.py`; a new input is one entry there.

## Adding a persona

A persona is a Markdown file in `personas/` that says who is doing a step. It has exactly
three headings:

```markdown
# Careful coder

## Expertise
Who this is and what they are good at.

## Priorities
What they care about, in order.

## Must not
What they never do.
```

Name it on a step's entry — `persona="careful_coder"` — and that step is carried out by it.
Nothing else changes. One persona can serve several steps.

A persona's "must not" is guidance to the agent. What actually holds it to that is the
step's `may_change`, checked from git after the step. The wording is never the only safeguard.

To change how an existing step behaves, edit its persona (who) or its prompt (what). The
test writer's attention to edge cases, for example, is in `personas/test_writer.md`.

## Where the rules live

In two files. `factory/tables.py` holds the tables: which steps each kind of run goes
through, in what order. `factory/workflow.py` holds the rules: the vocabularies (outcomes,
the ways a step can fail, verdicts), what a step entry may say, and the small functions that
read entries: `next_step` and `after_wait`, and the rules for which checks a step gets, what
counts as a question, and how the agent program's reply went. Neither does any input or
output — no files, no database, no processes — so you can read the two top to bottom and know
everything the factory will decide.

The rest of the code carries those decisions out and decides nothing:

| File | Layer | What it is for |
|------|-------|----------------|
| `cli.py` | presentation | Parses commands and prints results. No rules. |
| `operations.py` | control | What you can do to a run, and when it is refused |
| `workflow.py` | control | **The rules** |
| `tables.py` | control | **The tables**: the steps of each kind of run |
| `driver.py` | control | Carries one run forward, a step at a time |
| `checks.py` | control | The checks applied to each step's result |
| `records.py` | control | The rules about what a run's record must say |
| `run_record.py` | control | A run's record as a document in the codebase: `docs/runs/`, from approval to its end |
| `dialogue.py` | control | A planning dialogue's rounds, the batch you answer, what it waits for, and its transcript |
| `agent.py` | effect | The only code that knows which agent program is used |
| `workspace.py` | effect | Git, and only this module runs it: the run's checkout, commits, undo |
| `own_files.py` | effect | Fingerprints, snapshots and restores the factory's own files |
| `sandbox.py` | effect | The only code that knows how the target's code is contained |
| `proc.py` | effect | Runs a child process with a time limit; stops process groups |
| `notify.py` | effect | The desktop notification |
| `speckit.py` | effect | The only code that knows spec kit's scripts |
| `store.py` | data | Everything the factory keeps, behind one gateway: insert, get, query, update, delete on any table |
| `config.py` | data | Where things are; the target's settings; your ideals |

Read them in this order: `tables.py`, `workflow.py`, `driver.py`, `checks.py`, `operations.py`, then the
rest as you need them.

## What this proof of concept does not protect you from

Be clear-eyed about these before pointing it at anything you care about.

- **Tests written by an agent run contained, but not in a virtual machine.** The factory runs
  every test command inside bubblewrap: the code sees its checkout, the system read-only and
  the factory's Python, and nothing else of yours — no home, no records, no keys, no
  environment variables, no docker socket, no network unless the codebase allows it, and
  nothing it starts outlives the step. A codebase's setup command is contained the same way
  but always has the network, so what it downloads and runs while installing can reach the
  internet and your local network; it still cannot see your home. It shares your kernel, has no system-call filter, and
  has no limit on CPU or memory beyond the step's time limit. If bubblewrap does not work,
  the factory refuses to run the tests at all. (Feature 002.)
- **The agent program itself is not contained by the factory.** It is confined by its own
  permission system: no shell, and reads and edits outside the checkout refused. Containing
  it too is phase 2.
- **Confinement depends on the agent program.** When this was built, the agent program
  refused both reads and edits outside the run's checkout. That was tested with direct
  requests, not against an agent determined to get round it, and a later version of the
  program may behave differently. The factory's own check that its code, personas, prompts
  and your ideals are unchanged does not depend on the agent program.
- **A wrong plan produces confidently wrong work.** The factory checks the work against the
  plan and the tests. If the plan is not what you meant, everything downstream can pass.
  Reading the plan is your part of the job.
- **Tests can be weak.** The test writer must state edge cases and its tests must fail
  first, but nothing proves the tests are the right ones.
- **One machine, one run at a time.** A run that ends as needs-me can be carried on with
  `factory resume`, which redoes only the step it stopped at.
- **The agent program's cost figures are estimates**, reported by the program itself.

## Testing the factory

```bash
uv run pytest                           # everything, on a fake agent; uses no subscription
uv run pytest -m live                   # the few tests that use the real agent and desktop
```

Collection refuses a test that names no requirement, and, when the whole suite is collected,
a requirement that no test names (constitution S8).

The full specification, plan and design decisions are in `specs/001-near-loop-factory/`.
