"""Data: everything the factory keeps, behind one gateway.

The gateway has five operations, and each takes a table:

    gw.insert(table, row)                         -> the stored row
    gw.get(table, key)                            -> one row, by its primary key
    gw.query(table, where, order, limit)          -> rows
    gw.update(table, where, changes)              -> the rows it changed
    gw.delete(table, where)                       -> how many it removed

It learns each table's columns from the database itself, so a new table needs its DDL
below and nothing else: no class, no methods. Rows are plain mappings (JSON, with access
by name as a convenience). Conditions are values, not SQL text; table and column names
are checked against the catalog, so nothing a caller passes is ever run as SQL.

There are no rules about runs, plans or steps here. Those are business rules and live in
the control layer, in records.py.

The schema is the contract with the observability app: contracts/run-store.md.
`gw.files` owns every per-run file, so no other module opens a file under the home.
"""
import json
import pathlib
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

VERSION = 2     # of the schema's column types; an older home is refused, not misread

# A column typed "JSON TEXT" is stored as JSON text and handed back parsed.
# A column typed "BOOLEAN" is stored as 1 or 0 and handed back as True or False.
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
    workflow        TEXT    NOT NULL DEFAULT 'change',
    CHECK ((state = 'ended') = (outcome IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_run ON runs ((state != 'ended')) WHERE state != 'ended';
CREATE TABLE IF NOT EXISTS plans (
    run_id            INTEGER NOT NULL REFERENCES runs(id),
    version           INTEGER NOT NULL,
    text              TEXT    NOT NULL,
    ideals_addressed  JSON TEXT NOT NULL,
    conflicts         JSON TEXT NOT NULL,
    comment           TEXT,
    decision          TEXT    NOT NULL CHECK (decision IN ('pending','approved','revised','abandoned')),
    created_at        TEXT    NOT NULL,
    PRIMARY KEY (run_id, version)
);
DROP INDEX IF EXISTS one_approved_plan;     -- a run may now be approved more than once: spec, then plan
CREATE TABLE IF NOT EXISTS steps (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         INTEGER NOT NULL REFERENCES runs(id),
    name           TEXT    NOT NULL,
    kind           TEXT    NOT NULL CHECK (kind IN ('agent','code')),
    persona        TEXT,
    attempt        INTEGER NOT NULL,
    asked          TEXT    NOT NULL,
    produced       JSON TEXT,
    checks         JSON TEXT,
    passed         BOOLEAN,
    failure        TEXT    CHECK (failure IN ('timeout','error','guard','malformed','check')),
    started_at     TEXT    NOT NULL,
    ended_at       TEXT,
    tokens         JSON TEXT,
    cost_estimate  REAL
);
CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    INTEGER NOT NULL REFERENCES runs(id),
    step_id   INTEGER REFERENCES steps(id),
    at        TEXT    NOT NULL,
    kind      TEXT    NOT NULL,
    summary   TEXT    NOT NULL,
    payload   JSON TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS questions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER NOT NULL REFERENCES runs(id),
    step         TEXT    NOT NULL,
    asked_by     TEXT,
    question     TEXT    NOT NULL,
    answer       TEXT,
    answered_by  TEXT    CHECK (answered_by IN ('lead','operator')),
    asked_at     TEXT    NOT NULL,
    answered_at  TEXT
);
CREATE INDEX IF NOT EXISTS events_by_run ON events (run_id, id);
CREATE INDEX IF NOT EXISTS steps_by_run  ON steps  (run_id, id);
"""


ADDED_SINCE = [("runs", "workflow", "TEXT NOT NULL DEFAULT 'change'")]      # (table, column, definition)


def now() -> str:
    """The current time, UTC, ISO 8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class Row(dict):
    """A row: a plain mapping, with `row.column` as a shorter way to write `row["column"]`."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


# ---- conditions: values that say which rows, composed by putting them in a list ----

@dataclass(frozen=True)
class Condition:
    column: str
    test: str           # one of the keys of TESTS
    value: object = None


TESTS = {"eq": "= ?", "ne": "!= ?", "gt": "> ?", "lt": "< ?", "is_null": "IS NULL", "not_null": "IS NOT NULL"}


def eq(column, value) -> Condition:
    return Condition(column, "is_null") if value is None else Condition(column, "eq", value)


def ne(column, value) -> Condition:
    return Condition(column, "ne", value)


def gt(column, value) -> Condition:
    return Condition(column, "gt", value)


def lt(column, value) -> Condition:
    return Condition(column, "lt", value)


def is_null(column) -> Condition:
    return Condition(column, "is_null")


def not_null(column) -> Condition:
    return Condition(column, "not_null")


def conditions(where) -> list[Condition]:
    """Normalise a `where`: a mapping means "all of these are equal"; a list combines several."""
    if not where:
        return []
    if isinstance(where, Condition):
        return [where]
    if isinstance(where, dict):
        return [eq(column, value) for column, value in where.items()]
    return [condition for part in where for condition in conditions(part)]


# ---- the gateway ----

class Gateway:
    def __init__(self, home):
        self.home = pathlib.Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.home / "factory.db", timeout=10, isolation_level=None,
                                  check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode = WAL")
        is_new = not self.db.execute("SELECT 1 FROM sqlite_master WHERE name = 'runs'").fetchone()
        if not is_new and self.db.execute("PRAGMA user_version").fetchone()[0] != VERSION:
            raise RuntimeError(f"{self.home / 'factory.db'} was made by an earlier version of the factory."
                               " Move it aside, or point TOMFACTORY_HOME at a new directory.")
        self.db.executescript(SCHEMA)
        for table, column, definition in ADDED_SINCE:      # columns a store made earlier does not have yet
            if column not in [row["name"] for row in self.db.execute(f"PRAGMA table_info({table})")]:
                self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        self.db.execute(f"PRAGMA user_version = {VERSION}")
        self.files = Files(self.home)
        self._catalog: dict = {}
        self._depth = 0

    # -- the five operations --

    def insert(self, table, row) -> Row:
        columns = self._columns(table, row)
        sql = (f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})"
               if columns else f"INSERT INTO {table} DEFAULT VALUES")
        return self._rows(table, sql + " RETURNING *", self._encode(table, row))[0]

    def get(self, table, key) -> Row:
        primary = self._table(table)["primary_key"]
        if len(primary) != 1:
            raise ValueError(f"{table} has no single-column primary key; use query")
        found = self.query(table, {primary[0]: key})
        if not found:
            raise LookupError(f"there is no row {key} in {table}")
        return found[0]

    def query(self, table, where=None, order=None, limit=None) -> list[Row]:
        info = self._table(table)
        clause, values = self._where(table, where)
        ordering = [order] if order else info["primary_key"]
        self._columns(table, [name.lstrip("-") for name in ordering])
        sql = f"SELECT * FROM {table}{clause} ORDER BY " + ", ".join(
            f"{name[1:]} DESC" if name.startswith("-") else name for name in ordering)
        if limit is not None:
            sql, values = sql + " LIMIT ?", [*values, int(limit)]
        return self._rows(table, sql, values)

    def update(self, table, where, changes) -> list[Row]:
        columns = self._columns(table, changes)
        clause, values = self._where(table, where, required=True)
        assignments = ", ".join(f"{column} = ?" for column in columns)
        return self._rows(table, f"UPDATE {table} SET {assignments}{clause} RETURNING *",
                          [*self._encode(table, changes), *values])

    def delete(self, table, where) -> int:
        clause, values = self._where(table, where, required=True)
        return self.db.execute(f"DELETE FROM {table}{clause}", values).rowcount

    @contextmanager
    def transaction(self):
        """Group several operations so they happen together or not at all. May be nested."""
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

    # -- the catalog: what the database says its tables are --

    def _table(self, table) -> dict:
        if table not in self._catalog:
            known = self.db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                                    (str(table),)).fetchone()
            if not known:
                raise ValueError(f"there is no table named {table!r}")
            described = self.db.execute(f"PRAGMA table_info({table})").fetchall()
            self._catalog[table] = {
                "types": {column["name"]: column["type"].upper() for column in described},
                "primary_key": [column["name"] for column in sorted(described, key=lambda c: c["pk"]) if column["pk"]],
            }
        return self._catalog[table]

    def _columns(self, table, names) -> list[str]:
        """The names given, once each is known to be a column of the table."""
        types = self._table(table)["types"]
        for name in names:
            if name not in types:
                raise ValueError(f"{table} has no column named {name!r}")
        return list(names)

    def _where(self, table, where, required=False):
        parts = conditions(where)
        if required and not parts:
            raise ValueError("this operation needs conditions saying which rows; none were given")
        self._columns(table, [part.column for part in parts])
        clause = " AND ".join(f"{part.column} {TESTS[part.test]}" for part in parts)
        values = [part.value for part in parts if "?" in TESTS[part.test]]
        return (f" WHERE {clause}" if clause else ""), values

    def _encode(self, table, row) -> list:
        types = self._table(table)["types"]
        return [value if value is None
                else json.dumps(value) if types[name].startswith("JSON")
                else int(bool(value)) if types[name] == "BOOLEAN"
                else value
                for name, value in row.items()]

    def _rows(self, table, sql, values) -> list[Row]:
        types = self._table(table)["types"]
        found = []
        for stored in self.db.execute(sql, values).fetchall():
            row = Row(stored)
            for name, value in row.items():
                if value is not None and types[name].startswith("JSON"):
                    row[name] = json.loads(value)
                elif value is not None and types[name] == "BOOLEAN":
                    row[name] = bool(value)
            found.append(row)
        return found


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


def open_store(home) -> Gateway:
    return Gateway(home)
