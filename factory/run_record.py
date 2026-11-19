"""Control: a run's record, as a document in the codebase it worked on (FR-079, FR-080).

Written to the run's branch when its plan is approved, and completed when the run ends,
so the reason for a change, and how it was made, travel with the code. The record is
rendered from the factory's own records of the run; this module decides nothing.
"""
import datetime


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
        lines += [f"| {s.name} | {s.attempt} | {'passed' if s.passed else s.failure} |" for s in steps]
        lines += ["", f"**Outcome: {run.outcome}.** {run.reason}", ""]
        judged = next((s.produced for s in reversed(steps) if s.persona == "reviewer"
                       and isinstance(s.produced, dict) and "verdict" in s.produced), None)
        if judged:
            lines += [f"## The review: {judged['verdict']}", ""] + [f"- {r}" for r in judged.get("reasons", [])] + [""]
        lines += _section("Commits on the run's branch", [f"`{c}`" for c in checkout.log_since_base()])
    return "\n".join(lines)


def _section(heading, items) -> list:
    return [f"## {heading}", "", *[f"- {item}" for item in items], ""] if items else []


def _took(started, ended) -> str:
    def at(text):
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    seconds = int((at(ended) - at(started)).total_seconds())
    return f"{seconds // 60}m {seconds % 60:02d}s"
