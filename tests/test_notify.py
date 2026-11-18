"""Desktop notification: best effort, never raises (FR-017)."""
import os
import stat

import pytest

from factory import notify

pytestmark = pytest.mark.fr("FR-017")


def stub_command(tmp_path, monkeypatch, body):
    """Put a stand-in `notify-send` first on PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / "notify-send"
    script.write_text("#!/bin/sh\n" + body)
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


def test_send_runs_the_command_with_title_and_body(tmp_path, monkeypatch):
    out = tmp_path / "args.txt"
    stub_command(tmp_path, monkeypatch, f'printf "%s|%s" "$1" "$2" > {out}\n')
    assert notify.send("Run 7: accepted", "tests pass and the review agreed") is True
    assert out.read_text() == "Run 7: accepted|tests pass and the review agreed"


def test_a_failing_command_returns_false(tmp_path, monkeypatch):
    stub_command(tmp_path, monkeypatch, "exit 1\n")
    assert notify.send("title", "body") is False


def test_a_missing_command_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))  # nothing here
    assert notify.send("title", "body") is False


def test_a_hanging_command_returns_false(tmp_path, monkeypatch):
    stub_command(tmp_path, monkeypatch, "sleep 60\n")
    monkeypatch.setattr(notify, "TIME_LIMIT", 0.3)
    assert notify.send("title", "body") is False
