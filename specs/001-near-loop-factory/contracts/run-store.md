# Contract: Run Store

The run store is everything the factory keeps: one SQLite file, `factory.db`, and a folder of per-run files, both in the factory's home directory (`~/.tomfactory` or `TOMFACTORY_HOME`). The factory is the only writer. The observability app and any other reader open the database read-only.

Inside the factory, **all persistence goes through `factory/store.py`** (constitution S3). It exposes five repos: `runs`, `plans`, `steps`, `events` — one per table below — and `files`, which owns every per-run file. No other module issues SQL or opens a file under the home directory.

The database schema is the contract between the factory and the observability app. Changing it is a breaking change to the app. `tests/test_store.py` exercises it round trip, including the follow query.

## Opening it

- The factory opens the database in WAL mode, so readers never block the writer and the writer never blocks readers.
- Readers must open it read-only and must not hold long transactions.

## Tables

```sql
CREATE TABLE runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request         TEXT    NOT NULL,
    target          TEXT    NOT NULL,
    base_commit     TEXT    NOT NULL,
    branch          TEXT,                 -- set in the creating transaction
    workspace       TEXT,                 -- set in the creating transaction
    state           TEXT    NOT NULL CHECK (state IN
                      ('planning','awaiting_approval','working','ended')),
    current_step    TEXT,                 -- the step being run, or to run next
    outcome         TEXT    CHECK (outcome IN ('accepted','rejected','needs-me')),
    reason          TEXT,
    ideals          TEXT    NOT NULL DEFAULT '',
    attempt_limit   INTEGER NOT NULL DEFAULT 3,
    driver_pid      INTEGER,              -- the driver process, while one is running
    driver_started  TEXT,                 -- that process's start time, to tell it from a reused pid
    child_pgid      INTEGER,              -- the process group of the step's child, while one is running
    created_at      TEXT    NOT NULL,
    ended_at        TEXT,
    CHECK ((state = 'ended') = (outcome IS NOT NULL))
);

-- At most one run that has not ended (FR-033).
CREATE UNIQUE INDEX one_open_run ON runs ((state != 'ended')) WHERE state != 'ended';

CREATE TABLE plans (
    run_id            INTEGER NOT NULL REFERENCES runs(id),
    version           INTEGER NOT NULL,
    text              TEXT    NOT NULL,
    ideals_addressed  TEXT    NOT NULL,   -- JSON list
    conflicts         TEXT    NOT NULL,   -- JSON list
    comment           TEXT,
    decision          TEXT    NOT NULL CHECK (decision IN
                        ('pending','approved','revised','abandoned')),
    created_at        TEXT    NOT NULL,
    PRIMARY KEY (run_id, version)
);

-- At most one approved plan per run.
CREATE UNIQUE INDEX one_approved_plan ON plans (run_id) WHERE decision = 'approved';

CREATE TABLE steps (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         INTEGER NOT NULL REFERENCES runs(id),
    name           TEXT    NOT NULL,
    kind           TEXT    NOT NULL CHECK (kind IN ('agent','code')),
    persona        TEXT,                 -- name of the persona, for agent steps
    attempt        INTEGER NOT NULL,     -- 1, 2, 3 … for this step name in this run
    asked          TEXT    NOT NULL,     -- the full prompt, or the command, or '' for a step with nothing to ask
    produced       TEXT,                 -- JSON: the envelope, or a code step's output summary
    checks         TEXT,                 -- JSON list of {"name","passed","note"}, in the order run
    passed         INTEGER,              -- 1, 0, or NULL while running
    failure        TEXT    CHECK (failure IN
                     ('timeout','error','guard','malformed','check')),
    started_at     TEXT    NOT NULL,
    ended_at       TEXT,
    tokens         TEXT,                 -- JSON object
    cost_estimate  REAL
);

CREATE TABLE events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    INTEGER NOT NULL REFERENCES runs(id),
    step_id   INTEGER REFERENCES steps(id),
    at        TEXT    NOT NULL,
    kind      TEXT    NOT NULL,
    summary   TEXT    NOT NULL,
    payload   TEXT    NOT NULL           -- JSON object
);

CREATE INDEX events_by_run ON events (run_id, id);
CREATE INDEX steps_by_run  ON steps  (run_id, id);
```

All timestamps are UTC in ISO 8601 form, for example `2026-11-18T21:04:05Z`.

## What the repos return

Each repo returns typed records, not bare dictionaries (constitution S5). They are dataclasses defined in `factory/store.py` — `Run`, `Plan`, `StepRecord`, `Event` — with one field per column, the field's type, and the allowed values spelled out for `state`, `outcome`, `decision`, `kind` and `failure`. JSON columns arrive already parsed. `dataclasses.asdict` gives the plain form the command line prints as JSON.

## Rules the repos keep

| Rule | Kept by |
|------|---------|
| Creating a run inserts the row and sets `branch` and `workspace`, which contain the new id, in one transaction | `runs.create` |
| Branch name: `factory/<id>-<slug>`. The slug is the request's first five words, lower-cased, every run of characters other than `a–z` and `0–9` replaced by `-`, trimmed of `-`, cut to 40 characters; `run` if that leaves nothing | `runs.create` |
| Changing a run's state writes a `run_state` event. The caller sets the state; the repo keeps the history | `runs.set_state`, `runs.end` |
| Ending a run sets `state`, `outcome`, `reason` and `ended_at` together and clears `driver_pid`, `driver_started` and `child_pgid` | `runs.end` |
| A step's attempt number is one more than the number of earlier records with the same run and name | `steps.start` |
| An event's `id` only increases | `events.add` |

The two unique indexes are a backstop. The rules "one open run" and "one approved plan" are decided in `factory/operations.py`, where the operator sees a readable refusal.

## The one query for following a run

```sql
SELECT id, step_id, at, kind, summary, payload
FROM events
WHERE run_id = :run AND id > :last_seen
ORDER BY id
LIMIT 500;
```

A live view runs it every second or so with the last id it saw. A history view runs it from zero. They are the same query.

## Event kinds

| Kind | When | Written by |
|------|------|------------|
| `run_state` | The run changed state | the runs repo |
| `step_start`, `step_end` | A step began or finished | the driver |
| `agent_text` | The agent wrote text | the driver, from the adapter |
| `tool_call` | The agent used a tool; one event per use | the driver, from the adapter |
| `check` | A check ran; the payload has its name, result and note | the driver |
| `denied` | The agent program refused something the agent tried; the payload has the action and path | the driver, from the adapter |
| `guard` | A forbidden change was found and undone; the payload lists the files | the driver |
| `commit` | The factory committed to the run's branch | the driver |
| `notify` | A notification was sent, or failed to send | the end-of-run and wait routines |
| `error` | Something went wrong in the factory itself | the driver |

## Guarantees to readers

1. **Rows appear as things happen.** A step row exists from the moment the step starts; `ended_at`, `passed` and `checks` are filled in when it finishes.
2. **Rows are never deleted or rewritten**, with two exceptions: a `steps` row is completed once when its step ends, and a `runs` row is updated as the run moves on.
3. **`events.id` only increases**, so the cursor query never misses or repeats an event.
4. **Event kinds may be added.** A reader must ignore kinds it does not know.
5. **A run that is `ended` never changes again.**
6. **A run can be dead without yet being marked ended.** If the driver was killed, the row stays `planning` or `working` until the next `factory` command notices and ends it as needs-me, "interrupted". A reader that wants to be exact must treat a `planning` or `working` run as stopped when no process with `driver_pid` and `driver_started` exists. The observability app's first versions may simply show the state as stored.

## Per-run files (the `files` repo)

| Path under the home directory | What it is | Written through |
|-------------------------------|------------|-----------------|
| `ideals.md` | The operator's ideals | the operator's editor |
| `runs/<id>/driver.log` | The driver's own output for that run | `files.driver_log(run_id)` |
| `runs/<id>/steps/<step-id>.jsonl` | The agent program's raw lines for that step, exactly as received | `files.raw_sink(run_id, step_id)` |
| `runs/<id>/steps/<step-id>.stderr` | Anything the step's process wrote to standard error | `files.stderr_file(run_id, step_id)` |
| `runs/<id>/displaced/` | Changed versions of the factory's own files, copied here before they are put back, so nothing an operator edited mid-run is lost | `files.displaced_dir(run_id)` |
| `runs/<id>/snapshot/` | A copy of `personas/`, `prompts/`, the factory's package folder and `ideals.md` taken when the run starts, used to restore them if a step changes them | `files.snapshot_dir(run_id)` |
| `workspaces/<id>/` | The run's checkout of the target codebase | `factory/workspace.py`, at the path `files.workspace_path(run_id)` gives |

The raw files are the record of last resort. Everything a reader needs is in the database.
