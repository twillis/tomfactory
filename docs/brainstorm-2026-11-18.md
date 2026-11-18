# Software factory — brainstorm and spec input

Date: 2026-11-18. Status: approved by Tom; Part 1 was handed to `/speckit-specify`.

## Decisions

- Repo name: `tomfactory`
- Repo location: `src/tomfactory`, its own nested repo
- Tom's two additions (test-driven full cycle; stated ideals) were reworded into
  Part 1. His design-ideals note is `thoughts/2026-11-10-software-design-ideals.md`.

---

## Part 1 — Input for `/speckit-specify`

This is the text I will hand to spec kit. It says what and why only. Edit freely.

```text
A small software factory I can run on my own machine, so I can work near the
loop instead of in it.

Near the loop means this: I hand the factory a short written request for a
change to a codebase. It writes a plan and stops. I read the plan and either
approve it or send it back with a comment. Once I approve, it does the rest
unattended and notifies me when the run is finished. I then review the result.
I am not needed between approving the plan and the notification.

After approval it runs a full development cycle, test first. It writes tests
that describe the change and confirms they fail. It builds the change until
those tests and the project's existing tests pass. It reviews the result
against the request, the approved plan and my stated ideals. It documents what
it changed. Running tests is done by ordinary code, not by an agent. A failed
test run sends the failure back to the build step, up to a fixed number of
attempts; after that the run stops and reports why. A run ends as accepted,
rejected, or needs-me, and I can always tell which and why.

I can state ideals for the factory to adhere to, once, in my own words, and
every run is held to them: the plan must follow them, and the review checks the
result against them and names any ideal it found broken. An example ideal:
well-defined layers with explicit interfaces between them, so the system can
absorb change over time. The ideals are mine to edit, and changing them needs
no change to the factory itself.

Every step of every run is recorded as it happens, so I can see what a run is
doing now and read back what a finished run did: which step, what it was asked,
what it produced, how long it took, and whether its check passed.

The first thing the factory builds is its own observability app: a way to look
at those recorded runs. The bare minimum that proves the cycle works is a
hello-world version of that app, produced end to end by the factory from a
written request. The app then grows into a real tool through further requests,
each one going through the same cycle.

This is a proof of concept. Its purpose is for me to see it work, understand
how it works, and learn how to use and extend it. It must stay small enough to
read in one sitting, and adding a new step or a new workflow must be an obvious,
documented change.

It runs on my Claude subscription. Nothing in it should assume one way of
paying or one model, because the next stage adds both choices.

Next, if this proof of concept succeeds (not part of this effort):
- working with an API key as well as the subscription
- choosing which model each step uses
- running several requests at once
- isolation or sandboxing beyond a separate branch
- scheduled or triggered runs
- models from other vendors
- using spec kit's own steps (specify, plan, tasks, converge) as the cycle
```

---

## Part 2 — Notes for `/speckit-plan` (how, not what)

These are kept out of the spec on purpose. They are the technical findings from
the brainstorm, for the plan step to pick up.

### Choices made so far

- Language: Python scripts for now.
- Agent: the official `claude` command, run non-interactively, on the Claude
  subscription.
- A plain script owns the order of steps and decides what happens next. Agents
  only plan, build and review. Tests and other known commands run as code.
  ("Agents propose, code disposes.")
- One small adapter is the only code that knows how to launch an agent. The rest
  of the factory asks it to "run this prompt with this model and give back the
  result and the event stream". This is what lets API keys, model choice and
  other agents be added later without touching the workflows.

### Process handling (Tom has found this tricky in Python before)

Three requirements on the adapter, each fixing a known failure:

- Read the agent's output continuously, line by line, so it cannot stall on a
  full output buffer. The recording needs this stream anyway.
- Start each agent in its own process group and stop the whole group, so
  stopping a run never leaves an agent running.
- Give every step a time limit, so a stuck agent cannot block a run forever.

The proof of concept runs one agent at a time and waits for it, which is the
easy case.

### Recording and the observability app

- Prior art records every event into a SQLite file as it happens, and the viewer
  polls that file with one query ("events after the last one I saw"). Live view
  and history are the same query.
- Under subscription login the agent often does not report dollar cost. Expect
  time and tokens per step; the cost column stays empty until an API key is used.

### Plan approval and notification

- Approval is a parked state after the plan step: the run waits, and a command
  approves it or sends it back with a comment that the planner sees.
- Notification can start as a desktop notification on this machine. Anything
  that reaches a phone is a later choice.

### Things to settle in the plan

- Where the observability app lives relative to the factory's own code. If both
  are in one repo, the build agent must not be able to change the factory while
  the factory is running it.
- What each unattended step is allowed to do, decided up front, because an
  unattended agent cannot stop to ask. Prior art (SSSF) compares the repo before
  and after each step and rolls back changes the step was not allowed to make.
- What the test step runs before the app has any tests.

### Prior art looked at

- `disler/super-simple-software-factory` (IndyDevDan, MIT): Python workflow
  scripts, typed handoff notes between agents, code checks after each step,
  SQLite trace plus a read-only web viewer. Built on the Pi agent; has a file
  named `agent_cc.py` that suggests a Claude Code adapter (not read).
- `stratonext/software-factory` (`sf`, MIT, v0.0.3): YAML pipelines, pass / fail
  / human verdicts, counted rework with a limit, one git worktree per request,
  agent definitions as small adapter files. Runs agents with permissions
  bypassed.
- IndyDevDan videos: "My Super Simple Software Factory" (Aug 2026) for the
  mechanics; "Tiny Software Factories" (Nov 2026) for the in-loop versus
  near-loop framing.
