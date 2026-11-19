"""The run's own checkout: created beside the operator's work, never on top of it."""
import pytest

from factory import workspace
from factory.workspace import Workspace
from tests.conftest import git


@pytest.fixture
def ws(target, tmp_path):
    return Workspace.create(target, tmp_path / "home" / "workspaces" / "1", "factory/1-hello", git(target, "rev-parse", "HEAD"))


def tree(path):
    """Every file under a directory with its bytes, ignoring git's own folder."""
    return {str(f.relative_to(path)): f.read_bytes()
            for f in sorted(path.rglob("*")) if f.is_file() and ".git" not in f.relative_to(path).parts}


@pytest.mark.fr("FR-019")
def test_creating_a_checkout_leaves_the_operators_working_copy_untouched(target, tmp_path):
    (target / ".factory.toml").write_text("# an uncommitted edit\n")
    (target / "scratch.txt").write_text("untracked\n")
    before, head, branch = tree(target), git(target, "rev-parse", "HEAD"), git(target, "branch", "--show-current")

    ws = Workspace.create(target, tmp_path / "ws", "factory/1-hello", git(target, "rev-parse", "HEAD"))

    assert tree(target) == before
    assert git(target, "rev-parse", "HEAD") == head and git(target, "branch", "--show-current") == branch
    assert ws.base_commit == head and ws.branch == "factory/1-hello"
    assert git(ws.path, "branch", "--show-current") == "factory/1-hello"
    assert not (ws.path / "scratch.txt").exists()  # the checkout starts from the commit
    assert "test_command" in (ws.path / ".factory.toml").read_text()

    reopened = Workspace(ws.path, target, ws.branch, ws.base_commit)
    assert reopened.dirty() == {}


@pytest.mark.fr("FR-032")
def test_dirty_lists_what_changed_and_ignores_caches(ws):
    assert ws.dirty() == {}
    (ws.path / "app.py").write_text("print('hi')\n")
    (ws.path / "tests").mkdir()
    (ws.path / "tests" / "test_app.py").write_text("def test(): pass\n")
    (ws.path / ".gitignore").write_text("__pycache__/\n*.pyc\nextra\n")
    (ws.path / ".factory.toml").unlink()
    (ws.path / "__pycache__").mkdir()
    (ws.path / "__pycache__" / "app.pyc").write_text("cache")
    assert set(ws.dirty()) == {"app.py", "tests/test_app.py", ".gitignore", ".factory.toml"}


@pytest.mark.fr("FR-032")
def test_changed_sees_a_second_edit_to_an_already_dirty_file(ws):
    (ws.path / "app.py").write_text("one\n")
    before = ws.dirty()
    assert workspace.changed(before, ws.dirty()) == set()
    (ws.path / "app.py").write_text("two\n")           # edited again
    (ws.path / "new.py").write_text("x\n")             # added
    assert workspace.changed(before, ws.dirty()) == {"app.py", "new.py"}
    (ws.path / "app.py").unlink()                      # an added file removed again
    assert "app.py" in workspace.changed(before, ws.dirty())


@pytest.mark.fr("FR-032")
def test_undo_restores_the_last_commit_exactly(ws):
    clean = tree(ws.path)
    (ws.path / "new.py").write_text("x\n")
    (ws.path / "sub").mkdir()
    (ws.path / "sub" / "deep.py").write_text("y\n")
    (ws.path / ".factory.toml").write_text("tampered\n")
    (ws.path / ".gitignore").unlink()
    ws.undo()
    assert tree(ws.path) == clean and ws.dirty() == {}


@pytest.mark.fr("FR-013")
def test_commit_records_everything_not_ignored_and_nothing_when_clean(ws, target):
    assert ws.commit("nothing to do") is None
    (ws.path / "app.py").write_text("print('hi')\n")
    (ws.path / "__pycache__").mkdir()
    (ws.path / "__pycache__" / "app.pyc").write_text("cache")
    commit = ws.commit("factory: add app")
    assert commit == git(ws.path, "rev-parse", "HEAD") and commit != ws.base_commit
    assert git(ws.path, "show", "--stat", "--format=%an|%s", "HEAD").splitlines()[0] == "tomfactory|factory: add app"
    assert "app.pyc" not in git(ws.path, "show", "--stat", "HEAD")
    assert ws.dirty() == {}
    assert git(target, "rev-parse", "HEAD") == ws.base_commit  # the operator's branch did not move


@pytest.mark.fr("FR-012")
def test_diff_since_base_is_the_runs_whole_change(ws):
    assert ws.diff_since_base() == ""
    (ws.path / "app.py").write_text("print('hi')\n")
    ws.commit("one")
    (ws.path / "app.py").write_text("print('hello')\n")
    ws.commit("two")
    diff = ws.diff_since_base()
    assert "+print('hello')" in diff and "app.py" in diff and "print('hi')" not in diff


@pytest.mark.fr("FR-030")
def test_fingerprint_changes_only_when_content_does(tmp_path):
    folder, single, missing = tmp_path / "pkg", tmp_path / "ideals.md", tmp_path / "absent"
    folder.mkdir()
    (folder / "a.py").write_text("a\n")
    single.write_text("layers\n")
    paths = [folder, single, missing]
    first = workspace.fingerprint(paths)
    assert workspace.fingerprint(paths) == first
    (folder / "__pycache__").mkdir()
    (folder / "__pycache__" / "a.pyc").write_text("cache")
    assert workspace.fingerprint(paths) == first, "caches written by Python itself must not count"
    (folder / "a.py").write_text("changed\n")
    second = workspace.fingerprint(paths)
    assert second != first
    (folder / "b.py").write_text("new\n")
    third = workspace.fingerprint(paths)
    assert third != second
    single.unlink()
    assert workspace.fingerprint(paths) != third
    missing.write_text("now exists\n")
    assert workspace.fingerprint(paths) != third


@pytest.mark.fr("FR-032")
def test_snapshot_then_restore_returns_everything_to_the_snapshot(tmp_path):
    folder, single, missing = tmp_path / "personas", tmp_path / "ideals.md", tmp_path / "prompts"
    folder.mkdir()
    (folder / "planner.md").write_text("plan\n")
    (folder / "reviewer.md").write_text("review\n")
    single.write_text("layers\n")
    paths, dest = [folder, single, missing], tmp_path / "snapshot"
    workspace.snapshot(paths, dest)
    before = workspace.fingerprint(paths)

    (folder / "planner.md").write_text("tampered\n")
    (folder / "reviewer.md").unlink()
    (folder / "intruder.md").write_text("new\n")
    single.unlink()
    missing.mkdir()
    (missing / "plan.md").write_text("should not exist\n")
    assert workspace.fingerprint(paths) != before

    workspace.restore(paths, dest)
    assert workspace.fingerprint(paths) == before
    assert (folder / "planner.md").read_text() == "plan\n" and not (folder / "intruder.md").exists()
    assert single.read_text() == "layers\n" and not missing.exists()


@pytest.mark.fr("FR-003")
def test_remove_deletes_the_checkout_and_an_empty_branch_only(target, tmp_path):
    empty = Workspace.create(target, tmp_path / "ws1", "factory/1-empty", git(target, "rev-parse", "HEAD"))
    empty.remove()
    assert not empty.path.exists()
    assert "factory/1-empty" not in git(target, "branch", "--list", "factory/*")

    worked = Workspace.create(target, tmp_path / "ws2", "factory/2-worked", git(target, "rev-parse", "HEAD"))
    (worked.path / "app.py").write_text("x\n")
    worked.commit("work")
    worked.remove()
    assert not worked.path.exists()
    assert "factory/2-worked" in git(target, "branch", "--list", "factory/*")  # the work is kept


@pytest.mark.fr("FR-050")
def test_discard_puts_back_only_the_named_files(ws):
    (ws.path / "kept.py").write_text("stays\n")                    # someone else's uncommitted work
    (ws.path / ".factory.toml").write_text("tampered\n")           # a tracked file, changed
    (ws.path / "docs").mkdir()
    (ws.path / "docs" / "backlog.md").write_text("half written")   # a new file
    ws.discard({".factory.toml", "docs/backlog.md", "never-existed.txt"})
    assert set(ws.dirty()) == {"kept.py"}
    assert "test_command" in (ws.path / ".factory.toml").read_text()


@pytest.mark.fr("FR-065")
def test_lines_added_counts_new_lines_in_changed_and_new_files(ws):
    (ws.path / "tests").mkdir()
    (ws.path / "tests" / "test_old.py").write_text("a = 1\nb = 2\n")
    ws.commit("an existing test")
    assert ws.lines_added(["tests/test_old.py"]) == 0
    (ws.path / "tests" / "test_old.py").write_text("a = 1\nb = 2\nc = 3\nd = 4\n")      # two lines added
    (ws.path / "tests" / "test_new.py").write_text("x\ny\nz\n")                          # a new file: three
    assert ws.lines_added(["tests/test_old.py", "tests/test_new.py"]) == 5
    assert ws.lines_added(["tests/test_new.py", "tests/never.py"]) == 3
