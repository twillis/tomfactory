"""Child processes: live output, time limits, and nothing left running (FR-014)."""
import os
import sys
import threading
import time

import pytest

from factory import proc

pytestmark = pytest.mark.fr("FR-014")

PY = sys.executable


def run(code, tmp_path, timeout=10.0, on_line=None, **kw):
    lines = []
    with open(tmp_path / "stderr.txt", "w") as err:
        result = proc.run([PY, "-u", "-c", code], cwd=tmp_path, timeout=timeout,
                          on_line=on_line or lines.append, stderr=err, **kw)
    return result, lines


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def wait_gone(pgid, seconds=3.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not group_alive(pgid):
            return True
        time.sleep(0.05)
    return False


def test_lines_arrive_while_the_child_is_still_running(tmp_path):
    seen = []
    code = "import time; print('first'); time.sleep(0.6); print('second')"
    result, _ = run(code, tmp_path, on_line=lambda line: seen.append((line, time.monotonic())))
    assert [line for line, _ in seen] == ["first", "second"]
    assert seen[1][1] - seen[0][1] > 0.4, "the first line was held back until the child finished"
    assert result.exit_code == 0 and not result.timed_out


def test_a_child_past_its_time_limit_is_stopped(tmp_path):
    started = time.monotonic()
    result, _ = run("import time; time.sleep(60)", tmp_path, timeout=0.5)
    assert result.timed_out
    assert time.monotonic() - started < 5
    assert result.duration_seconds >= 0.5


def test_a_grandchild_does_not_outlive_the_time_limit(tmp_path):
    groups = []
    code = (
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "print('started', flush=True)\n"
        "time.sleep(60)\n"
    )
    result, lines = run(code, tmp_path, timeout=0.8, on_child=groups.append)
    assert result.timed_out and lines == ["started"]
    assert wait_gone(groups[0]), "something in the child's process group is still alive"


def test_a_child_that_ignores_terminate_is_killed(tmp_path, monkeypatch):
    monkeypatch.setattr(proc, "GRACE_SECONDS", 0.5)
    groups = []
    code = (
        "import signal, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "print('ignoring', flush=True)\n"
        "time.sleep(60)\n"
    )
    result, _ = run(code, tmp_path, timeout=0.5, on_child=groups.append)
    assert result.timed_out
    assert wait_gone(groups[0])


def test_a_megabyte_with_no_final_newline_does_not_stall(tmp_path):
    code = "import sys; sys.stdout.write('x' * 1_200_000); sys.stdout.flush()"
    result, lines = run(code, tmp_path, timeout=10)
    assert not result.timed_out and result.exit_code == 0
    assert sum(len(line) for line in lines) == 1_200_000


def test_the_child_is_stopped_when_the_callback_raises(tmp_path):
    groups = []

    def boom(line):
        raise RuntimeError("callback failed")

    code = "import time; print('one', flush=True); time.sleep(60)"
    with pytest.raises(RuntimeError, match="callback failed"):
        run(code, tmp_path, on_line=boom, on_child=groups.append)
    assert wait_gone(groups[0])


def test_on_child_gets_the_group_then_none(tmp_path):
    calls = []
    lines = []

    def on_line(line):
        lines.append((line, list(calls)))

    run("print('hello')", tmp_path, on_line=on_line, on_child=calls.append)
    assert isinstance(calls[0], int) and calls[0] > 0
    assert calls[-1] is None and len(calls) == 2
    assert lines[0][1] == [calls[0]], "on_child must be called before the first line"


def test_stop_group_ends_a_group_started_elsewhere(tmp_path, monkeypatch):
    monkeypatch.setattr(proc, "GRACE_SECONDS", 0.5)
    groups, results = [], []

    def worker():
        results.append(run("import time; time.sleep(60)", tmp_path, timeout=30, on_child=groups.append)[0])

    thread = threading.Thread(target=worker)
    thread.start()
    deadline = time.monotonic() + 5
    while not groups and time.monotonic() < deadline:
        time.sleep(0.02)
    proc.stop_group(groups[0])
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert not results[0].timed_out and results[0].exit_code != 0
    assert wait_gone(groups[0])
    proc.stop_group(groups[0])  # harmless for a group that is already gone


def test_env_reaches_the_child(tmp_path):
    env = dict(os.environ, SPIKE_MARKER="reached")
    _, lines = run("import os; print(os.environ['SPIKE_MARKER'])", tmp_path, env=env)
    assert lines == ["reached"]


def test_liveness_tells_a_process_from_a_reused_id():
    me = os.getpid()
    started = proc.started_at(me)
    assert started and proc.is_alive(me, started)
    assert not proc.is_alive(me, "not-the-start-time")
    assert proc.started_at(2**22 + 12345) is None  # no such process
    assert not proc.is_alive(None, None)


def test_capture_returns_exit_code_output_and_errors(tmp_path):
    code = "import sys; print('out one'); print('out two'); print('oops', file=sys.stderr); sys.exit(3)"
    exit_code, out, err = proc.capture([PY, "-c", code], cwd=tmp_path)
    assert (exit_code, out, err.strip()) == (3, "out one\nout two", "oops")
    with pytest.raises(TimeoutError):
        proc.capture([PY, "-c", "import time; time.sleep(60)"], cwd=tmp_path, timeout=0.3)


def test_standard_input_can_be_given_as_a_file(tmp_path):
    big = "line of prompt text\n" * 20_000   # about 400 KB: far more than one argument may hold
    source = tmp_path / "prompt.txt"
    source.write_text(big)
    lines = []
    with open(source) as stdin, open(tmp_path / "err.txt", "w") as err:
        result = proc.run([PY, "-c", "import sys; print(len(sys.stdin.read()))"], cwd=tmp_path,
                          timeout=10, on_line=lines.append, stderr=err, stdin=stdin)
    assert result.exit_code == 0 and lines == [str(len(big))]
    _, out = run("import sys; print(repr(sys.stdin.read()))", tmp_path)
    assert out == ["''"], "with no stdin given, the child's input is closed, not inherited"


def test_terminate_does_not_wait_for_a_process_that_has_exited_but_not_been_collected(tmp_path):
    import subprocess
    child = subprocess.Popen([PY, "-c", "import time; time.sleep(60)"], start_new_session=True)
    started = proc.started_at(child.pid)
    assert proc.is_alive(child.pid, started)
    began = time.monotonic()
    proc.terminate(child.pid, started)          # the child exits at once; nobody has collected it yet
    assert time.monotonic() - began < 2, "terminate waited for a process that had already exited"
    assert not proc.is_alive(child.pid, started)
    proc.terminate(child.pid, started)          # harmless when it is already gone
    child.wait()
