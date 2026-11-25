"""Control: a planning dialogue, from an ask to an agreed plan (FR-119 to FR-128).

What each speaker said is kept as its step's reply, the questions it put to the asker as questions with their
round, the plan the planner proposed aligned as a plan, and the asker's agreement as that plan's decision: the
factory's records, through records.py. This module closes a round, says what a waiting dialogue waits for, writes
the batch the asker answers and reads it back, and renders the dialogue so far, for the next round's speakers and
for the run's record. What the end of a round means is decided in workflow.py; nothing here decides it.
"""
import re
from typing import NamedTuple

from factory import records, workflow

BUDGET, POINTS = "budget", "points"         # the factory's own questions in a batch (FR-124, FR-120)
SIMILAR = 5                                 # how many earlier runs the estimate is shown beside (FR-123)
ROLES = {"reviewer": "the plan check"}      # a speaker is named by its persona, but the reviewer by its part here
FATES = {"pending": "proposed for agreement", "agreed": "agreed by the asker", "approved": "agreed, and approved",
         "abandoned": "abandoned"}
MARK = re.compile(r"^\[Q(\d+)\]")
ANSWER = re.compile(r"^answer(?: \(([^)]*)\))?:")     # `answer:`, or `answer (orchestrator):` to say who gave it


def role(persona) -> str:
    return ROLES.get(persona, f"the {persona}")


def rounds(store, run_id) -> list:
    """Every round closed so far, oldest first; each event's payload has its number, how it ended, the record of
    what each speaker said in it, and the plan it proposed, if any."""
    return store.query("events", {"run_id": run_id, "kind": "round"})


def batch(store, run_id) -> list:
    """The dialogue's questions still waiting for the asker, in the order they were asked; a question merged into
    another is answered with it, so it is not in the batch (FR-132)."""
    merged = merged_into(store, run_id)
    return [q for q in store.query("questions", {"run_id": run_id})
            if q.round is not None and q.answer is None and q.id not in merged]


# ---- the end of a round ----

def close_round(store, run, steps, settings) -> workflow.Run | workflow.Wait:
    """Record the round that has just ended: every speaker's questions and measurements as one batch each, the
    factory's own questions where the agents are stuck or the budget is spent, and the plan proposed aligned. Then
    say where the run goes: round again at once, or wait for the asker (FR-120, FR-122, FR-124)."""
    speakers = [entry for entry in steps if entry.dialogue]
    done = store.query("steps", {"run_id": run.id})
    said = {entry.name: next(s for s in reversed(done) if s.name == entry.name and s.passed) for entry in speakers}
    closed = rounds(store, run.id)
    number, in_a_row = len(closed) + 1, 0
    for earlier in reversed(closed):
        if earlier.payload["outcome"] != "points":
            break
        in_a_row += 1
    outcome = workflow.round_outcome([s.produced for s in said.values()], in_a_row, run.attempt_limit)
    spent = allowances(store, run.id, said)[-1]
    over = outcome != "aligned" and workflow.dialogue_over_budget(spent, settings.dialogue_budget_dollars)
    with store.transaction():
        for name, record in said.items():
            for text in record.produced.get("questions") or []:
                records.ask(store, run.id, name, record.persona, text, number)
            for text in record.produced.get("measure") or []:
                records.ask(store, run.id, name, record.persona, text, number, measure=True)
        if outcome == "stuck":
            points = [f"{role(r.persona)}: {p}" for r in said.values() for p in r.produced.get("blocking") or []]
            records.ask(store, run.id, POINTS, "factory", f"The agents have raised blocking points for {in_a_row + 1}"
                        " rounds without settling them among themselves:\n" + "\n".join(f"- {p}" for p in points)
                        + "\nWhat should they do?", number)
        if over:
            cap = settings.dialogue_budget_dollars
            records.ask(store, run.id, BUDGET, "factory", f"The dialogue has cost ${spent:.2f}, at its budget of"
                        f" ${cap:.2f}. Spend up to ${cap:.2f} more? yes / no", number)
        version = None
        if outcome == "aligned":
            proposed = next(r.produced for r in said.values() if "aligned" in r.produced)
            notes = [f"{role(r.persona)}: {n}" for r in said.values() for n in r.produced.get("notes") or []]
            version = records.add_plan(store, run.id, proposal(store, run, proposed, notes),
                                       proposed.get("ideals_addressed") or [], proposed.get("conflicts") or []).version
        records.event(store, run.id, "round", f"round {number}: {outcome}",
                      {"round": number, "outcome": outcome, "said": {n: r.id for n, r in said.items()},
                       "plan": version})
    return workflow.Wait() if over else workflow.after_round(outcome, speakers[0].name)


def allowances(store, run_id, speakers=()) -> list[float]:
    """What the dialogue's speakers have cost in each allowance, oldest first: from the start to the asker's first
    yes to spend more, then to each next yes, the last still open (FR-124). The one computation of what a dialogue
    cost: the budget question quotes the last, and the run's record shows them all beside its table (FR-137).
    The speakers are every step that has spoken in a round, and `speakers`, the names of a round being closed."""
    names = set(speakers) | {name for closed in rounds(store, run_id) for name in closed.payload["said"]}
    yeses = sorted(q.answered_at for q in store.query("questions", {"run_id": run_id, "step": BUDGET})
                   if q.answer and workflow.spend_more(q.answer))
    costs = [0.0] * (len(yeses) + 1)
    for s in store.query("steps", {"run_id": run_id}):
        if s.name in names:
            costs[sum(1 for yes in yeses if s.started_at >= yes)] += s.cost_estimate or 0
    return [round(cost, 2) for cost in costs]


def proposal(store, run, said, notes=()) -> str:
    """The plan the asker is asked to agree to: the planner's plan and estimate, beside similar past runs (FR-123),
    the points it declined, each with its reason, and the notes raised on it that held nothing open (FR-130)."""
    similar = similar_runs(store, run)
    estimate = said.get("estimate", "").strip() or "The planner gave none: it had not yet proposed aligned."
    text = (said["plan"].strip() + "\n\n## The estimate\n\n" + estimate + "\n\nBeside it, from the"
            f" factory's own records, the last {SIMILAR} runs of this kind on this codebase that were accepted:\n\n"
            + "\n".join(f"- {line}" for line in similar or ["none yet"]))
    if said.get("declined"):
        text += "\n\n## Declined by the planner, with its reason\n\n" + "\n".join(f"- {d}" for d in said["declined"])
    if notes:
        text += ("\n\n## Notes raised on this plan, not taken into it\n\nNotes never hold the dialogue open; the plan"
                 " above is what is built. Reply with any you want taken.\n\n" + "\n".join(f"- {n}" for n in notes))
    return text


def similar_runs(store, run) -> list[str]:
    """The rule for "similar" (FR-123): the last runs of the same kind on the same codebase that ended accepted,
    newest first, each with the minutes its steps took and what they cost."""
    earlier = [r for r in store.query("runs", {"target": run.target, "run_kind": run.run_kind, "outcome": "accepted"},
                                      order="-id") if r.id != run.id][:SIMILAR]
    return [f"Run {r.id} (accepted, {r.created_at[:10]}): {minutes:.0f} minutes of steps, ${cost:.2f}"
            for r in earlier for minutes, cost in [records.took(store, r.id)]]


# ---- a dialogue paused at its budget (FR-124) ----

def paused(store, run_id) -> bool:
    """Has the asker said no to spending more, with nothing done in the dialogue since?"""
    moves = [e for e in store.query("events", {"run_id": run_id}) if e.kind in ("round", "answered", "paused", "agreed")]
    return bool(moves) and moves[-1].kind == "paused"


def latest_draft(store, run_id) -> dict | None:
    """The planner's latest reply in the dialogue that holds a plan, to agree to at a pause."""
    said = [s.produced for s in store.query("steps", {"run_id": run_id}) if s.passed and isinstance(s.produced, dict)
            and "aligned" in s.produced and str(s.produced.get("plan")).strip()]
    return said[-1] if said else None


def so_far(store, run) -> str:
    """What a paused dialogue has: every round so far, and the planner's latest draft."""
    draft_text = draft(store, run.id) or "The planner has written no plan yet."
    return (f"# Run {run.id}: the dialogue is paused at its budget. Nothing is lost; what it has so far is below.\n"
            f"# Say yes to spend more (factory answer yes), agree to the draft (factory agree), or abandon it.\n\n"
            f"{transcript(store, run)}\n\n## The planner's latest draft\n\n{draft_text}\n")


# ---- what a waiting dialogue waits for (FR-128) ----

def waiting(store, run) -> dict | None:
    """What a dialogue run waiting for the asker waits for: answers, agreement or approval; None for a run that is
    not a dialogue's, or not waiting. `says` is a sentence; `short`, a few words for a status line."""
    closed = rounds(store, run.id)
    if run.state != "awaiting_approval" or not closed:
        return None
    number, pending = closed[-1].payload["round"], batch(store, run.id)
    if pending:
        who = list(dict.fromkeys(role(q.asked_by) for q in pending))
        measure = any(q.measure for q in pending)
        count = f"{len(pending)} question" + ("s" if len(pending) > 1 else "")
        says = f"answers to {count} from {_and(who)}" + (", with a measurement asked for" if measure else "")
        return {"for": "answers", "round": number, "from": who, "measure": measure, "says": says,
                "short": "answers: " + ", ".join(who), "next": "factory questions, then factory answer"}
    plan = records.current_plan(store, run.id)
    if paused(store, run.id) and not (plan and plan.decision == "agreed"):
        return {"for": "paused", "round": number, "short": "paused at its budget",
                "says": "the asker: the dialogue is paused at its budget, with everything it has so far kept",
                "next": "factory questions (what it has), then factory answer yes, factory agree or factory abandon"}
    if plan and plan.decision == "pending":
        return {"for": "agreement", "round": number, "version": plan.version,
                "short": f"agreement: plan {plan.version}",
                "says": f"your agreement to plan version {plan.version}, proposed in round {number}",
                "next": "factory plan, then factory agree, or reply with factory revise \"...\""}
    if plan and plan.decision == "agreed":
        return {"for": "approval", "round": number, "version": plan.version, "short": f"approval: plan {plan.version}",
                "says": f"approval of plan version {plan.version}, which you agreed", "next": "factory approve"}
    return None


def not_current(store, run) -> str | None:
    """Why a dialogue run has no plan to show as the current one, or None if it has one (FR-128): no plan is
    proposed yet, or the latest was replied to or found stale and the dialogue has gone on."""
    if run.state == "ended" or not rounds(store, run.id):
        return None
    plan, now = records.current_plan(store, run.id), waiting(store, run)
    if plan and plan.decision in ("pending", "agreed", "approved") and not (now and now["for"] == "answers"):
        return None
    doing = f"it is waiting for {now['says']}" if now else f"the agents are in round {len(rounds(store, run.id)) + 1}"
    earlier = (f"; the plan proposed as version {plan.version} was {_fate(plan)}" if plan
               else "; no plan is proposed yet")
    return f"run {run.id} has no plan to read now: {doing}{earlier}"


def _and(names) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _fate(plan) -> str:
    if plan.decision == "revised":
        return f"replied to, not agreed: {plan.comment}"
    if plan.decision == "stale":
        return f"approved, then found stale against the codebase: {plan.comment}"
    return FATES[plan.decision]


# ---- the batch the asker answers: each question with a place for its answer under it (FR-121) ----

def render_batch(run, questions, why=None) -> str:
    """The batch as the asker answers it: each question with a place for its answer under it, and on the line before
    it, which `#` keeps from being read back, why no ruling settles it, as its speaker said (FR-156)."""
    number = questions[0].round if questions else 0
    lines = [f"# Run {run.id}, round {number}: {len(questions)} question{'s' if len(questions) > 1 else ''}."
             " Write each answer under its question, after \"answer:\".",
             "# An answer the orchestrator gave, a measurement above all, goes after \"answer (orchestrator):\".",
             "# Lines that start with # are not read. Save and close to send every answer as one batch."]
    heard = None
    for q in questions:
        who = (q.asked_by, q.measure)
        if who != heard:
            heard = who
            lines += ["", f"# ---- {role(q.asked_by)} asks{' for a measurement' if q.measure else ''} ----"]
        checked = [f"# Checked against the rulings: {(why or {})[q.id]}"] if (why or {}).get(q.id) else []
        lines += ["", *checked, f"[Q{q.id}] {q.question}", "answer:"]
    return "\n".join(lines) + "\n"


def rulings_checked(store, run_id) -> dict[int, str]:
    """Why no ruling settled each question, by its id, as the speaker that asked it said in its reply (FR-156). A
    question from a reply that gave no reason (one made before speakers gave them) has none."""
    asked = store.query("questions", {"run_id": run_id})
    why = {}
    for closed in rounds(store, run_id):
        for name, record_id in closed.payload["said"].items():
            said = store.get("steps", record_id).produced
            said = said if isinstance(said, dict) else {}
            reasons = dict(zip(said.get("questions") or [], said.get("rulings_checked") or []))
            why.update({q.id: str(reasons[q.question]) for q in asked if q.round == closed.payload["round"]
                        and q.step == name and not q.measure and q.question in reasons})
    return why


class Answer(NamedTuple):
    text: str
    by: str         # who gave it: one of workflow.ANSWERERS (FR-139)


def parse_batch(text, questions, by="operator") -> dict[int, Answer]:
    """The asker's answers, by question: every waiting question answered, and nothing else. Lines that start with
    # are not read. A plain `answer:` is `by`'s; `answer (orchestrator):` or `answer (operator):` says who gave
    that one (FR-139). A ValueError says what is missing, not asked, or marked as no one's who may answer."""
    blocks, current = {}, None
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        found = MARK.match(line)
        if found:
            current = int(found.group(1))
            blocks[current] = []
        elif current is not None:
            blocks[current].append(line)
    answers = {}
    for number, lines in blocks.items():
        at = next((i for i, line in enumerate(lines) if ANSWER.match(line)), None)
        if at is None:
            answers[number] = Answer("", by)
            continue
        marked = ANSWER.match(lines[at])
        who = marked.group(1) or by
        if who not in workflow.ANSWERERS:
            raise ValueError(f"Q{number}'s answer is marked as {who}'s; an answer is the operator's or the"
                             " orchestrator's: write answer:, answer (operator): or answer (orchestrator):")
        answers[number] = Answer("\n".join([lines[at][marked.end():], *lines[at + 1:]]).strip(), who)
    unknown = sorted(set(answers) - {q.id for q in questions})
    if unknown:
        raise ValueError("the answers name questions that are not waiting: " + ", ".join(f"Q{n}" for n in unknown))
    missing = [f"Q{q.id}" for q in questions if not (q.id in answers and answers[q.id].text)]
    if missing:
        raise ValueError(f"each of these has no answer: {', '.join(missing)}; write one under it, after \"answer:\"")
    return {q.id: answers[q.id] for q in questions}


# ---- the dialogue so far: for the next round's speakers, and for the run's record (FR-120, FR-127) ----

def round_now(store, run_id) -> str:
    number = len(rounds(store, run_id)) + 1
    if number == 1:
        return ("This is round 1 of the dialogue. It is the first: nothing has been asked or answered yet. Read the"
                " artifacts first, then ask your open questions: only what they do not settle.")
    return f"This is round {number} of the dialogue."


def draft(store, run_id) -> str:
    """The latest plan the planner wrote in the dialogue, in this round or an earlier one."""
    written = [s.produced["plan"] for s in store.query("steps", {"run_id": run_id}) if s.passed
               and isinstance(s.produced, dict) and "aligned" in s.produced and str(s.produced.get("plan")).strip()]
    return written[-1] if written else ""


def transcript(store, run) -> str:
    """Every round so far: what each speaker asked and was answered, the points it raised, the plan proposed and
    what the asker did with it; and each re-check of an approved plan against a codebase that had moved."""
    asked = store.query("questions", {"run_id": run.id})
    plans = {p.version: p for p in store.query("plans", {"run_id": run.id})}
    into, why = merged_into(store, run.id), rulings_checked(store, run.id)
    lines = []
    added = notes(store, run.id)
    if added:                                   # rulings and facts added while it plans, for every speaker (FR-133)
        lines += ["### Notes added to this run", "", "Rulings and facts added while the dialogue runs. A ruling here"
                  " stands over the ask and over any earlier answer.", "",
                  *[f"- {n.at[:16].replace('T', ' ')} UTC, from {n.payload['by']}: {n.payload['text']}"
                    for n in added], ""]
    for closed in rounds(store, run.id):
        number = closed.payload["round"]
        lines += [f"### Round {number}", ""]
        for name, record_id in closed.payload["said"].items():
            record = store.get("steps", record_id)
            said = record.produced
            heading = role(record.persona).capitalize()
            if "aligned" in said:
                heading += f" (aligned: {said['aligned']}; how much dialogue this needs: {said['how_much']})"
            items = [_asked(q, into, why) for q in asked if q.round == number and q.step == name]
            items += [f"- Blocking: {point}" for point in said.get("blocking") or []]
            items += [f"- A note for the planner: {note}" for note in said.get("notes") or []]
            items += [f"- Declined, with its reason: {item}" for item in said.get("declined") or []]
            lines += [f"{heading}:", "", *(items or ["- nothing to raise"]), ""]
        own = [_asked(q, into) for q in asked if q.round == number and q.asked_by == "factory"]
        lines += ["The factory:", "", *own, ""] if own else []
        if closed.payload.get("plan"):
            plan = plans[closed.payload["plan"]]
            lines += [f"The planner proposed plan version {plan.version}; it was {_fate(plan)}.", ""]
    for moved in store.query("events", {"run_id": run.id, "kind": "restarted_from"}):
        checked = [s for s in store.query("steps", {"run_id": run.id}) if s.started_at >= moved.at and s.ended_at
                   and isinstance(s.produced, dict) and "findings" in s.produced][:1]
        for s in checked:
            found = "; ".join(s.produced["findings"]) or "nothing"
            lines += [f"Re-checked against the codebase at {moved.payload['to'][:10]}, which had moved: "
                      f"{s.produced.get('verdict')}; found: {found}.", ""]
    return "\n".join(lines).strip()


def _asked(q, into=None, why=None) -> str:
    said = f"- {'Asked for a measurement' if q.measure else 'Asked'} (Q{q.id}): {q.question}"
    if (why or {}).get(q.id):           # why no ruling settled it, as its speaker said (FR-156)
        return _asked(q, into) + f"\n  Checked against the rulings: {why[q.id]}"
    if (into or {}).get(q.id):          # answered once, under the question it was merged into: not again here
        return said + (f"\n  The same as another agent's question: merged into Q{into[q.id]} and answered there,"
                       " once.")
    if q.answer is None:
        return said + "\n  Not yet answered."
    return said + f"\n  Answered by the {q.answered_by}: {q.answer}"


# ---- rulings and facts added to a run while it plans (FR-133) ----

def notes(store, run_id) -> list:
    """Every note added to the run, oldest first: each event's payload has its text and who added it."""
    return store.query("events", {"run_id": run_id, "kind": "note"})


# ---- questions from different agents that ask the same thing, answered once (FR-132) ----

def to_merge(store, run_id) -> list:
    """The waiting questions the merge reads: the agents' own, where more than one agent asked; else none."""
    waiting = [q for q in batch(store, run_id) if q.asked_by != "factory"]
    return waiting if len({q.step for q in waiting}) > 1 else []


def merge_input(store, run_id) -> str:
    return "\n".join(f"[Q{q.id}] {role(q.asked_by)}{', a measurement' if q.measure else ''}: {q.question}"
                     for q in to_merge(store, run_id))


def merge(store, run_id, said, waiting) -> dict[int, int]:
    """Record the merge the light model proposed, if it holds: each group two or more waiting questions, from more
    than one agent, all questions or all measurements, none in two groups; the first is the one the asker answers.
    One group given as a flat list of numbers is read as that group (FR-151). Anything else, or no reply, merges
    nothing: the batches go to the asker as they were asked. Returns what was merged into what."""
    by_id, into, seen = {q.id: q for q in waiting}, {}, set()
    groups = (said or {}).get("merged") if isinstance(said, dict) else None
    if isinstance(groups, list) and groups and all(isinstance(number, str) for number in groups):
        groups = [groups]
    for group in groups if isinstance(groups, list) else []:
        ids = [int(str(i).lstrip("Q")) if str(i).lstrip("Q").isdigit() else None for i in
               (group if isinstance(group, list) else [])]
        found = [by_id.get(i) for i in ids]
        if len(ids) < 2 or None in found or seen & set(ids) or len({q.step for q in found}) < 2 \
                or len({q.measure for q in found}) > 1:
            into = {}
            break
        seen |= set(ids)
        into.update({i: ids[0] for i in ids[1:]})
    if into:
        records.event(store, run_id, "merged", f"{len(into)} questions merged into others", {"into": into})
    return into


def merged_into(store, run_id) -> dict[int, int]:
    """Each question merged into another, by its id: the id of the one the asker answers for it."""
    return {int(dup): kept for e in store.query("events", {"run_id": run_id, "kind": "merged"})
            for dup, kept in e.payload["into"].items()}
