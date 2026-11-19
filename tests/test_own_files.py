"""The factory's own files: a fingerprint that notices any change, and a snapshot that puts it back."""
import pytest

from factory import own_files


@pytest.mark.fr("FR-030")
def test_fingerprint_changes_only_when_content_does(tmp_path):
    folder, single, missing = tmp_path / "pkg", tmp_path / "ideals.md", tmp_path / "absent"
    folder.mkdir()
    (folder / "a.py").write_text("a\n")
    single.write_text("layers\n")
    paths = [folder, single, missing]
    first = own_files.fingerprint(paths)
    assert own_files.fingerprint(paths) == first
    (folder / "__pycache__").mkdir()
    (folder / "__pycache__" / "a.pyc").write_text("cache")
    assert own_files.fingerprint(paths) == first, "caches written by Python itself must not count"
    (folder / "a.py").write_text("changed\n")
    second = own_files.fingerprint(paths)
    assert second != first
    (folder / "b.py").write_text("new\n")
    third = own_files.fingerprint(paths)
    assert third != second
    single.unlink()
    assert own_files.fingerprint(paths) != third
    missing.write_text("now exists\n")
    assert own_files.fingerprint(paths) != third


@pytest.mark.fr("FR-032")
def test_snapshot_then_restore_returns_everything_to_the_snapshot(tmp_path):
    folder, single, missing = tmp_path / "personas", tmp_path / "ideals.md", tmp_path / "prompts"
    folder.mkdir()
    (folder / "planner.md").write_text("plan\n")
    (folder / "reviewer.md").write_text("review\n")
    single.write_text("layers\n")
    paths, dest = [folder, single, missing], tmp_path / "snapshot"
    own_files.snapshot(paths, dest)
    before = own_files.fingerprint(paths)

    (folder / "planner.md").write_text("tampered\n")
    (folder / "reviewer.md").unlink()
    (folder / "intruder.md").write_text("new\n")
    single.unlink()
    missing.mkdir()
    (missing / "plan.md").write_text("should not exist\n")
    assert own_files.fingerprint(paths) != before

    own_files.restore(paths, dest)
    assert own_files.fingerprint(paths) == before
    assert (folder / "planner.md").read_text() == "plan\n" and not (folder / "intruder.md").exists()
    assert single.read_text() == "layers\n" and not missing.exists()
