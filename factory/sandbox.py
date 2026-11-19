"""Effect: contain a command. The only module that knows how the target's code is contained.

The factory's agents are confined, but the tests they write, and the code those tests run,
are executed by the factory. This wraps such a command in bubblewrap so that it sees its own
checkout (the only place it can write to that lasts), the system read-only and the Python
the factory runs on, and nothing else of the operator's: no home, no records, no
credentials, no environment, no local services, and no network unless the codebase allows
it. It runs in its own process space, so nothing it starts outlives it.

Measured on 2026-11-19: specs/002-contain-target-code/research.md.
"""
import functools
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HIDDEN = ("/home", "/tmp", "/run")      # replaced inside by empty, private folders; /run holds local sockets


class Unavailable(Exception):
    """Containment does not work on this machine; the message says why and what to do."""


def command(argv, checkout, network=False) -> list[str]:
    """The command that runs `argv` contained, with `checkout` its one lasting writable place."""
    works, reason = available()
    if not works:
        raise Unavailable(f"the factory cannot contain the target's code on this machine, so it will not run"
                          f" it: {reason}")
    return _wrap(argv, checkout, network)


@functools.cache
def available() -> tuple[bool, str]:
    """Whether containment works here, by a trial run. Checked once per process."""
    if not shutil.which("bwrap"):
        return False, "bubblewrap (bwrap) is not installed; install it with: sudo apt install bubblewrap"
    with tempfile.TemporaryDirectory() as trial:
        try:
            done = subprocess.run(_wrap(["true"], trial, False), capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as problem:
            return False, f"bubblewrap could not be started: {problem}"
    if done.returncode != 0:
        return False, f"bubblewrap is installed but cannot contain a command here: {done.stderr.strip()[:300]}"
    return True, "bubblewrap"


def _wrap(argv, checkout, network) -> list[str]:
    hidden = [*HIDDEN, *(["/var/run"] if os.path.isdir("/var/run") and not os.path.islink("/var/run") else [])]
    python = sorted({sys.prefix, sys.base_prefix})      # the factory's Python and its libraries, read-only
    args = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc"]
    args += [arg for path in hidden for arg in ("--tmpfs", path)]
    args += [arg for path in python for arg in ("--ro-bind", path, path)]
    args += ["--bind", str(checkout), str(checkout), "--chdir", str(checkout),
             "--unshare-all", *(["--share-net"] if network else []), "--new-session", "--die-with-parent",
             "--clearenv"]
    environment = {"PATH": f"{Path(sys.executable).parent}:/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp",
                   "TMPDIR": "/tmp", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
    args += [arg for name, value in environment.items() for arg in ("--setenv", name, value)]
    return [*args, "--", *argv]
