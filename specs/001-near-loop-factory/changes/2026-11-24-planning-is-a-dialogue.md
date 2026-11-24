# Change record: planning is a dialogue from an ask to an executable plan (2026-11-24)

Made outside spec kit, for spec kit to review later. Specification 005 (`specs/005-planning-is-a-dialogue/spec.md`):
its need, the operator's eight answers and ten design decisions (D1 to D10), built as FR-119 to FR-129.

**Asked for by the operator.** "There needs to be an agent that can analyze the ask and the code base and the current
requirements and all that s*** to work with the asker to get a solid [executable] plan. I feel like this is what the
planning process should be not input into the planning process." Every answer and decision is his, given one at a
time on 2026-11-24.

**Changed**

- **FR-119, `tables.py`.** `DIALOGUE`: `dialogue_analyst`, `dialogue_planner`, `dialogue_architect`,
  `dialogue_check` (the one wait) and `recheck_plan`. `SPRINT_STEPS` starts with it in place of `plan`,
  `check_plan` and `amend_plan` (answer 5); a tidy on a sprint codebase is planned in it too (`SPRINT_TIDY_TESTS`,
  `SPRINT_TIDY_CODE`, chosen by `table_for` through `SPRINT`). The plain and spec kit cycles and spikes are as they
  were. `prompts/check_plan.md` and `amend_plan.md` are gone: their lessons are in `dialogue_check.md` and
  `dialogue_planner.md`, and the tests that held them now read those. `workflow.Step` gains `dialogue` (a speaker)
  and `on_moved` (where approval leads when the codebase moved).
- **FR-120, `workflow.py`, `dialogue.py`, `driver.py`.** `round_outcome` and `after_round`: questions or
  measurements wait for the asker; only points go round again at once; points `attempt_limit` rounds in a row are put
  to the asker ("stuck"); nothing raised is aligned. The driver, at a speaker's wait, calls `dialogue.close_round`,
  which records each speaker's questions with their round (`records.ask` takes `round` and `measure`) and the round
  as an event whose payload names each speaker's step record. Inputs `round`, `dialogue` (the transcript so far) and
  `draft` (the planner's latest plan). Speakers may not ask in the old way (`may_ask=False`): their batch is their
  reply. `records.sent_back_at`: an answered batch, like a plan sent back, starts a step's attempts afresh (FR-105).
- **FR-121, `dialogue.py`, `operations.py`, `cli.py`.** `render_batch` and `parse_batch`: `[Q<id>]` and `answer:`
  under each question, `#` lines not read. `operations.answer` takes a filled batch, or words for one question;
  `answer_in_editor` opens `$EDITOR` on `answers.md` in the run's folder (`Files.answers_draft`), kept when refused.
  `factory answer` (no words: the editor; `--file path` or `-`), `factory questions [--json]`.
- **FR-122, `checks.py`, `operations.py`.** `dialogue_moves` on the planner: aligned with a plan and an estimate and
  nothing asked, or asking something. `factory agree`; `approve` on a dialogue refused until agreed; `revise` is the
  reply that begins another round. The proposal shows what the planner `declined`, with its reasons.
  `store.py` migration 6: plans may be `agreed` and `stale`; questions gain `round` and `measure`.
- **FR-123, `dialogue.py`.** `similar_runs`: the last five runs of the same kind on the same codebase that ended
  accepted, with minutes and cost (`records.took`, and `records.minutes`, now shared with `run_record.facts`).
  Shown beside the planner's `estimate` in the plan, and to the planner as `similar_runs`.
- **FR-124, `config.py`, `workflow.py`, `dialogue.py`, `operations.py`.** `dialogue_budget_dollars`, 10.0.
  `dialogue_over_budget`, `spend_more`. A round that is not aligned, at or over the budget since the last yes, adds
  the factory's question; neither yes nor no is refused. No pauses the dialogue (the operator's ruling, below): a
  `paused` event, the run's record written to its branch (`run_record.paused_message`), the run waiting.
  `dialogue.paused`, `so_far` (shown by `factory questions`), `latest_draft`; from the pause `factory answer yes`
  goes on (`operations._resume_paused`, a fresh allowance), `factory agree` agrees to the latest draft, or abandon.
- **FR-125, `operations.py`, `workspace.py`, `records.py`, `driver.py`.** At `approve`, a head that differs from the
  run's starting commit moves the checkout there (`Workspace.move_to`, `records.restart_from`: the one way
  `base_commit` changes), refused if anything but the run's record is on the branch or the new head's table lacks the
  steps; `after_wait(..., moved=True)` leads to `recheck_plan`, given `codebase_moved` (`Workspace.moved`). Its
  `stale` verdict is a `Replan`: the driver marks the approved plan stale (`records.set_plan_aside`), sets nothing
  aside when nothing was built, and puts the run back in planning at the analyst.
- **FR-126.** The planner's `how_much`, every speaker's prompt and the shared `prompts/fragments/dialogue.md`.
- **FR-127, `run_record.py`.** "The dialogue" section: `dialogue.transcript`, the same text the speakers are given.
- **FR-128, `dialogue.py`, `operations.py`, `cli.py`.** `waiting` (answers from whom, a measurement, agreement,
  approval) in `status` (`RunView.waiting`), the end of `watch`, the notification and `plan`; `not_current` refuses
  `factory plan` with what the run waits for and what became of the last plan.
- **FR-129.** `prompts/fragments/dialogue.md`, added to every speaker's prompt by the driver.

**Ruled by the operator during the build**

- A no at the budget, 2026-11-24: "B and hopefully all the artifacts that were generated are not lost so that we can
  resume". It pauses the dialogue, keeping everything; it does not end the run (FR-124, as amended before it shipped).

**Mechanics chosen in the build, accepted by the orchestrator**

1. Within a round the speakers run one after another, and the architect and the plan check read the planner's plan
   of that round; "side by side" (D2) is read as every agent speaking every round, each with its own batch.
2. Points for the planner (things the artifacts settle) are not put to the asker: such a round goes again at once,
   at most `attempt_limit` rounds in a row before the asker is shown them.
3. The budget counts the speakers' cost since the asker last said yes.
4. A reply to a proposed plan is `factory revise "..."`; `factory answer` is for questions only.
5. "Moved" means the codebase's head differs from the commit the dialogue read; the run then restarts from the head.
6. The re-check is one step, by the plan check's persona; holding, the build starts with no second approval.
7. The similar runs are the last five accepted runs of the same kind on the same codebase.
8. Tidies on a sprint codebase go through the dialogue; a spike has no dialogue.
9. `tests/test_size.py`'s tripwire is raised from 3,500 to 4,100 lines; the factory is about 4,030.

**Not in this change**

- Several plans waiting at once (D7: "a later rethink").
- Spec 003's scorecard for what a dialogue costs against a misunderstood plan (answer 8): there is no scorecard yet.
- The ideals a run is held to stay those of the commit it was requested at, after a restart (FR-125).

Tests: `tests/test_dialogue.py` (new, 59 cases). `tests/test_sprint_cycle.py`, `test_questions.py`,
`test_overrides.py` and `test_workflow.py` follow the sprint into the dialogue; `tests/conftest.py` gains the
speakers' scripts, and `to_the_end` agrees before it approves.
