# Change record: the architect's backlog for the factory itself (2026-11-19)

Made outside spec kit with the operator's agreement ("I think all of the architects items
should be addressed"), for spec kit to review later. The findings are in `docs/backlog.md`,
from the factory's own architect persona run once over the factory's code at `26a7e00`.

No requirement changed. Behaviour changed in four places, each a fix the architect named:

- **A run's table is decided once, from its own checkout** (`driver.table_of`). Before, the
  first step was chosen from the operator's working copy and the rest from the checkout, so a
  target with uncommitted spec kit files could start at a step the driver could not find.
- **The checkout starts at the recorded base commit.** Before, the base was read twice, so a
  commit landing in between would have measured every later diff from the wrong place.
- **A question is recorded as a question.** The schema did not allow it, so it was recorded as
  a failed check. Migration v4 widens the list.
- **No default table.** `workflow.get` and `after_wait` no longer fall back to the plain table,
  which gave a wrong answer silently on a spec kit or tidy run.

## What changed, by phase

| Commit | What |
|--------|------|
| `84c5e24` | One judging mechanism (a step with routes; `verdict_accept` gone). The vocabularies (outcomes, failure kinds, verdicts) named once in `workflow.py`, with `End` and `StepResult` refusing other values. Waiting steps name where approval leads. The rules the driver used to make (which checks a step gets, what counts as a question, how a reply failed, when the lead has answered) are pure functions in `workflow.py`. `run_step` is prompt, execute, verify. Inputs are a registry. `validate(table)` refuses an unsound table before a run uses it. Numbered schema migrations; `runs.workflow` renamed `run_kind`. One seam for tests (`operations.launch`). `--kind` replaces `--tidy`. |
| `0d917f8` | The reply's JSON shape is generated from each step's envelope. The rules-in-order, spec kit and asking blocks are shared fragments the driver appends. The proportion rule is stated once, in the test writer's priorities. |
| `4a6810a` | `own_files.py` takes fingerprint, snapshot and restore out of `workspace.py`, which is now the only module that runs git. Each target setting's default is written once and the default `.factory.toml` is generated. One slug function; one front-matter rule; the command line's repeats folded. |
| `5e7d5df` | Tests: each rule tested once at its own level, one whole run per route; refusal and spec kit tests as tables; dead assertions fixed. The requirement gate is part of test collection; `scripts/traceability.py` is gone. |
| next commit | The README's map, rules and step guide brought in line; the docs test derives the commands from the parser and the inputs and modules from the code. Contracts updated. |

## For spec kit to review

- `plan.md` and `tasks.md` of feature 001 still describe `scripts/traceability.py`, the
  `verdict_accept` check and the single plain table. They record what was planned then; this
  record and the contracts say what is true now.
- One backlog entry is left: split tables from rules when a fourth table arrives.
- The code grew by about 170 lines (2,335 to 2,508), mostly `validate`, the migrations and
  the input registry; the tests shrank (3,531 lines and 245 test functions to 3,417 and 216).
