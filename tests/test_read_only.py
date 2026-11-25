"""Reading without side effects, and a brief status for a board (FR-146, FR-147).

`factory show` and `factory status` take `--read-only`: the home's database is opened read-only, nothing is
reconciled or migrated, and a home this version would have to change is refused, saying why. `factory status
--brief` gives each recent run as a board needs it, without the steps' prompts or bodies, so it does not grow with
them.
"""
import json
import sqlite3

import pytest

from factory import cli, driver, operations, proc, records
from factory.store import VERSION, open_store
from tests.conftest import drive_with, script
from tests.fake_agent import FakeAgent


def a_run(target, request="Add a greeting"):
    drive_with(FakeAgent(script()))
    return operations.request(request, target)


def database(home):
    """Everything the home's database holds, and its version: what a write or a migration would change."""
    with sqlite3.connect(home / "factory.db") as db:
        return [*db.iterdump(), db.execute("PRAGMA user_version").fetchone()[0]]


@pytest.fixture
def orphaned(home, target, fake_notify, monkeypatch):
    """A planning run whose driver has died: any ordinary command ends it as interrupted."""
    run = a_run(target)
    records.set_state(open_store(home), run.id, "planning", current_step="plan", driver_pid=999999,
                      driver_started="long ago")
    monkeypatch.setattr(proc, "is_alive", lambda pid, started: False)
    return run


# ---- FR-146: --read-only reads and changes nothing ----

@pytest.mark.fr("FR-146")
@pytest.mark.parametrize("command", [["show", "--json", "--read-only"], ["status", "--json", "--read-only"],
                                     ["status", "--brief", "--read-only"], ["show", "--read-only"],
                                     ["status", "--read-only"]])
def test_a_read_only_read_leaves_a_run_whose_driver_died_as_it_was_and_the_database_unchanged(
        home, orphaned, capsys, monkeypatch, command):
    monkeypatch.setattr(driver, "end_run", lambda *args: pytest.fail("a run was ended, its processes stopped"))
    before = database(home)
    assert cli.main(command) == 0
    assert str(orphaned.id) in capsys.readouterr().out
    assert database(home) == before
    assert open_store(home).get("runs", orphaned.id).state == "planning"      # not ended as interrupted


@pytest.mark.fr("FR-146")
def test_without_read_only_the_same_read_ends_that_run_as_before(home, orphaned):
    assert operations.show(orphaned.id).run.reason == "interrupted"


@pytest.mark.fr("FR-146")
def test_a_home_older_than_this_factory_is_refused_read_only_and_not_migrated(home, target, fake_notify):
    run = a_run(target)
    operations.abandon(run.id)
    with sqlite3.connect(home / "factory.db") as db:
        db.execute(f"PRAGMA user_version = {VERSION - 1}")
    before = database(home)
    with pytest.raises(operations.Refused, match=f"version {VERSION - 1}.*this factory reads version {VERSION}"):
        operations.show(run.id, read_only=True)
    assert database(home) == before


@pytest.mark.fr("FR-146")
def test_a_home_with_no_database_is_refused_read_only_and_nothing_is_made(tmp_path, monkeypatch):
    monkeypatch.setenv("TOMFACTORY_HOME", str(tmp_path / "nowhere"))
    with pytest.raises(operations.Refused, match="no factory database"):
        operations.status(read_only=True)
    assert not (tmp_path / "nowhere").exists()


@pytest.mark.fr("FR-146")
def test_a_store_opened_read_only_cannot_write(home, target, fake_notify):
    run = a_run(target)
    store = open_store(home, read_only=True)
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        records.event(store, run.id, "note", "written")


# ---- FR-147: status --brief, what a board needs ----

BRIEF_KEYS = ["id", "state", "outcome", "request_words", "current_step", "stages"]


@pytest.mark.fr("FR-147")
def test_status_brief_gives_each_run_newest_first_without_its_steps(home, target, fake_notify, capsys):
    first = a_run(target, "Add a greeting")
    operations.abandon(first.id)
    second = a_run(target, " ".join(f"word{n}" for n in range(30)))
    capsys.readouterr()
    assert cli.main(["status", "--brief"]) == 0
    brief = json.loads(capsys.readouterr().out)
    assert [list(run) for run in brief] == [BRIEF_KEYS, BRIEF_KEYS]
    newest, oldest = brief
    assert (newest["id"], newest["state"], newest["outcome"], newest["current_step"]) == (
        second.id, "awaiting_approval", None, "plan")
    assert newest["request_words"] == " ".join(f"word{n}" for n in range(20)) + " …"
    assert (oldest["id"], oldest["outcome"], oldest["request_words"]) == (first.id, "rejected", "Add a greeting")
    assert newest["stages"] == [dict(vars(stage)) for stage in operations.show(second.id).stages]


@pytest.mark.fr("FR-147")
@pytest.mark.parametrize("limit, shown", [(["--limit", "1"], 1), (["--limit", "5"], 3), ([], 3)])
def test_status_takes_a_limit(home, target, fake_notify, capsys, limit, shown):
    for _ in range(3):
        operations.abandon(a_run(target).id)
    capsys.readouterr()
    assert cli.main(["status", "--brief", *limit]) == 0
    assert len(json.loads(capsys.readouterr().out)) == shown


@pytest.mark.fr("FR-147")
def test_status_brief_does_not_grow_with_what_the_steps_were_asked(home, target, fake_notify, capsys):
    run = a_run(target)
    capsys.readouterr()
    cli.main(["status", "--brief"])
    small = len(capsys.readouterr().out)
    with sqlite3.connect(home / "factory.db") as db:
        db.execute("UPDATE steps SET asked = ?, produced = ? WHERE run_id = ?",
                   ("x" * 100_000, json.dumps({"plan": "y" * 100_000}), run.id))
    cli.main(["status", "--brief"])
    assert len(capsys.readouterr().out) == small
    cli.main(["status", "--json"])
    assert len(capsys.readouterr().out) > 200_000                          # the full form carries them
