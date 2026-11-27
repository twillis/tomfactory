"""FR-165: a run records how much it changed, the unit its cost is divided by."""
import pytest

from factory import config, operations, records, run_record
from factory.store import open_store
from tests.conftest import commit_files, drive_with, git, script
from tests.fake_agent import FakeAgent


@pytest.mark.fr("FR-165")
def test_an_ended_run_records_its_change_by_kind(home, target, fake_notify):
    drive_with(FakeAgent(script()))
    run = operations.approve(operations.request("Create a hello page", target).id)
    assert run.outcome == "accepted", run.reason
    [event] = [e for e in records.events_after(open_store(home), run.id) if e.kind == "change_size"]
    size = event.payload
    assert size["code"] == {"added": 2, "removed": 0, "files": 1}                 # hello.py, as the fake build wrote it
    assert size["tests"]["files"] == 1 and size["tests"]["added"] > 0           # tests/test_hello.py
    assert "code +2 -0 in 1 files" in event.summary


@pytest.mark.fr("FR-165")
@pytest.mark.parametrize("name, kind", [
    ("app/core.py", "code"), ("tests/test_core.py", "tests"), ("docs/runs/x.md", "docs"), ("CHANGELOG.md", "docs"),
    ("uv.lock", "other"), ("README.md", "code"),
])
def test_each_file_is_counted_under_one_kind(target, name, kind):
    base = git(target, "rev-parse", "HEAD")
    git(target, "checkout", "-q", "-b", "factory/sized")
    commit_files(target, {name: "one\ntwo\n"})
    settings = config.read_target_config(target, base)
    size = run_record.change_size(target, base, "factory/sized", settings)
    assert size[kind] == {"added": 2, "removed": 0, "files": 1}
    assert all(size[other]["files"] == 0 for other in run_record.SIZE_KINDS if other != kind)


@pytest.mark.fr("FR-165")
def test_a_branch_that_is_gone_has_no_size(target):
    base = git(target, "rev-parse", "HEAD")
    assert run_record.change_size(target, base, "factory/nowhere", config.read_target_config(target, base)) is None
