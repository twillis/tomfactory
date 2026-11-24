"""Presentation: the command line.

Each command parses its arguments, calls one operation, and prints what comes back.
There are no rules here: whether something is allowed, and what happens next, is decided
in operations.py and workflow.py. This file only turns the rows it is handed into text or JSON.
"""
import argparse
import dataclasses
import json
import sys
import time
from datetime import datetime, timezone

from factory import operations

PROG = "factory"


def main(argv) -> int:
    """Run one command. Returns 0 when it did what was asked, 1 when it refused, 2 for bad usage."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:      # argparse has already printed why
        return 2 if stop.code else 0
    try:
        return args.run(args) or 0
    except operations.Refused as reason:
        print(f"{PROG}: {reason}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROG, description="A small near-loop software factory.")
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")

    def command(name, run, help_text):
        sub = commands.add_parser(name, help=help_text, description=help_text)
        sub.set_defaults(run=run)
        return sub

    def with_run(sub):
        sub.add_argument("run_id", nargs="?", type=int, metavar="run", help="the run's number; default: the most recent")
        return sub

    sub = command("init-target", init_target, "Create a new target codebase with the default settings.")
    sub.add_argument("dir")
    sub.add_argument("--spec-kit", action="store_true", help="set spec kit up in it; plans become spec kit documents")

    sub = command("request", request, "Hand the factory a request. A plan is written, then the run waits for you.")
    sub.add_argument("text")
    sub.add_argument("--target", required=True, help="the codebase to change")
    sub.add_argument("--attempts", type=int, default=3, help="how many times any one step may run (default 3)")
    sub.add_argument("--kind", choices=operations.run_kinds(), default="change",
                     help="change (the default, tests first), or a tidy that must not alter behaviour:"
                          " tidy-tests holds the code still, tidy-code holds the tests still; or a spike,"
                          " a question answered by a throwaway probe")

    with_run(command("plan", plan, "Show the current plan.")).add_argument("--json", action="store_true")
    with_run(command("approve", approve, "Approve the waiting plan; the rest runs unattended."))
    with_run(command("abandon", abandon, "Give up on a request whose plan is waiting."))
    with_run(command("resume", resume, "Carry on a run that stopped as needs-me, from the step it stopped at."))
    with_run(command("stop", stop, "Stop a run that is being worked; nothing it started is left running."))

    sub = command("revise", revise, "Send the waiting plan back with a comment.")
    sub.add_argument("words", nargs="+", metavar="[run] comment")

    sub = command("answer", answer, "Answer the question a run is waiting on.")
    sub.add_argument("words", nargs="+", metavar="[run] answer")

    command("status", status, "What each recent run is doing, one line per run.").add_argument("--json", action="store_true")
    sub = with_run(command("show", show, "A whole run: every step, what it was asked and what it produced."))
    sub.add_argument("--step", type=int, metavar="id", help="show one step record in full")
    sub.add_argument("--json", action="store_true")
    with_run(command("watch", watch, "Follow a run as it happens, until it waits for you or ends."))
    command("ideals", ideals, "Show the ideals every run is held to.").add_argument("--edit", action="store_true")
    command("doctor", doctor, "Check that everything the factory needs is installed and working.")
    sub = command("table", table, "The steps a run would go through, with this codebase's overrides.")
    sub.add_argument("--target", required=True, help="the codebase")
    sub.add_argument("--kind", choices=operations.run_kinds(), default="change")

    sub = commands.add_parser("_drive")     # what the detached driver process runs; not for people
    sub.add_argument("run_id", type=int)
    sub.set_defaults(run=lambda args: operations.drive(args.run_id))
    return parser


# ---- one function per command: call the operation, print the result ----

def table(args):
    for step in operations.table(args.target, args.kind):
        model = f"model {step.model}" if step.kind == "agent" else "code"
        extras = [f"timeout {step.timeout}s" if step.timeout else "",
                  f"checks {', '.join(step.checks)}" if step.checks else "",
                  f"smells {', '.join(step.smells)}" if step.smells else "",
                  *[f"{verdict} -> {route.step} at most {route.at_most}" for verdict, route in step.routes.items()
                    if getattr(route, "at_most", None)]]
        print(f"{step.name:<22} {model:<16} " + "; ".join(e for e in extras if e))


def init_target(args):
    path = operations.init_target(args.dir, spec_kit=args.spec_kit)
    print(f"Created a new target codebase at {path}" + (", with spec kit set up." if args.spec_kit else "."))


def request(args):
    run = operations.request(args.text, args.target, attempts=args.attempts, run_kind=args.kind)
    print(f"Run {run.id} started: a plan is being written. You will be notified when it is ready.")
    print(f"  then read it with:  {PROG} plan")


def plan(args):
    current = operations.plan(args.run_id)
    if args.json:
        return print_json(current)
    print(f"Run {current.run_id}, plan version {current.version} ({current.decision})\n")
    print(current.text.rstrip())
    print_list("\nHow it follows your ideals:", current.ideals_addressed)
    print_list("\nConflicts with your ideals:", current.conflicts)
    if current.decision == "pending":
        print(f"\nNext:  {PROG} approve   |   {PROG} revise \"<comment>\"   |   {PROG} abandon")


def approve(args):
    run = operations.approve(args.run_id)
    print(f"Run {run.id} approved. It now runs unattended; you will be notified when it has finished.")


def run_and_text(words) -> tuple[int | None, str]:
    """`[run] words`: a leading number is the run, when more words follow it."""
    if len(words) > 1 and words[0].isdigit():
        return int(words[0]), " ".join(words[1:])
    return None, " ".join(words)


def ended(run) -> str:
    return f"Run {run.id} ended: {run.outcome} — {run.reason}"


def revise(args):
    run = operations.revise(*run_and_text(args.words))
    print(f"Run {run.id}: the plan was sent back. You will be notified when the new version is ready.")


def answer(args):
    run = operations.answer(*run_and_text(args.words))
    print(f"Run {run.id}: answered. It carries on; you will be notified when it next needs you or has finished.")


def abandon(args):
    run = operations.abandon(args.run_id)
    print(ended(run))




def resume(args):
    run = operations.resume(args.run_id)
    if run.state == "ended":
        print(ended(run))
    else:
        print(f"Run {run.id} resumed at {run.current_step}. You will be notified when it next needs you or has finished.")

def stop(args):
    run = operations.stop(args.run_id)
    print(ended(run))

def status(args):
    views = operations.status()
    if args.json:
        return print_json(views)
    for view in views:
        run, last = view.run, (view.steps[-1] if view.steps else None)
        waiting = [q.question for q in view.questions if q.answer is None]
        if waiting:        # a measurement is for whoever drives the run; any other question is the operator's
            measure = last and any(check["name"] == "measure" for check in last.checks or [])
            doing = "a measurement is asked for" if measure else "a question for you"
        elif run.state == "ended":
            doing = run.outcome
        elif last and last.ended_at is None:
            doing = f"{run.state}: {last.name}, {elapsed(last.started_at)}"
        else:
            doing = run.state.replace("_", " ")
        print(f"{run.id:>4}  {doing:34}  {words(run.request, 9)}")


def show(args):
    view = operations.show(args.run_id, step=args.step)
    if args.json:
        return print_json(view)
    if args.step is not None:
        return show_step(view)
    run = view.run
    print(f"Run {run.id}: {run.outcome or run.state.replace('_', ' ')}" + (f" — {run.reason}" if run.reason else ""))
    print(f"  request: {run.request}")
    print(f"  target: {run.target}")
    print(f"  branch: {run.branch}")
    print(f"  attempt limit: {run.attempt_limit}")
    print(f"  ideals: {'as stated when the run began (below)' if run.ideals else 'none stated'}")
    if run.ideals:
        print("    " + run.ideals.strip().replace("\n", "\n    "))
    for plan_version in view.plans:
        print(f"\n  plan version {plan_version.version} ({plan_version.decision})"
              + (f" — sent back with: {plan_version.comment}" if plan_version.comment else ""))
    print(f"\n  {'id':>4}  {'step':12} {'by':12} {'try':>3}  {'took':>6}  result")
    for step in view.steps:
        result = "running" if step.passed is None else ("passed" if step.passed else f"failed ({step.failure})")
        print(f"  {step.id:>4}  {step.name:12} {step.persona or 'code':12} {step.attempt:>3}  "
              f"{duration(step):>6}  {result}")
        for check in step.checks or []:
            mark = "ok" if check["passed"] else "FAILED"
            note = "" if check["passed"] else f": {first_line(check['note'])}"
            print(f"          {mark:6} {check['name']}{note}")
    for asked in view.questions:
        print(f"\n  {asked.asked_by} asked, at {asked.step}: {asked.question}")
        print(f"    {asked.answered_by + ' answered: ' + asked.answer if asked.answer else 'not yet answered'}")
    print(f"\nOne step in full:  {PROG} show --step <id>")


def show_step(view):
    step = view.steps[0]
    print(f"Run {view.run.id}, step {step.id}: {step.name}, attempt {step.attempt}, "
          f"by {step.persona or 'code'}, took {duration(step)}")
    if step.tokens:
        cost = f", estimated ${step.cost_estimate:.2f}" if step.cost_estimate else ""
        print(f"  tokens in {step.tokens.get('input')}, out {step.tokens.get('output')}{cost}")
    print("\n--- what it was asked ---\n" + (step.asked.rstrip() or "(nothing: a code step)"))
    print("\n--- what it produced ---\n" + json.dumps(step.produced, indent=2))
    print("\n--- checks ---")
    for check in step.checks or []:
        print(f"{'ok' if check['passed'] else 'FAILED':6} {check['name']}")
        if check["note"]:
            print("       " + check["note"].rstrip().replace("\n", "\n       "))
    print("\n--- what happened ---")
    for event in view.events:
        print(event_line(event))


def watch(args):
    run, seen = operations.get_run(args.run_id), 0
    while True:
        for event in operations.follow(run.id, after=seen):
            print(event_line(event), flush=True)
            seen = event.id
        run = operations.get_run(run.id)
        if run.state in ("awaiting_approval", "ended") and not operations.follow(run.id, after=seen):
            break
        time.sleep(1)
    if run.state == "ended":
        print(ended(run))
    else:
        print(f"Run {run.id} is waiting for you:  {PROG} plan")


def ideals(args):
    if args.edit:
        operations.edit_ideals()
    path, text = operations.ideals()
    print(f"Your ideals are kept in {path}\n")
    print(text.rstrip() or "(none stated yet; add some with:  factory ideals --edit)")


def doctor(args):
    found = operations.doctor()
    for item in found:
        print(f"{'ok' if item.ok else 'MISSING':8} {item.name:13} {item.detail}")
    return 0 if all(item.ok for item in found) else 1


# ---- rendering ----

def words(text, count):
    parts = text.split()
    return " ".join(parts[:count]) + (" …" if len(parts) > count else "")


def first_line(text):
    lines = [line for line in (text or "").strip().splitlines() if line.strip()]
    return lines[-1][:140] if lines else ""


def moment(stamp):
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def seconds(amount):
    return f"{amount:.0f}s" if amount < 100 else f"{amount / 60:.1f}m"


def duration(step):
    return seconds((moment(step.ended_at) - moment(step.started_at)).total_seconds()) if step.ended_at else "…"


def elapsed(stamp):
    return seconds((datetime.now(timezone.utc) - moment(stamp)).total_seconds())


def event_line(event):
    return f"{event.at[11:19]}  {event.kind:11} {event.summary}"



def print_list(heading, items):
    if items:
        print(heading)
        for item in items:
            print(f"  - {item}")


def print_json(record):
    def plain(item):
        return dataclasses.asdict(item) if dataclasses.is_dataclass(item) else item

    data = [plain(item) for item in record] if isinstance(record, list) else plain(record)
    print(json.dumps(data, indent=2))
