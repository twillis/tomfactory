"""Effect: run one child process, and stop process groups.

Every child the factory starts — an agent, the test command, git — goes through `run`.
It fixes the three classic ways a child process goes wrong:

* a child stalls because nobody is reading its output  -> output is read continuously;
* a child outlives its parent                          -> each child gets its own process
                                                          group, and the whole group is stopped;
* a child hangs forever                                -> every run has a time limit.
"""
import os
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass

GRACE_SECONDS = 5.0  # how long a group gets to exit after "terminate" before it is killed


@dataclass
class ProcResult:
    exit_code: int
    timed_out: bool
    duration_seconds: float


def run(cmd, cwd, timeout, on_line, stderr, env=None, on_child=None, stdin=None) -> ProcResult:
    """Run `cmd` (a list of words) and return when it, and everything it started, has ended.

    on_line(text)   is called with each line of standard output as it arrives.
    stderr          is an open file that receives the child's standard error.
    stdin           is an open file the child reads as its standard input; closed if not given.
    on_child(pgid)  is called with the child's process-group id when it starts, and
                    with None when it has ended, so the caller can record what to stop.
    """
    started = time.monotonic()
    child = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdin=stdin or subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=stderr, text=True, errors="replace", start_new_session=True,
    )
    pgid = child.pid  # a new session makes the child the leader of its own group
    timed_out = threading.Event()

    def expire():
        timed_out.set()
        stop_group(pgid)

    timer = threading.Timer(timeout, expire)
    timer.daemon = True
    try:
        if on_child:
            on_child(pgid)
        timer.start()
        assert child.stdout is not None
        for line in child.stdout:
            on_line(line.rstrip("\n"))
        child.wait()
    finally:
        timer.cancel()
        if child.poll() is None:  # still running: an exception got us here, not the end of output
            _signal_group(pgid, signal.SIGTERM)
            try:
                child.wait(timeout=GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                _signal_group(pgid, signal.SIGKILL)
        child.wait()  # collect the child, so the group reads as empty once it is
        stop_group(pgid)  # and anything the child started that is still around
        if child.stdout:
            child.stdout.close()
        if on_child:
            on_child(None)
    return ProcResult(child.returncode, timed_out.is_set(), time.monotonic() - started)


def stop_group(pgid, grace=None) -> None:
    """End every process in a group: ask first, then insist. Harmless if it is already gone."""
    if not pgid or not _signal_group(pgid, signal.SIGTERM):
        return
    deadline = time.monotonic() + (GRACE_SECONDS if grace is None else grace)
    while time.monotonic() < deadline:
        if not _signal_group(pgid, 0):
            return
        time.sleep(0.05)
    _signal_group(pgid, signal.SIGKILL)


def _signal_group(pgid, sig) -> bool:
    """Send a signal to a group. False when no such group exists (or it is not ours)."""
    try:
        os.killpg(pgid, sig)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def started_at(pid) -> str | None:
    """A process's start time, as the kernel reports it; None if there is no such live process.

    A process id can be reused by a later, unrelated process. The id together with the
    start time identifies one process for good.
    """
    try:
        with open(f"/proc/{pid}/stat") as stat:
            fields = stat.read().rsplit(")", 1)[1].split()
    except (OSError, IndexError):
        return None
    if fields[0] == "Z":  # exited, not yet collected by its parent
        return None
    return fields[19]


def is_alive(pid, started) -> bool:
    """Is the process with this id still the one that had this start time?"""
    return bool(pid) and started is not None and started_at(pid) == started


def capture(cmd, cwd, timeout=60.0, env=None) -> tuple[int, str, str]:
    """Run a short command and return (exit code, standard output, standard error)."""
    lines: list[str] = []
    with tempfile.TemporaryFile("w+") as errors:
        result = run(cmd, cwd, timeout, lines.append, errors, env=env)
        errors.seek(0)
        error_text = errors.read()
    if result.timed_out:
        raise TimeoutError(f"{cmd[0]} did not finish within {timeout} seconds")
    return result.exit_code, "\n".join(lines), error_text


def spawn_detached(cmd, cwd, log, env=None) -> int:
    """Start a process that outlives this one, in its own session. Returns its process id."""
    child = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                             start_new_session=True)
    return child.pid


def terminate(pid, started, grace=None) -> None:
    """End one process we did not start as our own child, and wait until it has really gone.

    Unlike `stop_group`, this knows the process by its id and start time, so it is not
    fooled by a process that has exited but has not yet been collected by its parent.
    """
    if not is_alive(pid, started):
        return
    _signal_group(pid, signal.SIGTERM)
    deadline = time.monotonic() + (GRACE_SECONDS if grace is None else grace)
    while is_alive(pid, started):
        if time.monotonic() > deadline:
            _signal_group(pid, signal.SIGKILL)
            return
        time.sleep(0.05)


def interactive(cmd) -> int:
    """Run a command the operator uses directly (an editor), on this terminal. Returns its exit code."""
    return subprocess.call(cmd)
