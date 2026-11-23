"""Control: a run's record, as a document in the codebase it worked on (FR-079, FR-080).

Written to the run's branch when its plan is approved, and completed when the run ends,
so the reason for a change, and how it was made, travel with the code. The record is
rendered from the factory's own records of the run; this module decides nothing.
"""
import datetime
import re


# What each step's commit holds, by the step that wrote it (FR-103). A step not named here is named by itself.
LABELS = {"plan": "Plan", "specify": "Specification", "clarify": "Specification", "tasks": "Tasks",
          "write_tests": "Tests", "mend_tests": "Tests mended", "build": "Build", "tidy_code": "Tidy",
          "tidy_tests": "Tidy tests", "architecture_review": "Backlog", "document": "Docs", "retro": "Retro"}
SUBJECT_LENGTH = 72     # what git log --oneline and most tools show in full
OUTCOMES = {"accepted": "Accepted", "rejected": "Rejected", "needs-me": "Needs me"}   # the record's subject begins so


def step_message(store, run, step, envelope) -> str:
    """The message for the commit after `step`: what it holds, in the words of the agent that wrote it. A code
    step commits what the last agent wrote (the test writer's tests at `red`, the builder's code at `test`)."""
    writer, summary = step.name, (envelope or {}).get("summary") if isinstance(envelope, dict) else None
    if step.kind == "code":
        wrote = [s for s in store.query("steps", {"run_id": run.id}) if s.kind == "agent" and s.ended_at
                 and s.failure in (None, "check") and s.name != "answer_question"]
        if wrote:
            writer = wrote[-1].name
            first = wrote[-1]
            for earlier in reversed(wrote):         # a step sent back is named by what it first did, not its fix
                if earlier.name != writer:
                    break
                first = earlier
            summary = (first.produced or {}).get("summary") if isinstance(first.produced, dict) else None
    label = LABELS.get(writer, writer)
    subject = f"{label}: {summary}" if summary else label
    return _message(run, step.name, subject)


def approved_message(store, run) -> str:
    """The message for the commit of the approved plan: the plan, by its title."""
    return _message(run, "plan", f"Plan: {title(store, run)}")


def resumed_message(run) -> str:
    return _message(run, run.current_step, f"Resumed at {run.current_step}")


def coverage_line(steps) -> str | None:
    """Coverage before the run and after it, where the codebase measures it (FR-110): the first a step measured,
    before anything changed, and the last a passing step measured."""
    found = [c["measured"] for s in steps if s.passed for c in s.checks or [] if c.get("measured")]
    before, after = (found[0], found[-1]) if len(found) > 1 else (None, found[-1] if found else None)
    if not after:
        return None
    if not before:
        return f"Coverage: {after['coverage']}% after."
    return (f"Coverage: {before['coverage']}% before, {after['coverage']}% after "
            f"({after['coverage'] - before['coverage']:+.1f}).")


def ended_message(store, run) -> str:
    """The message for the commit of the run's finished record: the run in brief, its outcome and why, what the
    review said, and what it cost."""
    steps = [s for s in store.query("steps", {"run_id": run.id}) if s.ended_at]
    judged = next((s.produced for s in reversed(steps) if s.persona == "reviewer"
                   and isinstance(s.produced, dict) and "verdict" in s.produced), None)
    brief = [run.reason or ""]
    if judged:
        brief += ["", f"The review: {judged['verdict']}", *[f"- {reason}" for reason in judged.get("reasons", [])]]
    totals = [line for line in facts(store, run) if line.startswith("Total:")]
    covered = coverage_line(steps)
    brief += ["", *totals, *([covered] if covered else [])]
    outcome = OUTCOMES.get(run.outcome, run.outcome)
    return _message(run, run.current_step, f"{outcome}: {title(store, run)}", brief)


def title(store, run) -> str:
    """What the run is about, in a line: the approved plan's heading or first line, else the request's first line."""
    approved = [p for p in store.query("plans", {"run_id": run.id}) if p.decision == "approved"]
    text = approved[-1].text if approved else run.request
    first = next((line for line in text.splitlines() if line.strip()), run.request)
    first = first.strip().lstrip("#").strip().strip("*_").strip()     # a heading, or a line in bold
    return re.sub(r"^Plan( for [^:]*)?:\s*", "", first) or first


def _message(run, step_name, subject, body=()) -> str:
    request = next((line for line in run.request.splitlines() if line.strip()), "")
    lines = [_shorten(subject, SUBJECT_LENGTH), "", *body]
    if body:
        lines.append("")
    lines += [f"Run {run.id}: {_shorten(request, 200)}", "", f"Factory-Run: {run.id}", f"Factory-Step: {step_name}"]
    return "\n".join(lines)


def _shorten(text, limit) -> str:
    """`text` on one line, cut at a word to at most `limit` characters, with an ellipsis where it was cut."""
    one_line = " ".join(text.split())
    if len(one_line) <= limit:
        return one_line
    cut = one_line[:limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


def name(run) -> str:
    """Where the record lives in the codebase: under the run's branch's own name, which no other machine shares."""
    return f"docs/runs/{run.branch.removeprefix('factory/')}.md"


def write(store, run, checkout, message) -> None:
    """Write the record as it stands now, and commit that file alone."""
    file = checkout.path / name(run)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(render(store, run, checkout))
    checkout.commit_only(name(run), message)


def render(store, run, checkout) -> str:
    plans = store.query("plans", {"run_id": run.id})
    steps = [s for s in store.query("steps", {"run_id": run.id}) if s.ended_at]
    approved = [p for p in plans if p.decision == "approved"]
    comments = [p.comment for p in plans if p.decision == "revised" and p.comment]
    ended = run.state == "ended"
    cost = sum(s.cost_estimate or 0 for s in steps)
    meta = f"*A {run.run_kind} run, started {run.created_at[:16].replace('T', ' ')} UTC"
    meta += f", took {_took(run.created_at, run.ended_at)}, an estimated ${cost:.2f} of agent time.*" if ended else ".*"
    lines = [f"# Run {run.id}" + (f": {run.outcome}" if ended else ""), "", meta, "",
             "## The request", "", run.request.strip(), ""]
    lines += _section("Sent back with", comments)
    if approved:
        plan = approved[-1]
        lines += [f"## The approved plan (version {plan.version})", "", plan.text.strip(), ""]
        lines += _section("How it follows the ideals", plan.ideals_addressed)
        lines += _section("Where it conflicts with them", plan.conflicts)
    if ended:
        lines += ["## How it went", "", "| Step | Attempt | Result |", "|------|---------|--------|"]
        lines += [f"| {s.name} | {s.attempt} | {_result(s)} |" for s in steps]
        lines += ["", f"**Outcome: {run.outcome}.** {run.reason}", ""]
        judged = next((s.produced for s in reversed(steps) if s.persona == "reviewer"
                       and isinstance(s.produced, dict) and "verdict" in s.produced), None)
        if judged:
            lines += [f"## The review: {judged['verdict']}", ""] + [f"- {r}" for r in judged.get("reasons", [])] + [""]
        if judged and "unbuilt" in judged:            # a spec kit sprint ends with its review (FR-090)
            lines += _sprint_review(judged, next((s.produced for s in reversed(steps) if s.name == "architecture_review"
                                                  and isinstance(s.produced, dict)), {}))
        documented = next((s.produced for s in reversed(steps) if s.name == "document" and s.passed
                           and isinstance(s.produced, dict)), None)
        if documented and documented.get("summary"):        # the documenter's account, kept (FR-104)
            lines += ["## What changed", "", documented["summary"].strip(), ""]
        lines += _smells(steps)
        covered = coverage_line(steps)
        lines += ["## Coverage", "", covered, ""] if covered else []
        lines += _tests_before_and_after(steps)
        lines += ["## Time and cost", "", *facts(store, run), ""]
        lines += _section("Commits on the run's branch", [f"`{c}`" for c in checkout.log_since_base()])
    return "\n".join(lines)


def _result(step) -> str:
    """How a step went: passed, or how it failed and, for a check, which one."""
    if step.passed:
        return "passed"
    failed = next((c["name"] for c in step.checks or [] if not c.get("passed")), None)
    return f"{step.failure}: {failed}" if step.failure == "check" and failed else str(step.failure)


def _sprint_review(judged, architect) -> list:
    """What the operator decides at merge: every deviation the final review found, and the architect's advice."""
    parts = [("Unbuilt", judged.get("unbuilt")), ("Requirement changes proposed", judged.get("requirement_changes")),
             ("Ideals reported broken", judged.get("ideals_broken")), ("Implementation details", judged.get("details")),
             ("Architect's warnings", architect.get("warnings")), ("Architect's suggestions", architect.get("suggestions"))]
    lines = ["## Sprint review", "", "For the operator at merge: what to take into the next request.", ""]
    for heading, items in parts:
        lines += [f"### {heading}", "", *([f"- {item}" for item in items] if items else ["- none"]), ""]
    return lines


def _smells(steps) -> list:
    """What the smells found (FR-107): measured on work that passed, reported here, and never a reason it went back."""
    found = [f"{s.name} (attempt {s.attempt}), {c['name']}: {c['note']}"
             for s in steps for c in s.checks or [] if c.get("smell") and not c.get("passed")]
    return ["## Smells", "", "Measured by the factory and reported, never a reason a step went back: tidy them at merge"
            " or in a later tidy.", "", *([f"- {item}" for item in found] if found else ["- none"]), ""]


def _tests_before_and_after(steps) -> list:
    """What the new tests said before the build, and the tests after it, as the factory ran them (FR-095)."""
    def output(check):
        ran = [s for s in steps if (s.produced or {}).get("output")
               and any(c["name"] == check for c in s.checks or [])]
        return ran[-1].produced["output"] if ran else ""
    before, after = output("tests_fail_first"), output("tests_pass")
    if not (before or after):
        return []
    return ["## The tests before and after the build", "",
            "### Before the build", "", "```text", before.strip() or "(not run)", "```", "",
            "### After the build", "", "```text", after.strip() or "(not run)", "```", ""]


def facts(store, run) -> list:
    """The run's time and cost, as the factory measured them (FR-092). Lines of a markdown table and its totals."""
    steps = [s for s in store.query("steps", {"run_id": run.id}) if s.ended_at]
    lines = ["| Step | Attempt | Model | Outcome | Minutes | Cost |", "|------|---------|-------|---------|---------|------|"]
    started = {e.step_id: e.payload.get("model") for e in store.query("events", {"run_id": run.id, "kind": "step_start"})}
    minutes = cost = waited = 0.0
    for before, s in zip([None, *steps], steps):
        took = _minutes(s.started_at, s.ended_at)
        minutes, cost = minutes + took, cost + (s.cost_estimate or 0)
        if before:
            waited += max(0.0, _minutes(before.ended_at, s.started_at))
        outcome = "passed" if s.passed else s.failure
        lines.append(f"| {s.name} | {s.attempt} | {started.get(s.id) or '-'} | {outcome} | {took:.1f} | "
                     f"${(s.cost_estimate or 0):.2f} |")
    lines += ["", f"Total: {minutes:.1f} minutes of steps, ${cost:.2f}.",
              f"Waiting for the operator, and between steps: {waited:.1f} minutes."]
    return lines


def _minutes(started, ended) -> float:
    def at(text):
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    return (at(ended) - at(started)).total_seconds() / 60


def _section(heading, items) -> list:
    return [f"## {heading}", "", *[f"- {item}" for item in items], ""] if items else []


def _took(started, ended) -> str:
    def at(text):
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    seconds = int((at(ended) - at(started)).total_seconds())
    return f"{seconds // 60}m {seconds % 60:02d}s"
