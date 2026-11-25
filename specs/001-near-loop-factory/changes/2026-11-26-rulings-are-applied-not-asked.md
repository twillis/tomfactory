# Change record: rulings are applied, not asked (2026-11-26)

Made outside spec kit, for spec kit to review later. The evidence is bttr_erp's run 103's planning dialogue. The
operator's ruling of 2026-11-21, "Withdrawn parent means its children are unreachable even if they reside in the
table so 404 not found", was quoted in the ask and was in the standing documents. The planner applied it in part and
left "the blank create form under a withdrawn parent" for the backlog. The plan check then asked the operator "should
this also be NOT_FOUND in this run? a) yes b) leave it in the backlog". The operator answered: "I would have thought
this goes without saying ... why would you be able to add a child record to a parent row that no longer exists", and
then asked: "Shouldn't the team have been aware of the rulings?" Built as FR-154 to FR-157. Spec 005 gains "A need
found in use (run 103)".

**Asked for by the operator, through the orchestrator.** A point the rulings settle is never put to him as a
question: the speaker applies the ruling and cites it. A plan that applies a ruling only in part is blocking for the
plan check. A question asked anyway says why no ruling settles it. The mechanism for the last one was left to the
build: a check where one is cheap, wording where it is not.

**Changed**

1. **FR-154, apply and cite, never ask.**
   - `prompts/fragments/dialogue.md` (every speaker) now says:
     - Where the standing documents hold an index of rulings, the speaker reads it first.
     - A point a ruling settles is never put to the asker, not even as "apply it here too?" or "this run or the
       backlog?". The speaker applies it whole and cites it: who made it, when, and where it is recorded.
     - A ruling stands until its maker changes it.
     - Each question asked goes with its `rulings_checked` item.
   - `prompts/dialogue_analyst.md` drops "say in a question what the record says only when the asker may want it
     otherwise". That clause invited exactly run 103's question. In its place, the analyst never asks whether the
     asker wants a ruling otherwise.
   - `prompts/dialogue_planner.md` says to apply each ruling whole and cite it, and that no part is left for the
     backlog or a later run. A blocking point that a ruling is applied in part is taken, not declined.
   - `personas/planner.md`, priority 6, kept the run-97 rule ("list it for the target's backlog as left for a later
     small sprint"), which is what licensed run 103's split. It now says a ruling is applied whole and that only a
     case no ruling settles may wait.
2. **FR-155, a ruling applied in part is blocking.**
   - `prompts/dialogue_check.md` gains this item under "What to look for": the plan check names the ruling, the cases
     the plan leaves out, and the fix.
   - Its "ask the asker only what is theirs" sentence adds: never whether to apply a ruling.
   - `prompts/dialogue_architect.md` says the same under **Blocking**.
   - `personas/reviewer.md` gains a priority: a ruling applied in part is not applied. That persona serves both the
     plan check and the final review.
3. **FR-156, why no ruling settles it, checked and shown.**
   - `factory/tables.py`: every speaker's envelope gains `rulings_checked` (a list). `_speaker` adds the check
     `rulings_checked` to every speaker, and the planner keeps `dialogue_moves` beside it.
   - `factory/checks.py` adds `rulings_checked`. The reply must hold one non-blank item per question. A measurement
     needs none. On failure the speaker is sent back (its `on_fail`, `Rework`), told the counts.
   - `factory/dialogue.py` adds `rulings_checked(store, run_id)`. It reads each question's item from the reply of the
     speaker that asked it, matched by the question's text within that speaker's round. Nothing new is stored and the
     schema has no migration.
   - `render_batch(run, questions, why)` prints `# Checked against the rulings: …` on the line before each question.
     A `#` line is not read back.
   - `transcript` prints the item under the question, so the next round and the run's record keep it.
   - `factory/operations.py`: `questions` passes the reasons to `render_batch`.
   - Each speaker prompt's reply list documents `rulings_checked`.
4. **FR-157, an index of rulings read first.** `factory/driver.py` adds `RULINGS_INDEX = "rulings.md"`. `_standing`
   names any copied standing document of that file name (any folder, any case) first, with "Read first the
   codebase's index of rulings, … then the entries it points to". It also lists the index first among the files. No
   codebase is named. bttr_erp's index is to be `requirements/rulings.md`, which `STANDING` already copies.

**Mechanics chosen in the build, for the operator to confirm**

- **A reason per question, checked by count, not a ruling named per question.** The batch could have named "the
  ruling it was checked against", but most questions are asked because no ruling bears on them, so there is often no
  ruling to name. What can be checked mechanically and cheaply is that every question carries a stated reason. The
  operator then sees the reason where he answers, and can say "ruling X settles this" in a word. Whether the reason
  is true stays a judgement: no check can tell that a ruling settles a question.
- **Shown as a `#` line before the question**, so the batch still parses as it did and an orchestrator walking the
  operator through the batch has the reason in hand.
- **Read from the reply, not stored.** This avoids a store migration while a run is open on bttr_erp under the
  installed factory. A question from an older reply simply has no line.
- **The index is found by file name (`rulings.md`)**, not by a setting. This is the cheapest rule that names no
  codebase. A setting can come later if a codebase names its index otherwise.
- **The final review is not given a new check.** Only its persona's priority changed (FR-155). The dialogue is where
  run 103's error happened.

**Not in this change**

- Whether a ruling truly settles a question is not checked by the factory. It is told, shown and reviewable.
- bttr_erp's `requirements/rulings.md` is drafted outside the repo, for the operator and orchestrator to check and
  commit. The run order stays the record, and it wins where the two differ.

Tests: `tests/test_rulings.py` (new, 27 cases). `tests/conftest.py`'s `speaks` and `planner_says` give one
`rulings_checked` item per question (helper `checked`). The suite went from 776 to 803 passed. Every new case
failed first for the reason it names, except two that guard behaviour already true:
- a question from an older reply is shown without a reason line;
- with no `rulings.md`, no index is named.
