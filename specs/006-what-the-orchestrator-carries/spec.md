# Feature Specification: What the Orchestrator Carries That the Factory Should

**Created**: 2026-11-24

**Status**: A need, agreed by the operator as factory tech debt. Nothing designed. To be worked through with the
operator the way spec 005 was: questions one at a time, then design, then build. Not run through spec kit; no FR numbers
until built (constitution S8).

## The need

The factory's results today depend on what its orchestrator does outside it. Another orchestrator, or the operator
driving the factory directly, would not get the same results, because work the factory needs is done by hand around it.
Whatever is mechanical, repeatable or checkable among that work belongs in the factory, where every run gets it and
its record shows it. What stays with an orchestrator is what genuinely needs one.

**How we would know it is met**

- A run driven from the command line alone, with no orchestrator, verifies its claims, measures what it needs and
  records its merge as well as a run driven by Claude Code does today.
- The operator can see, in a run's record, everything that was checked and why each file changed, without asking.

## In the operator's words (2026-11-24)

- On a merge summary that said why each file changed: "probably a good thing to do from now on, it helps since im not
  deep in the code but inevitably would be responsible for it, so that part of the loop i need".
- "good idea, its kind of hard for me to imagine what you orchestrator contribute to the process of the factory and its
  possible you are doing some things that probably should be in there."
- On the inventory below: "A yeah thats tech debt for the factory I think".

## The inventory (the orchestrator's own account, bttr_erp runs 86 to 95, 2026-11-24)

**Done by the orchestrator, probably belongs in the factory**

1. **Measuring.** Every fact only a running system can give: on a scratch database before writing a request, and each
   time an agent asked (`{"measure": ...}`): driver casts, timestamp round trips, hash costs, session settings, library
   behaviour (JsonLogic's official suite against two Python libraries). Agents can run nothing, so a run cannot get a
   fact without an orchestrator. Spikes (spec 004) are a partial answer.
2. **Verifying a run's claims against the running system after it ends.** The final review reads the change; nobody runs
   it against reality. Examples: run 87's tidy checked by logging every SQL statement and refusal of the list tests on
   main and on the run's branch (9,534 statements, 255 refusals, identical); run 90's "a write outside bttr makes a stale
   save CONFLICT" checked by a raw SQL UPDATE; run 91's field errors checked by sending 1 for a boolean and 12345 for a
   varchar(3); run 92's robot re-run.
3. **Merging and recording.** `git merge --no-ff`, the full suite on main, the run-order row, the backlog entries a tidy
   closed (a tidy has no architect), small fixes the review left (a broken docstring line, a CHANGELOG that said the
   tests were not run, a wrong measurement claimed in a CHANGELOG), the push.
4. **Catching environment drift.** Run 92's import failure on Python 3.13 was invisible in the factory's contained run on
   3.14; found only because the orchestrator ran the suite elsewhere. Now pinned by `.python-version`, but nothing in the
   factory checks that the Python it tests on is the codebase's floor.
5. **Why each file changed.** A one-line reason per changed file, traced to the plan; a file that does not trace is a
   reason to stop. Asked for by the operator (above).
6. **Deleting a file.** Run 95's builder built everything else and stopped, three attempts in a row, because "I have no tool that can delete a file"; the plan said to delete `bttr_erp/repo/named_form.py`. The orchestrator ran `git rm` in the run's checkout, committed it, and resumed. An agent can create and edit a file but cannot remove one, so a plan that deletes always needs a hand. **Built the same day** in the tuning (change record `2026-11-24-tuning-the-dialogue.md`): an agent lists the files to delete and the factory deletes them, checked against what the step may change.
7. **Answering what the record already settles.** In run 95's dialogue most questions were answered from the operator's
   earlier answers and the prior art in `knowledge/`; that is the dialogue agents' own job (spec 005's tuning). Run 97 (2026-11-24): round 2 was spent on one question (the gaps key's default) that the record settled (docs/backlog.md, run 67's architect warning: a new key's default is what earlier tables already do). The operator: a whole round for an easily answered question. A question the record answers should be answered by the agent that finds the answer, and one that only the orchestrator answers from the record should not hold a round alone.

8. **Saying who answered.** The factory's store records an answer as the lead's or the operator's, nothing else. In
   run 97 the orchestrator answered 25 of the 26 questions that reached the asker (the measurements, and the rest from
   the record and the prior art); the run record and the retro print every one as "operator answered". Raised by the
   orchestrator on 2026-11-24 during run 91 (its own send-back was filed as the operator's comment) and not built. A
   record that puts the orchestrator's words under the operator's name is the one thing a record must not do.
   **Built 2026-11-25** (change record `2026-11-25-who-answered.md`, FR-139 and FR-140): `factory answer --by
   orchestrator`, `answer (orchestrator):` in a batch, and every text made from an answer names who gave it; the
   retro's `operator_feedback` takes only his. A send-back by `factory revise` is still recorded as his; that part of
   run 91's case is not built.

**Evidence added 2026-11-25, from run 97**

- Item 2 (verifying): the factory accepted run 97 with tests, build and review each passing on the first attempt. The
  orchestrator's check afterwards (five checkers and ten sceptics on a real PostgreSQL) found two ways through the
  guard and five lesser faults the review had not, among them the very move the decision was written to stop, on a
  hand-written table. bttr_erp `docs/verification/2026-11-25-run-97-d10.md`.
- Item 3 (merging): run 96 ended accepted at 18:56 and was merged at 21:24. The orchestrator had said it would merge
  "in the background", and it cannot act between the operator's messages. An accepted run waited two and a half hours
  for a turn.

**Belongs with the operator; the orchestrator only relays it**

- Rulings, agreement, approval, a dialogue's budget. The factory now asks for these directly (spec 005).

**What an orchestrator adds that is hard to put in the factory**

- Translating between the operator and the factory: walking him through questions on his phone, recording a passing
  remark as a ruling in his words, noticing when "should we" is a decision.
- Research outside the codebase: deep dives into a reference implementation, a library's health, prior art.
- Running parallel work: building the factory itself in a worktree while it runs a target.
- Judgement across runs: noticing a repeated mistake, sequencing work, knowing when to stop.

## Open questions (to work through with the operator; none answered)

1. Which of items 1 to 7 first, and is any of them the orchestrator's after all?
2. Measuring: should the factory run measurements itself, contained like tests, from a measure an agent asks for? Who
   writes the measuring code, and who checks it measures what was asked?
3. Verifying: what does "checked against the running system" mean per kind of run (a tidy: behaviour identical; a change:
   the plan's claims hold), and who states what to check, the plan?
4. Merging: should the factory merge an accepted run itself (today the operator's rule is that the orchestrator merges
   and only the operator pushes)?
5. Where each item's result is shown: the run record, the merge commit, a summary for the operator's phone?
