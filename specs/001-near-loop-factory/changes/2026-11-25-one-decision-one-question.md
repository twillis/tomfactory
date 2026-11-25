# Change record: one decision, one question (2026-11-25)

Made outside spec kit, for spec kit to review later. Built as FR-151, amending FR-132.

**Asked for by the orchestrator, from suggestion-box theme #72.** `merge_questions` keeps missing plain duplicates.
bttr_erp's run 99 asked one reason-for-a-change choice three times (Q89 the analyst, Q92 the planner, Q94 the
architect), and run 100 asked one end-date choice twice (Q98 the analyst, Q101 the planner: "May an existing row's END
also be edited later ... a) no b) yes"). Neither was merged, though run 98 did merge Q75 and Q80 into Q72.

**Why they were not merged.** I read the two runs' records read-only (`factory show 99 --json --read-only`, the same for
100), including the merge step's prompt as it was sent and its reply. There were two causes, one per run.

- **Run 100: the merge was proposed and the factory threw it away.** The reply was `{"merged": ["Q101", "Q98"]}`, one
  flat list, where `dialogue.merge` reads a list of groups. It took each string as a "group" of no questions, judged
  the merge as not holding, and merged nothing. The model gave the shape it was shown twice: the prompt's example was
  `` `["Q3", "Q5"]` `` and the reply fragment's shape for any list is `["…"]`.
- **Run 99: the merge was never proposed** (`{"merged": []}`). The three questions offer their options in a different
  order and under different letters, and each offers one option the others don't. The prompt said "Two questions on
  the same subject that could be answered differently are not the same" (lettered differently, they literally could
  be) and "When in doubt, do not merge". Measured afterwards, on the rewritten prompt, the light model still kept one
  of the three apart in one try of three. The middle model merged all three in three tries of three.
- **Not the cause:** the check that a merge holds (it refused run 100's only because of the shape), and what the step
  is shown (every question, whole, with who asked).

Against the old prompt, both live tests below failed on the light model, with no merge at all. That reproduces both
runs.

**Changed**

1. **`prompts/merge_questions.md`** rewritten around the decision, not the words. The test is: once the asker has
   answered one, is there nothing left to decide in the other? The options' order, letters, examples,
   recommendations and an option only one question offers don't make a different decision. Two questions on one
   subject where answering one leaves the other open stay apart, with run 100's look-alike as the example (may an
   end move later; must a moved date be marked a correction). The question kept first is the one whose options cover
   the others'. The reply's shape is shown as a list of groups: `[["Q3", "Q5"]]`, and two groups. "When in doubt, do
   not merge" is gone.
2. **`factory/dialogue.py`**: `merge` reads one group given as a flat list of question numbers as that group. A
   reply mixing a group and a loose number still merges nothing, as any reply that does not hold.
3. **`factory/tables.py`**: `MERGE` runs on the middle grade, not the light one.
4. **`factory/driver.py`**: `merge_questions`'s docstring no longer names the light model.
5. **`README.md`**: the dialogue's merge says the middle model and what counts as one question.
6. **`specs/001-near-loop-factory/spec.md`**: FR-132's text says the facilitator on the middle model, with an
   amendment note. FR-151 added.
7. **`docs/suggestions.md`**: theme #72 marked TAKEN for questions asking one decision, OPEN still for its other two
   parts: measurements of one shape, and questions that stand alone.
8. **`tests/test_merge_same_decision.py`**: the tests for FR-151, written first, using runs 99's and 100's question
   texts as they were asked.
   - Five run in the suite: run 100's flat reply is merged; a list of groups still merges and a mixed reply merges
     nothing; the prompt shows a list of groups and judges the decision; the merge is on the middle grade.
   - Two are live (`uv run pytest -m live tests/test_merge_same_decision.py`) and run the step's own prompt, persona
     and grade on the real model. Run 99's three reason questions must be one group. Run 100's two end-date
     questions must be one group, and the correction-mark question that looks like them must be in none.
   - Before the change, the three suite tests of new behaviour (the flat reply, the prompt, the grade) failed. The
     two that pin existing behaviour (a list of groups, a mixed reply) passed, and both live tests failed. After it,
     all pass.
9. **`tests/test_tuning.py`**: the FR-132 test expects the merge on the middle model.

**Decided in the build, for the operator to confirm**

- **The middle grade, about $0.025 a merge in place of $0.003.** A merge runs once a round, and only when two or more
  agents asked, so it costs cents a run. A missed duplicate costs him another answer from his phone. The light model
  got run 99 fully right two times in three, so the prompt alone didn't settle it. It isn't the strongest model.
  `[steps.<name>]` overrides do not reach the merge, which is in no table, so changing it back is a one-line edit
  in `tables.py`.
- **The flat list is read, not refused.** Refusing it would leave the batches unmerged with nobody to ask again,
  since the merge is advisory and runs once. A flat list of numbers can only mean one group.
- **Tests of a judgment are live tests.** No fake agent can show that a prompt makes a model merge, so the real
  cases run against the real model, outside the default suite like the other live tests. I ran them: both pass on
  the middle model.
- **Theme #72's other two parts are left open.** They are grouping many measurements of one shape (run 97's
  thirteen "See Q48's answer"), and questions that lean on another's context (run 98's "the same setup"). They ask
  for changes to how the speakers write questions, not to the merge's reading of them.

The suite: 755 passed before (after FR-150), 760 after (5 new), with the same one warning; the two live tests are
deselected by default (5 deselected now, 3 before) and pass on the middle model.
