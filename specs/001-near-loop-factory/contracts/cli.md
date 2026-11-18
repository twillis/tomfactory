# Contract: Commands

The operator uses the factory through one command, written `factory` in the tables below and run as `uv run python -m factory …` from the factory's repository. Each command calls one operation in `factory/operations.py`, which returns plain data; `cli.py` only turns that data into text. Every command prints plain text for a person. `--json` on `plan`, `status` and `show` prints the same information as JSON.

The factory's home directory is `~/.tomfactory` unless `TOMFACTORY_HOME` is set. It holds `factory.db`, `ideals.md`, a folder per run with logs, raw event files and a snapshot, and each run's checkout under `workspaces/`.

## Commands that start or steer a run

| Command | What it does | Returns |
|---------|--------------|---------|
| `factory init-target <dir>` | Creates a git repository at `<dir>` with a default `.factory.toml` and one commit. Refuses if `<dir>` already has content. | At once |
| `factory request "<text>" --target <dir> [--attempts N]` | Creates a run, creates its checkout, starts the plan step in the background. `--attempts` sets how many times any one step may run (default 3). Refuses if another run has not ended (FR-033), if `<dir>` is not a git repository with a committed `.factory.toml`, or if the text is empty. | At once, printing the run id |
| `factory plan [<run>]` | Prints the current plan, how it addresses the ideals, and any conflicts. | At once |
| `factory approve [<run>]` | Approves the waiting plan and starts the unattended cycle in the background. Refuses unless the run is awaiting approval. | At once |
| `factory revise [<run>] "<comment>"` | Sends the plan back with a comment and starts a new plan step in the background. | At once |
| `factory abandon [<run>]` | Ends a run that is awaiting approval as rejected, reason "abandoned by operator", and removes its checkout. | At once |
| `factory stop [<run>]` | Stops a run that is `planning` or `working`: ends every process it started, ends the run as needs-me, reason "stopped by operator". | When everything has stopped |

`<run>` is optional everywhere; without it the command applies to the most recent run.

## Commands that read

| Command | What it shows |
|---------|---------------|
| `factory status` | One line per recent run: id, state or outcome, current step and how long it has been running, the first words of the request. Answers "what is it doing now" (SC-005). |
| `factory show [<run>]` | The whole run: request, plan versions with comments, every step attempt in order with the persona that carried it out, what it was asked, what it produced, duration and check result, then outcome and reason (FR-026, FR-028). `--step <id>` prints one step record in full, by the id shown in the listing. The listing includes the attempt limit and the ideals in effect. |
| `factory watch [<run>]` | Prints events as they are recorded until the run waits or ends. |
| `factory ideals` | Prints the path of `ideals.md` and its current text. `--edit` opens it in `$EDITOR`. |
| `factory doctor` | Checks that git, the agent command and the notification command are available, that the agent command can answer a one-line prompt, and that the home directory is writable. |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | The command did what was asked |
| 1 | The command refused, and printed why (for example "run 4 is still in progress") |
| 2 | The command was used wrongly (bad arguments) |

## Notifications

Two desktop notifications are sent, each also recorded as an event:

- **Waiting for you**: "Run 7: plan ready — waiting for you" plus the first words of the request.
- **Run ended**: "Run 7: accepted" (or rejected / needs-me) plus the reason. Sent for every ending, including a stop and an interrupted run.

## What the operator does with a finished run

An accepted run leaves its changes on the branch named in `factory show`. The operator merges that branch into the target codebase by hand. The factory never merges (spec Assumptions).
