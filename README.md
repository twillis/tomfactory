# tomfactory

A small software factory you run on your own machine, so you can work *near* the loop
instead of *in* it.

You hand it a short written request for a change to a codebase. It writes a plan and stops.
You read the plan and approve it, or send it back with a comment. Once you approve, it does
the rest on its own — writes failing tests, builds until they pass, has an architect look
it over, documents the change, reviews the whole result — and notifies you when it has finished. You are not needed in between.

This is a proof of concept. It is meant to be read, used, and changed.

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

Seven rules, applied in this order:

1. The step changed something it may not → the change is undone, the run ends, **needs-me**.
2. The step is advisory and failed in any other way → the failure is recorded and the run carries on.
3. The step ran past its time limit → **needs-me**.
4. The agent program failed, or refused to let the agent work in its own checkout → **needs-me**.
5. An agent's reply did not end with the JSON it was asked for → that step runs again.
6. One of the step's own checks failed → what the step's entry says. Failing tests send the
   work back to `build`. Tests that do not fail first send it back to `write_tests`. A review
   that rejects ends the run, **rejected**.
7. Everything passed → the next step.

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
(`factory/<run>-<first words of the request>`). Your own working copy is never touched. An
accepted run leaves up to four commits on its branch: the tests, the change, the architect's
backlog notes if it had any, and the documentation. **You merge the branch yourself.** The factory never merges.

## Using the factory

Commands are run from this folder as `uv run python -m factory <command>`. Below they are
written `factory <command>` for short; an alias makes that literal:

```bash
alias factory='uv run --project ~/projects/2026_projects/src/tomfactory python -m factory'
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

This returns at once. A plan is written in the background, and a desktop notification tells
you when it is ready.

```bash
factory plan                        # read the plan
factory approve                     # go ahead: the rest is unattended
factory revise "Also show the time."    # or: send it back with a comment
factory abandon                     # or: give up on the request
```

After `factory approve` you are not needed until the notification that the run has ended.

```bash
factory status                      # what is it doing now?
factory watch                       # follow it as it happens
factory show                        # the whole run: every step, what it was asked, what it produced
factory show --step 12              # one step in full, with everything the agent did
factory stop                        # stop a run; nothing it started is left running
```

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
it. From then on the planner follows that codebase's own `/speckit-specify` and
`/speckit-plan` instructions, and the plan you approve is real spec kit documents on the
run's branch: `specs/<NNN-name>/spec.md` and `plan.md`. `factory plan` gives a summary and
names them. Sending a plan back revises the same documents.

**Whose rules win.** Where they disagree, the order is: the codebase's own constitution
(`.specify/memory/constitution.md` in it) first, then your ideals, then spec kit's generic
instructions. Agents are given all three and told that order. A codebase whose constitution
is still spec kit's blank template is treated as having none, so your ideals are the rules.

No agent runs anything to do this. Spec kit's scripts are run by the factory's own code,
and the planner is handed the instructions and what the scripts set up. The planner may
write under `specs/` and nowhere else. A codebase without spec kit runs exactly as before.

So far only the planner uses spec kit. The reviewer with `/speckit-analyze`, and the test
writer and code writer with `/speckit-implement`, are designed but not built
(`specs/001-near-loop-factory/changes/2026-11-18-speckit-steps.md`).

### The architect and the backlog

After the tests pass, the architect reviews the change for how well it will bear being
maintained: repeated code, blurred boundaries, the wrong tool for the job. It is written to
think like a Lisp programmer — someone who knows every paradigm as a tool with strengths and
weaknesses. It does not change code and it cannot fail the run. What it finds is added, one
line each, to `docs/backlog.md` in the target codebase, and recorded on the run
(`factory show --step <id>` for the `architecture_review` step).

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

A step is one entry in the table in `factory/workflow.py`.

**A code step** is a check. Say you want to refuse any change that adds a file over 500
lines. Write the check in `factory/checks.py`:

```python
@register("no_huge_files")
def no_huge_files(ctx) -> CheckResult:
    huge = [name for name in ctx.checkout.files_changed_since_base()
            if len((ctx.checkout.path / name).read_text().splitlines()) > 500]
    return CheckResult("no_huge_files", not huge, f"over 500 lines: {', '.join(huge)}")
```

Then add its entry to `STEPS` in `factory/workflow.py`, after `test`, and point `test` at it:

```python
Step("test", "code", on_pass="no_huge_files", checks=("tests_pass",), on_fail=Rework("build"),
     commit_after=True),

Step("no_huge_files", "code", on_pass="document", checks=("no_huge_files",), on_fail=Rework("build")),
```

That is the whole change. The driver, the store and the command line are not touched: the
new step is run, recorded and shown like any other.

**An agent step** needs two more things: a prompt at `prompts/<step name>.md`, and a persona
(an existing one, or a new file). In its entry you say which inputs its prompt uses, what its
reply must contain, and what it may change:

```python
Step("security_review", "agent", persona="reviewer", on_pass="finish",
     inputs=("request", "diff"),
     envelope={"verdict": "verdict", "reasons": "list", "ideals_broken": "list"},
     checks=("verdict_accept",), on_fail=End("rejected")),
```

Add `advisory=True` to an entry and the step's failure is recorded without stopping the run,
which is how the architect's review works.

An entry that says nothing gets the most restrictive values: the agent may read but not
edit, and may change nothing. The safety checks — the factory itself is untouched, nothing
changed outside what the entry allows, the reply is well-formed — are applied to every step
whatever its entry says. A new step cannot leave them out.

The inputs a prompt can use, written `{{name}}` in the prompt file: `request`, `ideals`,
`plan`, `constitution`, `previous_plan`, `comment`, `test_paths`, `docs_paths`, `test_files`, `failure`,
`diff`, `test_output`.

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

In one file: `factory/workflow.py`. It holds the table of steps and two small functions,
`next_step` and `after_wait`, that read it. It does no input or output — no files, no
database, no processes — so you can read it top to bottom and know everything the factory
will decide.

The rest of the code carries those decisions out and decides nothing:

| File | Layer | What it is for |
|------|-------|----------------|
| `cli.py` | presentation | Parses commands and prints results. No rules. |
| `operations.py` | control | What you can do to a run, and when it is refused |
| `workflow.py` | control | **The rules** |
| `driver.py` | control | Carries one run forward, a step at a time |
| `checks.py` | control | The checks applied to each step's result |
| `records.py` | control | The rules about what a run's record must say |
| `agent.py` | effect | The only code that knows which agent program is used |
| `workspace.py` | effect | Git: the run's checkout, commits, undo |
| `proc.py` | effect | Runs a child process with a time limit; stops process groups |
| `notify.py` | effect | The desktop notification |
| `speckit.py` | effect | The only code that knows spec kit's scripts |
| `store.py` | data | Everything the factory keeps, behind one gateway: insert, get, query, update, delete on any table |
| `config.py` | data | Where things are; the target's settings; your ideals |

Read them in this order: `workflow.py`, `driver.py`, `checks.py`, `operations.py`, then the
rest as you need them.

## What this proof of concept does not protect you from

Be clear-eyed about these before pointing it at anything you care about.

- **Tests written by an agent are run on your machine with your permissions.** The agents
  themselves have no shell and cannot write outside their checkout. But the test command
  executes the tests and the code that agents wrote, and nothing limits what that code does
  when it runs. There is no sandbox. This is the main thing the next stage has to add.
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
- **One machine, one run at a time, no resuming.** A run that ends as needs-me is not
  continued; you make a new request.
- **The agent program's cost figures are estimates**, reported by the program itself.

## Testing the factory

```bash
uv run pytest                           # everything, on a fake agent; uses no subscription
uv run pytest -m live                   # the few tests that use the real agent and desktop
uv run python scripts/traceability.py   # every requirement in the spec is named by a test
```

The full specification, plan and design decisions are in `specs/001-near-loop-factory/`.
