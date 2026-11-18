"""Data: everything the factory keeps, behind five repos.

    store.runs    one row per run; changing a run's state writes its own history
    store.plans   the versions of a run's plan
    store.steps   one row per execution of a step
    store.events  an append-only log, read with one "after this id" query
    store.files   every per-run file on disk

No other module issues SQL or opens a file under the home directory. The schema is the
contract with the observability app: see specs/001-near-loop-factory/contracts/run-store.md.
"""
import json
import pathlib
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

STATES = ("planning", "awaiting_approval", "working", "ended")
OUTCOMES = ("accepted", "rejected", "needs-me")
DECISIONS = ("pending", "approved", "revised", "abandoned")
KINDS = ("agent", "code")
FAILURES = ("timeout", "error", "guard", "malformed", "check")

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request         TEXT    NOT NULL,
    target          TEXT    NOT NULL,
    base_commit     TEXT    NOT NULL,
    branch          TEXT,
    workspace       TEXT,
    state           TEXT    NOT NULL CHECK (state IN ('planning','awaiting_approval','working','ended')),
    current_step    TEXT,
    outcome         TEXT    CHECK (outcome IN ('accepted','rejected','needs-me')),
    reason          TEXT,
    ideals          TEXT    NOT NULL DEFAULT '',
    attempt_limit   INTEGER NOT NULL DEFAULT 3,
    driver_pid      INTEGER,
    driver_started  TEXT,
    child_pgid      INTEGER,
    created_at      TEXT    NOT NULL,
    ended_at        TEXT,
    CHECK ((state = 'ended') = (outcome IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_run ON runs ((state != 'ended')) WHERE state != 'ended';
CREATE TABLE IF NOT EXISTS plans (
    run_id            INTEGER NOT NULL REFERENCES runs(id),
    version           INTEGER NOT NULL,
    text              TEXT    NOT NULL,
    ideals_addressed  TEXT    NOT NULL,
    conflicts         TEXT    NOT NULL,
    comment           TEXT,
    decision          TEXT    NOT NULL CHECK (decision IN ('pending','approved','revised','abandoned')),
    created_at        TEXT    NOT NULL,
    PRIMARY KEY (run_id, version)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_approved_plan ON plans (run_id) WHERE decision = 'approved';
CREATE TABLE IF NOT EXISTS steps (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         INTEGER NOT NULL REFERENCES runs(id),
    name           TEXT    NOT NULL,
    kind           TEXT    NOT NULL CHECK (kind IN ('agent','code')),
    persona        TEXT,
    attempt        INTEGER NOT NULL,
    asked          TEXT    NOT NULL,
    produced       TEXT,
    checks         TEXT,
    passed         INTEGER,
    failure        TEXT    CHECK (failure IN ('timeout','error','guard','malformed','check')),
    started_at     TEXT    NOT NULL,
    ended_at       TEXT,
    tokens         TEXT,
    cost_estimate  REAL
);
CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    INTEGER NOT NULL REFERENCES runs(id),
    step_id   INTEGER REFERENCES steps(id),
    at        TEXT    NOT NULL,
    kind      TEXT    NOT NULL,
    summary   TEXT    NOT NULL,
    payload   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS events_by_run ON events (run_id, id);
CREATE INDEX IF NOT EXISTS steps_by_run  ON steps  (run_id, id);
"""


def now() -> str:
    """The current time, UTC, ISO 8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _one_of(value, allowed, what, optional=False):
    if value is None and optional:
        return
    if value not in allowed:
        raise ValueError(f"{what} must be one of {', '.join(allowed)}; got {value!r}")


# ---- the typed records the repos return (constitution S5) ----

@dataclass(frozen=True)
class Run:
    id: int
    request: str
    target: str
    base_commit: str
    branch: str | None
    workspace: str | None
    state: str              # one of STATES
    current_step: str | None
    outcome: str | None     # one of OUTCOMES, once ended
    reason: str | None
    ideals: str
    attempt_limit: int
    driver_pid: int | None
    driver_started: str | None
    child_pgid: int | None
    created_at: str
    ended_at: str | None

    def __post_init__(self):
        _one_of(self.state, STATES, "state")
        _one_of(self.outcome, OUTCOMES, "outcome", optional=True)


@dataclass(frozen=True)
class Plan:
    run_id: int
    version: int
    text: str
    ideals_addressed: list
    conflicts: list
    comment: str | None
    decision: str           # one of DECISIONS
    created_at: str

    def __post_init__(self):
        _one_of(self.decision, DECISIONS, "decision")


@dataclass(frozen=True)
class StepRecord:
    id: int
    run_id: int
    name: str
    kind: str               # one of KINDS
    persona: str | None
    attempt: int
    asked: str
    produced: dict | None
    checks: list | None     # [{"name", "passed", "note"}], in the order run
    passed: bool | None     # None while running
    failure: str | None     # one of FAILURES
    started_at: str
    ended_at: str | None
    tokens: dict | None
    cost_estimate: float | None

    def __post_init__(self):
        _one_of(self.kind, KINDS, "kind")
        _one_of(self.failure, FAILURES, "failure", optional=True)


@dataclass(frozen=True)
class Event:
    id: int
    run_id: int
    step_id: int | None
    at: str
    kind: str
    summary: str
    payload: dict


# ---- the repos ----

class _Repo:
    def __init__(self, store):
        self.store = store
        self.db = store.db


class Runs(_Repo):
    CHANGEABLE = ("current_step", "driver_pid", "driver_started", "child_pgid")

    def create(self, request, target, base_commit, ideals="", attempt_limit=3, current_step=None) -> Run:
        with self.store.transaction():
            cursor = self.db.execute(
                "INSERT INTO runs (request, target, base_commit, state, current_step, ideals,"
                " attempt_limit, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (request, str(target), base_commit, "planning", current_step, ideals, attempt_limit, now()))
            run_id = cursor.lastrowid
            self.db.execute("UPDATE runs SET branch = ?, workspace = ? WHERE id = ?",
                            (f"factory/{run_id}-{slug(request)}",
                             str(self.store.files.workspace_path(run_id)), run_id))
            self.store.events.add(run_id, "run_state", "planning", {"state": "planning"})
        return self.get(run_id)

    def get(self, run_id) -> Run:
        row = self.db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise LookupError(f"there is no run {run_id}")
        return Run(**dict(row))

    def latest(self) -> Run | None:
        runs = self.all(limit=1)
        return runs[0] if runs else None

    def all(self, limit=20) -> list[Run]:
        rows = self.db.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))
        return [Run(**dict(row)) for row in rows]

    def open(self) -> Run | None:
        row = self.db.execute("SELECT * FROM runs WHERE state != 'ended'").fetchone()
        return Run(**dict(row)) if row else None

    def update(self, run_id, **fields) -> Run:
        """Change the fields that move as a run is carried forward. Nothing else may change."""
        for name in fields:
            if name not in self.CHANGEABLE:
                raise ValueError(f"{name} is not a field that may change")
        if fields:
            assignments = ", ".join(f"{name} = ?" for name in fields)
            self.db.execute(f"UPDATE runs SET {assignments} WHERE id = ?", (*fields.values(), run_id))
        return self.get(run_id)

    def set_state(self, run_id, state, **fields) -> Run:
        """Set a run's state. The repo writes the `run_state` event; the caller does not."""
        _one_of(state, STATES[:-1], "state")  # a run is ended only through end()
        with self.store.transaction():
            self.db.execute("UPDATE runs SET state = ? WHERE id = ?", (state, run_id))
            run = self.update(run_id, **fields)
            self.store.events.add(run_id, "run_state", state,
                                  {"state": state, "current_step": run.current_step})
        return run

    def end(self, run_id, outcome, reason) -> Run:
        """End a run: state, outcome, reason and end time together, exactly once."""
        _one_of(outcome, OUTCOMES, "outcome")
        with self.store.transaction():
            if self.get(run_id).state == "ended":
                raise ValueError(f"run {run_id} has already ended")
            self.db.execute(
                "UPDATE runs SET state = 'ended', outcome = ?, reason = ?, ended_at = ?,"
                " driver_pid = NULL, driver_started = NULL, child_pgid = NULL WHERE id = ?",
                (outcome, reason, now(), run_id))
            self.store.events.add(run_id, "run_state", f"ended: {outcome}",
                                  {"state": "ended", "outcome": outcome, "reason": reason})
        return self.get(run_id)


class Plans(_Repo):
    def add(self, run_id, text, ideals_addressed, conflicts) -> Plan:
        with self.store.transaction():
            version = 1 + self.db.execute(
                "SELECT count(*) FROM plans WHERE run_id = ?", (run_id,)).fetchone()[0]
            self.db.execute(
                "INSERT INTO plans VALUES (?,?,?,?,?,NULL,'pending',?)",
                (run_id, version, text, json.dumps(ideals_addressed), json.dumps(conflicts), now()))
        return self.list(run_id)[-1]

    def list(self, run_id) -> list[Plan]:
        rows = self.db.execute("SELECT * FROM plans WHERE run_id = ? ORDER BY version", (run_id,))
        return [Plan(**{**dict(row), "ideals_addressed": json.loads(row["ideals_addressed"]),
                        "conflicts": json.loads(row["conflicts"])}) for row in rows]

    def current(self, run_id) -> Plan | None:
        plans = self.list(run_id)
        return plans[-1] if plans else None

    def decide(self, run_id, version, decision, comment=None) -> Plan:
        _one_of(decision, DECISIONS, "decision")
        self.db.execute("UPDATE plans SET decision = ?, comment = coalesce(?, comment)"
                        " WHERE run_id = ? AND version = ?", (decision, comment, run_id, version))
        return self.list(run_id)[version - 1]


class Steps(_Repo):
    def start(self, run_id, name, kind, persona, asked) -> StepRecord:
        """Record that a step has begun, so a run in progress shows its current step."""
        _one_of(kind, KINDS, "kind")
        with self.store.transaction():
            cursor = self.db.execute(
                "INSERT INTO steps (run_id, name, kind, persona, attempt, asked, started_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (run_id, name, kind, persona, self.count(run_id, name) + 1, asked, now()))
        return self.get(cursor.lastrowid)

    def finish(self, step_id, produced, checks, passed, failure=None, tokens=None,
               cost_estimate=None) -> StepRecord:
        _one_of(failure, FAILURES, "failure", optional=True)
        if self.get(step_id).ended_at is not None:
            raise ValueError(f"step {step_id} has already finished")
        self.db.execute(
            "UPDATE steps SET produced = ?, checks = ?, passed = ?, failure = ?, tokens = ?,"
            " cost_estimate = ?, ended_at = ? WHERE id = ?",
            (_json(produced), json.dumps(checks), int(bool(passed)), failure, _json(tokens),
             cost_estimate, now(), step_id))
        return self.get(step_id)

    def get(self, step_id) -> StepRecord:
        row = self.db.execute("SELECT * FROM steps WHERE id = ?", (step_id,)).fetchone()
        if row is None:
            raise LookupError(f"there is no step {step_id}")
        return self._record(row)

    def list(self, run_id) -> list[StepRecord]:
        rows = self.db.execute("SELECT * FROM steps WHERE run_id = ? ORDER BY id", (run_id,))
        return [self._record(row) for row in rows]

    def count(self, run_id, name) -> int:
        """How many times this step has run in this run: its attempts so far."""
        return self.db.execute("SELECT count(*) FROM steps WHERE run_id = ? AND name = ?",
                               (run_id, name)).fetchone()[0]

    @staticmethod
    def _record(row) -> StepRecord:
        data = dict(row)
        for column in ("produced", "checks", "tokens"):
            data[column] = json.loads(data[column]) if data[column] is not None else None
        data["passed"] = None if data["passed"] is None else bool(data["passed"])
        return StepRecord(**data)


class Events(_Repo):
    def add(self, run_id, kind, summary, payload=None, step_id=None) -> Event:
        at = now()
        cursor = self.db.execute(
            "INSERT INTO events (run_id, step_id, at, kind, summary, payload) VALUES (?,?,?,?,?,?)",
            (run_id, step_id, at, kind, summary, json.dumps(payload or {})))
        return Event(cursor.lastrowid, run_id, step_id, at, kind, summary, payload or {})

    def after(self, run_id, last_seen=0, limit=500) -> list[Event]:
        """The one query for following a run: live view and history are the same query."""
        rows = self.db.execute(
            "SELECT id, run_id, step_id, at, kind, summary, payload FROM events"
            " WHERE run_id = ? AND id > ? ORDER BY id LIMIT ?", (run_id, last_seen, limit))
        return [self._record(row) for row in rows]

    def for_step(self, step_id) -> list[Event]:
        rows = self.db.execute("SELECT * FROM events WHERE step_id = ? ORDER BY id", (step_id,))
        return [self._record(row) for row in rows]

    @staticmethod
    def _record(row) -> Event:
        return Event(**{**dict(row), "payload": json.loads(row["payload"])})


class Files:
    """Every per-run file. Other modules are handed sinks and open files, never paths to choose."""

    def __init__(self, home):
        self.home = pathlib.Path(home)

    def workspace_path(self, run_id) -> pathlib.Path:
        return self.home / "workspaces" / str(run_id)

    def snapshot_dir(self, run_id) -> pathlib.Path:
        return self._run_dir(run_id) / "snapshot"

    def displaced_dir(self, run_id) -> pathlib.Path:
        """Where changed versions of the factory's own files are kept when they are put back."""
        return self._run_dir(run_id) / "displaced"

    def raw_sink(self, run_id, step_id):
        """A function that appends each line it is given to the step's raw event file."""
        file = open(self._step_file(run_id, step_id, "jsonl"), "a", buffering=1)

        def sink(line):
            file.write(line + "\n")
        return sink

    def stderr_file(self, run_id, step_id):
        return open(self._step_file(run_id, step_id, "stderr"), "a")

    def driver_log(self, run_id):
        return open(self._run_dir(run_id) / "driver.log", "a")

    def _run_dir(self, run_id) -> pathlib.Path:
        path = self.home / "runs" / str(run_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _step_file(self, run_id, step_id, extension) -> pathlib.Path:
        folder = self._run_dir(run_id) / "steps"
        folder.mkdir(exist_ok=True)
        return folder / f"{step_id}.{extension}"


class Store:
    def __init__(self, home):
        self.home = pathlib.Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.home / "factory.db", timeout=10, isolation_level=None,
                                  check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.executescript(SCHEMA)
        self._depth = 0
        self.files = Files(self.home)
        self.events = Events(self)
        self.runs, self.plans, self.steps = Runs(self), Plans(self), Steps(self)

    @contextmanager
    def transaction(self):
        """Group several statements so they happen together or not at all. May be nested."""
        self._depth += 1
        try:
            if self._depth == 1:
                self.db.execute("BEGIN IMMEDIATE")
            yield
            if self._depth == 1:
                self.db.execute("COMMIT")
        except BaseException:
            if self._depth == 1:
                self.db.execute("ROLLBACK")
            raise
        finally:
            self._depth -= 1


def open_store(home) -> Store:
    return Store(home)


def slug(request) -> str:
    """The readable part of a run's branch name: its first five words, made safe."""
    words = " ".join(request.split()[:5]).lower()
    return re.sub(r"[^a-z0-9]+", "-", words).strip("-")[:40].strip("-") or "run"


def _json(value):
    return None if value is None else json.dumps(value)
