"""The data layer: one gateway with five operations that take a table.

    gw.insert(table, row)   gw.get(table, id)   gw.query(table, where, order, limit)
    gw.update(table, where, changes)            gw.delete(table, where)

It knows the tables from the database's own catalog, so a new table needs no code here.
It holds no rules about runs, plans or steps: those live in factory/records.py.
The schema is the contract with the observability app (contracts/run-store.md).
"""
import json
import sqlite3

import pytest

from factory import store as store_module
from factory.store import Row, gt, is_null, ne, open_store


@pytest.fixture
def gw(home):
    return open_store(home)


def a_run(gw, **changes):
    row = {"request": "Create a hello page", "target": "/tmp/t", "base_commit": "abc", "state": "planning",
           "created_at": store_module.now()}
    return gw.insert("runs", {**row, **changes})


@pytest.mark.fr("FR-025")
def test_a_new_store_has_the_contract_schema_in_wal_mode(gw, home):
    db = sqlite3.connect(home / "factory.db")
    names = {row[0] for row in db.execute("select name from sqlite_master")}
    assert {"runs", "plans", "steps", "events", "one_open_run", "events_by_run", "steps_by_run"} <= names
    assert "one_approved_plan" not in names         # a run may be approved more than once: spec, then plan
    assert db.execute("pragma journal_mode").fetchone()[0] == "wal"

    def columns(table):
        return {row[1] for row in db.execute(f"pragma table_info({table})")}

    assert columns("runs") == {"id", "request", "target", "base_commit", "branch", "workspace", "state",
                               "current_step", "outcome", "reason", "ideals", "attempt_limit", "driver_pid",
                               "driver_started", "child_pgid", "created_at", "ended_at"}
    assert columns("steps") == {"id", "run_id", "name", "kind", "persona", "attempt", "asked", "produced",
                                "checks", "passed", "failure", "started_at", "ended_at", "tokens", "cost_estimate"}
    assert columns("plans") == {"run_id", "version", "text", "ideals_addressed", "conflicts", "comment",
                                "decision", "created_at"}
    assert columns("events") == {"id", "run_id", "step_id", "at", "kind", "summary", "payload"}


@pytest.mark.fr("FR-026")
def test_insert_returns_the_stored_row_as_a_plain_mapping(gw):
    run = a_run(gw)
    assert isinstance(run, dict) and isinstance(run, Row)
    assert run["id"] == 1 and run["state"] == "planning" and run["attempt_limit"] == 3   # the schema's default
    assert run.id == 1 and run.state == "planning"          # the same values, by name
    assert run["outcome"] is None and run["ideals"] == ""
    assert json.loads(json.dumps(run)) == run                # it is JSON, nothing more
    with pytest.raises(AttributeError):
        run.no_such_column


@pytest.mark.fr("FR-026")
def test_get_and_query_read_rows_back(gw):
    first = a_run(gw)
    gw.update("runs", {"id": first.id}, {"state": "ended", "outcome": "rejected", "reason": "x"})
    second = a_run(gw, request="Another")
    assert gw.get("runs", second.id) == second
    with pytest.raises(LookupError, match="no row 99 in runs"):
        gw.get("runs", 99)
    assert [r.id for r in gw.query("runs")] == [1, 2]                              # by primary key
    assert [r.id for r in gw.query("runs", order="-id")] == [2, 1]
    assert [r.id for r in gw.query("runs", order="-id", limit=1)] == [2]
    assert [r.id for r in gw.query("runs", {"state": "ended"})] == [1]
    assert [r.id for r in gw.query("runs", {"outcome": None})] == [2]              # None means "is empty"
    assert gw.query("runs", {"state": "working"}) == []


@pytest.mark.fr("FR-025")
def test_conditions_are_values_that_compose(gw):
    run = a_run(gw)
    for number in range(5):
        gw.insert("events", {"run_id": run.id, "at": store_module.now(), "kind": "agent_text" if number % 2 else "check",
                             "summary": f"event {number}", "payload": {"n": number}})
    after_two = gw.query("events", [{"run_id": run.id}, gt("id", 2)])
    assert [e.payload["n"] for e in after_two] == [2, 3, 4]
    assert [e.payload["n"] for e in gw.query("events", [gt("id", 1), ne("kind", "check")])] == [1, 3]
    assert [e.payload["n"] for e in gw.query("events", [gt("id", 0)], order="-id", limit=2)] == [4, 3]
    assert len(gw.query("events", [is_null("step_id")])) == 5
    assert len(gw.query("events", {"run_id": run.id, "kind": "check"})) == 3       # a dict is "all of these"


@pytest.mark.fr("FR-026")
def test_update_and_delete_take_conditions_and_say_what_they_did(gw):
    run = a_run(gw)
    changed = gw.update("runs", {"id": run.id}, {"current_step": "plan", "driver_pid": 42})
    assert [(r.id, r.current_step, r.driver_pid) for r in changed] == [(run.id, "plan", 42)]
    assert gw.update("runs", {"id": 99}, {"current_step": "x"}) == []
    assert gw.get("runs", run.id).current_step == "plan"
    for kind in ("a", "b", "a"):
        gw.insert("events", {"run_id": run.id, "at": store_module.now(), "kind": kind, "summary": "", "payload": {}})
    assert gw.delete("events", {"kind": "a"}) == 2
    assert [e.kind for e in gw.query("events")] == ["b"]
    with pytest.raises(ValueError, match="conditions"):
        gw.delete("events", {})                 # deleting everything must be asked for on purpose
    with pytest.raises(ValueError, match="conditions"):
        gw.update("runs", [], {"current_step": "x"})


@pytest.mark.fr("FR-026")
def test_json_and_yes_no_columns_come_back_as_what_they_are(gw):
    run = a_run(gw)
    step = gw.insert("steps", {"run_id": run.id, "name": "build", "kind": "agent", "attempt": 1, "asked": "p",
                               "started_at": store_module.now()})
    assert step.produced is None and step.checks is None and step.passed is None
    checks = [{"name": "tests_pass", "passed": False, "note": "1 failed"}]
    done = gw.update("steps", {"id": step.id}, {"produced": {"summary": "x"}, "checks": checks, "passed": False,
                                                 "tokens": {"input": 1}})[0]
    assert done.produced == {"summary": "x"} and done.checks == checks and done.tokens == {"input": 1}
    assert done.passed is False
    assert gw.update("steps", {"id": step.id}, {"passed": True})[0].passed is True
    raw = sqlite3.connect(gw.home / "factory.db").execute("select produced, passed from steps").fetchone()
    assert raw == ('{"summary": "x"}', 1)       # on disk: text and a number, as any reader expects


@pytest.mark.fr("FR-037")
def test_a_new_table_needs_no_code_in_the_data_layer(gw):
    """The point of the gateway: inventing a table means writing its DDL and nothing else."""
    gw.db.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, body TEXT NOT NULL,"
                  " tags JSON TEXT, urgent BOOLEAN)")
    note = gw.insert("notes", {"run_id": 7, "body": "remember this", "tags": ["later"], "urgent": True})
    assert (note.id, note.body, note.tags, note.urgent) == (1, "remember this", ["later"], True)
    assert gw.query("notes", {"run_id": 7}) == [note] and gw.get("notes", 1) == note
    assert gw.update("notes", {"id": 1}, {"urgent": False})[0].urgent is False
    assert gw.delete("notes", {"id": 1}) == 1 and gw.query("notes") == []


@pytest.mark.fr("FR-026")
def test_names_come_from_the_catalog_never_from_the_caller(gw):
    with pytest.raises(ValueError, match="no table named"):
        gw.query("runs; drop table runs")
    with pytest.raises(ValueError, match="no column named"):
        gw.insert("runs", {"request": "x", "not a column": 1})
    with pytest.raises(ValueError, match="no column named"):
        gw.query("runs", {"state = 'x' or 1=1 --": 1})
    with pytest.raises(ValueError, match="no column named"):
        gw.query("runs", order="id; drop table runs")
    with pytest.raises(ValueError, match="no column named"):
        gw.update("runs", {"id": 1}, {"nope": 1})
    assert gw.query("runs") == []                 # and nothing was harmed


@pytest.mark.fr("FR-015")
def test_the_database_itself_refuses_values_outside_their_sets(gw):
    with pytest.raises(sqlite3.IntegrityError):
        a_run(gw, state="paused")
    run = a_run(gw)
    with pytest.raises(sqlite3.IntegrityError):
        gw.update("runs", {"id": run.id}, {"outcome": "great", "state": "ended"})
    with pytest.raises(sqlite3.IntegrityError):
        gw.update("runs", {"id": run.id}, {"outcome": "accepted"})          # an outcome without being ended
    with pytest.raises(sqlite3.IntegrityError):
        gw.insert("steps", {"run_id": run.id, "name": "x", "kind": "robot", "attempt": 1, "asked": "",
                            "started_at": store_module.now()})


@pytest.mark.fr("FR-033")
def test_a_second_open_run_is_refused_by_the_database(gw):
    a_run(gw)
    with pytest.raises(sqlite3.IntegrityError):
        a_run(gw, request="another")


@pytest.mark.fr("FR-025")
def test_a_transaction_happens_together_or_not_at_all(gw):
    with pytest.raises(sqlite3.IntegrityError):
        with gw.transaction():
            run = a_run(gw)
            gw.insert("events", {"run_id": run.id, "at": store_module.now(), "kind": "x", "summary": "", "payload": {}})
            a_run(gw, request="a second open run")      # refused: everything above is undone
    assert gw.query("runs") == [] and gw.query("events") == []


@pytest.mark.fr("FR-025")
def test_a_read_only_reader_is_not_blocked_by_an_open_write(gw, home):
    run = a_run(gw)
    gw.db.execute("begin immediate")
    gw.db.execute("insert into events(run_id, at, kind, summary, payload) values (?,?,?,?,?)",
                  (run.id, "now", "agent_text", "uncommitted", "{}"))
    reader = sqlite3.connect(f"file:{home / 'factory.db'}?mode=ro", uri=True, timeout=0.5)
    rows = reader.execute("select summary from events").fetchall()
    assert ("uncommitted",) not in rows         # sees only committed rows, and does not wait
    assert reader.execute("select count(*) from runs").fetchone() == (1,)
    gw.db.execute("rollback")


@pytest.mark.fr("FR-025")
@pytest.mark.fr("FR-029")
def test_per_run_files_are_reached_only_through_the_store(gw, home):
    sink = gw.files.raw_sink(7, 3)
    sink('{"type":"assistant"}')
    sink('{"type":"result"}')
    raw = home / "runs" / "7" / "steps" / "3.jsonl"
    assert raw.read_text() == '{"type":"assistant"}\n{"type":"result"}\n'      # on disk as it happens
    with gw.files.stderr_file(7, 3) as err:
        err.write("warning\n")
    assert (home / "runs" / "7" / "steps" / "3.stderr").read_text() == "warning\n"
    with gw.files.driver_log(7) as log:
        log.write("started\n")
    with gw.files.driver_log(7) as log:
        log.write("again\n")
    assert (home / "runs" / "7" / "driver.log").read_text() == "started\nagain\n"
    assert gw.files.snapshot_dir(7) == home / "runs" / "7" / "snapshot"
    assert gw.files.displaced_dir(7) == home / "runs" / "7" / "displaced"
    assert gw.files.workspace_path(7) == home / "workspaces" / "7"
