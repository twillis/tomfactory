# Change record: a run's stages, published (2026-11-25)

Made outside spec kit, for spec kit to review later. Built as FR-145.

**Asked for by the operator.** In the viewer, a pipeline strip on each run's page (the run's stages left to right,
each done, current or still to come, and failed or sent back where that happened) and a board on the home page (one
card per run, in a column by stage group, the column that waits on him the most useful). The viewer must not keep its
own copy of the step tables, so the factory publishes each run's stages and the viewer draws them. The mechanics are
the orchestrator's.

**Changed**

1. **`workflow.py`**: the vocabularies `STAGE_STATES` (done, current, to-come, failed, skipped), `GROUPS` (planning,
   waiting, building, reviewing), `WAITS` (approval) and `DIALOGUE_WAITS` (answers, agreement, approval); and
   `main_path(steps)`, the steps a run goes through when nothing is sent back: from the first, each one's `on_pass`,
   past a wait to its `on_approve`, to the end. `mend_tests` and `recheck_plan`, reached only by a route or a moved
   codebase, are not on it.
2. **`tables.py`**: `STAGE_GROUPS`, which group each step's stage is shown in, and `group_of(name)`. A list, not a
   rule derived from what a step may change, so a newcomer reads it at a glance; a test holds every step of every
   table to exactly one group, so a new step cannot be left out.
3. **`operations.py`**: the published shape `Stage` (name, by, group, state, tries) and `stages(store, run)`.
   `RunView` gains `stages`; `show` (a whole run) and `status` fill it, so `factory show --json` and
   `factory status --json` carry it (the command line's `print_json` already turns dataclasses into JSON).
   The pipeline is the run's own table (`driver.table_of`, so its kind, its codebase's cycle and spec kit, as of its
   starting commit) along its main path, the operator's waits after the step that waits, and any step off the path
   the run took shown before the step it leads to. The state comes from where the run is: the wait it waits at
   (from `dialogue.waiting`, a pending question, or else approval) or the step it is on. Stages before that are done,
   except a step never run (skipped), a dialogue's answers where none were asked (skipped), and advice that failed and
   was carried past (failed); stages after it are to come, or skipped once the run has ended. An ended run that stopped
   short is failed where it stopped: at the step that failed, or, where the step it is on passed (abandoned at a wait,
   interrupted between steps), at the stage after it. An accepted or answered run is done throughout.
4. **`README.md`**: under "A run, start to finish", the shape, every field and every state.
5. **`specs/001-near-loop-factory/spec.md`**: FR-145.
6. **`tests/test_stages.py`**: the tests, each naming FR-145, written first and seen to fail.
7. **`tests/test_size.py`**: the tripwire on the factory's own code (FR-039) raised from 4,400 to 4,500 lines, with
   the reason beside it, as for each feature before: this change took it from about 4,350 to about 4,450, and FR-146 and FR-147 to about 4,495, five lines under it.

The suite: 654 passed before, 703 after (49 new, counting each parametrised case).

**Mechanics chosen in the build, for the operator to confirm**

- A run whose table can no longer be read, or that took a step its table no longer has, has `"stages": []`. The tables
  are code and change; `table_of` gives today's table for the run's settings, not the one it ran on. On bttr_erp, run
  87 (a tidy planned with `plan`, before a sprint codebase's tidies were planned in the dialogue) has none, and run
  18 (spec kit, before spec kit runs had a retro) shows `retro` as skipped, which is true: it never ran. Keeping each
  run's table on the run would give every old run its own; that is a larger change than this.
- A dialogue goes round, and the strip is a line: in round 2 the speakers before the current one are done and the
  rest, the answers among them, are to come again. The round is not published; `waiting` and the plan already say it.
- `factory status --json` carries every step's prompt (`asked`), about 20 MB for ten runs on bttr_erp. Settled below
  by FR-147, `status --brief`.

**Evidence.** Against a copy of the operator's home: run 98 (dialogue, accepted, the test sent back once) is done
throughout, `build` and `test` with two tries; run 99 (planning, round 2) has the analyst done and the planner
current; run 88 (spike, answered) is done throughout with no wait; run 18 (spec kit) is done but for `retro`, skipped;
run 87 has none, as above.

## Added the same day: read-only reads and a brief status (FR-146, FR-147)

At the operator's word, before merge: the viewer reads through the factory's command line, and must not change the
home by reading it, nor read 20 MB for a board.

1. **FR-146, `--read-only`** on `factory show` and `factory status`. `store.open_store(home, read_only=True)` opens
   `factory.db` with SQLite's `mode=ro` URI, sets no journal mode, and refuses, saying why, a home with no database
   or one at another version than this factory's (`_check_up_to_date`) instead of making or migrating it.
   `operations._open(read_only)` then skips `reconcile`, so no run whose driver died is ended and no process group
   stopped; `config.home(create=False)` makes no directory. `show` and `status` take `read_only`; the command line's
   `--read-only` passes it. A write through a read-only store fails in SQLite itself.
2. **FR-147, `factory status --brief`**: `operations.brief(limit, read_only)` gives each recent run as `Brief` (id,
   state, outcome, `request_words`: the first 20 words, with … where there were more, `current_step`, stages), newest
   first; `status --limit` (10 by default) applies to both forms. Measured against a copy of the operator's home
   (99 runs): ten runs, 15,442 bytes in 0.16 s, where `status --json` is 19,671,422 bytes in 0.25 s; all 99 runs,
   84,168 bytes in 0.53 s, where `status --json --limit 1000` is 70,564,400 bytes in 1.05 s. The brief form's time is
   mostly reading each run's table from git at its starting commit.
3. **`README.md`**: both flags and the brief shape. **`tests/test_read_only.py`**: their tests, written first.
