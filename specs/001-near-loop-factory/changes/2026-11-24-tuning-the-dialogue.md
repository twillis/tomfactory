# Change record: tuning the dialogue after its first real run (2026-11-24)

Made outside spec kit, for spec kit to review later. The first real dialogue was bttr_erp's run 95; its retro
(`docs/retros/20261124-190526-ask-from-the-operator-through.md` in that codebase, "What did not") and its record are
the evidence. Built as FR-130 to FR-138, with FR-032, FR-120, FR-122, FR-124, FR-127 and FR-129 amended.

**Asked for by the operator.** On the plan check: "plan checker needs to chill the fuck out". On rulings reaching a
dialogue mid-way, he chose both ways (a note command, and reading the standing documents from main as it is now). On
a deletion an agent needs, he chose B: the factory deletes the files an agent asks it to. The rest are mechanics,
the orchestrator's.

**Changed**

1. **FR-130, the plan check stops blocking on polish (the operator's).** `tables.py`: the architect's and the plan
   check's reply is `blocking` and `notes` (was `points`). `workflow.round_outcome` counts only `blocking`; a round
   with notes alone is aligned, and `dialogue.proposal` shows its notes beside the plan ("Notes raised on this plan,
   not taken into it"). The transcript labels "Blocking:" and "A note for the planner:". `dialogue_check.md` now
   opens: "In a dialogue you are a colleague at the planning table, not the assayer. Raise what would break the
   build or contradict a ruling. Everything else is a note the planner may take or leave. A good plan agreed today
   beats a perfect plan in round twelve." Its checklist is kept, each item blocking only where it would break or
   stick the build or contradict a ruling. `dialogue_architect.md` sorts the same way. `review.md`, `converge.md`
   and the reviewer persona are unchanged: still the assayer at the end.
2. **FR-131, agents read before asking.** `dialogue_analyst.md`: read the ask against the requirements and rulings,
   `knowledge/` and the run records first; ask only what they do not settle; in round 1 do not present a reading of
   the ask as the answer. `dialogue.round_now` and `fragments/dialogue.md` say the same.
3. **FR-132, duplicate questions merged.** `tables.MERGE` (`merge_questions`, the facilitator, light, advisory,
   outside every table like the lead), run by `driver.merge_questions` after a round that waits, only when two or
   more agents asked. `dialogue.merge` keeps a merge only if every group holds (waiting ids, two or more, more than
   one agent, all questions or all measurements, no id twice); otherwise, or if the step fails, nothing is merged.
   A `merged` event records it; `dialogue.batch` leaves the duplicates out; `operations._answer_batch` copies each
   answer to its duplicates; the transcript says "merged into Q<n>".
4. **FR-133 and FR-134, rulings mid-dialogue (the operator's, both).** (a) `factory note [run] "<text>" [--by who]`,
   `operations.note`: a `note` event; `dialogue.transcript` heads with "Notes added to this run", each with its UTC
   time and who; refused when empty, ended, or not planning in a dialogue. (b) `Workspace.mirror_main`: before each
   speaker's turn, `requirements/`, the constitution and `IDEALS.md` as committed at the codebase's head now are
   copied into `.factory-main/` in the checkout, read-only, with a `.gitignore` of `*` inside so git (status, add,
   undo, commit) never sees it; the `standing` input names the commit and each file. Chosen as the safest: the
   agents can read it with their own tools inside their working directory, nothing a step commits or a check judges
   includes it, and `.factory.toml` and the table are still read from the starting commit.
5. **FR-135, the factory deletes files (the operator's, B).** A reply may carry `delete: [paths]`;
   `driver.delete_asked` deletes them after the step, before the checks. `checks.refused_deletions` refuses a path
   outside the checkout, in `.git` or among the factory's own files; then nothing is deleted and the new always-on
   check `deletions_inside` fails the step as a guard (undone, needs-me). A deletion made is in the step's change,
   so `changes_allowed` judges it against `may_change` (a builder deleting a test is undone as a guard). It is
   committed with the step's work. `prompts/fragments/deleting.md` is added to every read+edit step's prompt; the
   planner is told to name the step that deletes.
6. **FR-136, the documenter states only measured facts.** `run_record.measured`: test lines added against the
   budget, lines removed and test files deleted (`Workspace.lines_since_base`), every smell found, coverage before
   and after. The `measured` input is the documenter's; `document.md` says to state such figures only from it,
   never from the plan's hopes. The record shows the same under "What the factory measured".
7. **FR-137, the budget figures reconcile.** `dialogue.allowances` is the one sum: every speaker's step cost, split
   at each yes to spend more. The budget question quotes the last allowance; `run_record.facts` adds "The dialogue's
   speakers: $X in all, the sum of their rows above; from the start and from each yes to spend more: $a, then $b".
   Before, the question summed one way and nothing in the record showed it, so $11.52 and $11.42 could not be traced.
8. **FR-138, new-module scaffolding.** `write_tests.md`: a test of a module the build will create imports it inside
   the test, never behind `except ImportError` with a stand-in. `build.md`: such scaffolding is removed once the
   module is built; one in a test, which the builder may not change, is named in its summary.

**Mechanics chosen in the build, for the operator to confirm**

- Notes beside an aligned round reach the asker with the plan, not the planner: the planner spoke before them in
  that round, and a further planner turn would cost a round. A reply (`factory revise`) gives them to the planner.
- The builder cannot remove scaffolding in a test (it may not change tests): it names it, for the review.
- The merge keeps the clearest question's wording verbatim; it does not reword.
- `tests/test_size.py`'s tripwire is raised from 4,100 to 4,300 lines; the factory went from about 4,030 to 4,250.
- `.factory-main/` copies are text (what `git show` prints, line by line); a binary file there would be garbled.

**Not in this change**

- A merge step for the factory's own questions (budget, stuck points): they are never merged.
- Spec 006's other items.

Tests: `tests/test_tuning.py` (new, 24 cases). `tests/test_dialogue.py` and `tests/test_sprint_cycle.py` follow
`points` to `blocking`, and add the merge's reply where two agents ask in one round; `tests/conftest.py`'s `speaks`
takes `blocking` and `notes`, and `merges` is new.
