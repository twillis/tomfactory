# tomfactory

A small software factory you run on your own machine, so you can work *near* the loop
instead of *in* it.

You hand it a short written request for a change to a codebase. It writes a plan and stops.
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

About 3,500 lines of Python, 418 tests, standard library plus pytest. What is next is in
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
| 4 | `red` | code | Runs the tests. They must **fail** | nothing |
| 5 | `build` | agent: code writer | Makes the tests pass | anything except tests |
| 6 | `test` | code | Runs the tests. They must **pass** | nothing |
| 7 | `architecture_review` | agent: architect | Reviews the change for maintainability; adds suggestions and warnings to a backlog. **Advisory**: it never fails the run | documentation only |
| 8 | `document` | agent: documenter | Writes an account of what changed | documentation only |
| 9 | `review` | agent: reviewer | Judges the whole result against the request, the plan and your ideals | nothing |
| 10 | `finish` | code | Ends the run as accepted | nothing |

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
attempt. Now the builder says so, with the verdict `test_defect`, and the `mend_tests` step asks
the test writer, once, to correct that test and nothing else; the tests are then run again. It
goes on to `test`, not back to `red`, because the build is already there. The test writer may
find the builder wrong and change nothing. A second report in the same run is not chased: the
tests are run and their failure takes its usual course.

No step runs more than three times in one run (you can change the number per request).
When a step has used its attempts, the run ends as **needs-me** and tells you what failed.

### How a run ends

Every run ends in exactly one of three outcomes, with a reason you can read:

- **accepted** — the tests pass and the review found the result matches the request, the
  plan and your ideals. The work is on a branch, waiting for you to merge it.
- **rejected** — the review found a mismatch, or you abandoned the request.
- **needs-me** — the factory could not finish on its own.

### Where the work goes

Each run works in its own checkout of the target codebase, on its own branch
(`factory/<when it was requested>-<first words of the request>`, for example
`factory/20261119-145203-add-a-greeting`). Your own working copy is never touched. An
accepted run leaves up to six commits on its branch: the plan you approved, the tests, the
change, the architect's backlog notes if it had any, the documentation, and the run's record.
The record is one file under `docs/runs/`, with the branch's own name. Neither is named by the
run's number, which is counted on your machine alone, so two people working on one codebase do
not collide. It is written when you approve the
plan (the request, anything you sent it back with, the plan) and completed when the run ends,
whatever the outcome (every step, the outcome and why, the review, the commits), so the reason
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
uv sync                             # pytest, for the factory's own tests; the factory itself needs nothing else
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

Add `--kind tidy-tests` or `--kind tidy-code` for a change that must not alter behaviour; see below.

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
That is the way through when the test writer's one chance to mend a test (`mend_tests`, above) did
not settle it.

Every command that takes a run works on the most recent run unless you give its number:
`factory show 3`. `factory plan`, `factory status` and `factory show` take `--json`.

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
architect's, and never stops a run. Its inputs are `run_facts`, `friction`,
`operator_feedback`, `findings` and `run_name`.

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

A sprint is: `plan` (the planner reads the codebase's standing documents and writes one plan),
`check_plan` (a reviewer reads the plan for contradictions, missed rulings, wrong claims and
untested refusals; its findings are shown beneath the plan, and it is never a gate), your one
approval, then the build, the tests, the architect, the documenter, `converge` (the
final review: unbuilt work goes back to the build once, everything else is recorded), `retro`
and `finish`. No spec kit stage runs. The planner and the plan check are told where each later
step may write, so a plan gives no step a file it may not touch; the diff the architect and the
final review are given leaves out the run's own record, which repeats the plan they already
have; and the retro is given the constitution and the ideals, so it can say which rule a run
missed. The record ends with the sprint review, what the new
tests said before the build and the tests after it, the time and cost, and the retro. `cycle = "auto"`, the default, picks spec kit where
it is set up and the plain cycle elsewhere.

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
default. A step's entry names a grade, and there are two:

- **strongest**, for the steps that judge a change: the architect's review, and the final
  review (`review`, or `converge` on a spec kit codebase).
- **standard**, for everything else: planning, writing tests, building, documenting.

Which model each grade is, is written in one place, `MODELS` in `agent.py`. To give a step
the other grade, set `model=` in its entry in `tables.py`.

### Tests that cannot be read are not failing tests

Before the new tests are run to see them fail, the factory runs the codebase's
`tests_readable_command` (by default `python -m compileall -q tests`), contained. A test file
with a syntax error fails every time whatever is built, and the builder may not touch tests,
so without this check it would use up its attempts on tests that can never run. When the
command fails, the work goes back to the test writer with what it said. Set it to `""` to
switch it off, or to your own language's equivalent.

### Keeping tests proportionate

Left alone, a test writer told to cover edge cases will keep finding more. Two things hold
it back. Its persona tells it to test each behaviour once, at the level where it lives. And
each codebase sets a budget, `test_budget_lines` in `.factory.toml` (300 by default; 0 for
no limit): a run whose new tests add more lines than that is sent back and told the numbers.

### A longest line, if the codebase wants one

```toml
line_length = 120       # the longest line a step may add to code or tests; 0, the default, is no limit
```

Where it is set, the factory measures the lines each writing step added (the test writer, the
builder, a mended test), counting indentation, and sends the work back to that step with each
line that is over, as `file:line (length)`. Lines already there are not measured, and
documentation is not: prose and tables run long. It is measured by code, before the tests are
run, so a width nobody checked is not discovered by the final review after everything else has
passed.

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

What was asked and answered travels with the run. The plan check and the final review are given
every answered question, with who asked and who answered, and are told that where the request
and an answer disagree, the answer stands: the request was written first.

A run cannot be approved past a question that is still waiting. Every question, who asked
it, the answer and who answered are kept with the run and shown by `factory show`. An agent
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
read.

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

The inputs a prompt can use, written `{{name}}` in the prompt file: `request`, `run_kind`,
`ideals`, `constitution`, `plan`, `previous_plan`, `comment`, `test_paths`, `docs_paths`,
`test_files`, `failure`, `question`, `diff`, `test_output`, `run_facts`, `friction`, `operator_feedback`, `findings`, `run_name`, `red_output`, `planning_answers`. Each is one entry in `INPUTS` in
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
