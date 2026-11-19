# Change record: each run's record is committed with the code (2026-11-19)

Made outside spec kit with the operator's agreement, for spec kit to review later.

**Found** publishing the viewer: "there were no corresponding specs". On the plain cycle the
approved plan, and everything about how a run went, lived only in the factory's local
database, so a codebase the factory built carried no record of why or how. The viewer's past
runs were exported by hand into its `docs/runs/`. Then the operator: "once a run is completed
it should be exported and put into the runs directory".

**Changed** (FR-079, FR-080): one record per run, `docs/runs/<run>-<name>.md`, rendered by
`factory/run_record.py` from the factory's own records, in the format of the hand export.

- On approval of a plan no spec kit stage wrote (`operations.approve`), the record is written
  with the request, anything it was sent back with, and the plan, and committed as
  `factory: approved plan (run N)`.
- When the run ends, whatever the outcome (`driver.end_run`, the one way a run ends), it is
  completed with every step, the outcome and reason, the review and the commits, and
  committed alone as `factory: run record (run N)`, so half-written work is never swept in.
  A run whose checkout is gone (abandoned) gets none. A failure to write it is recorded as
  an event; the run has ended either way.
- The operator is now notified before the record is written. This also fixed a race in
  `test_detached.py`, which read the notifications as soon as the run showed as ended.

There is no shared index of runs in the codebase: every run editing one file would make
branches conflict when merged.

An hour earlier the same session committed the plan alone to `docs/plans/`. That is
superseded by this: one file per run, in one place.

**Tests**: `tests/test_cycle.py` (a run sent back once then accepted, from approval to end; a
run stopped mid-step; a tidy), `tests/test_speckit.py` (no plan record on a spec kit run).
Four commit counts rose.
