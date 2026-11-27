"""Effect: contain a command. The only module that knows how the target's code is contained.

The factory's agents are confined, but the tests they write, and the code those tests run,
are executed by the factory. This wraps such a command in bubblewrap so that it sees its own
checkout (the only place it can write to that lasts), the system read-only and the Python
the factory runs on, and nothing else of the operator's: no home, no records, no
credentials, no environment, no local services, and no network unless the codebase allows
it. It runs in its own process space, so nothing it starts outlives it.

A codebase can ask for three things more, in its committed settings: programs from the
operator's PATH (an installer, a compiler), by name, each let in read-only as that one file;
a home of its own, a folder the factory keeps for it, where its setup command leaves what
it fetched; and other codebases it is built on (`readable`), each a folder with its own git
repository, let in read-only at the same path (FR-163). Nothing else of the operator's comes
with any of them.

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


def command(argv, checkout, network=False, tools=(), home=None, home_writable=False, readable=()) -> list[str]:
    """The command that runs `argv` contained, with `checkout` its one lasting writable place.

    `tools` are programs it may use, by name. `home` is the codebase's own home, read-only
    unless `home_writable`: the setup command fills it, the tests only read it. `readable` are
    other codebases it may read, never change, each at its own path (FR-163).
    """
    works, reason = available()
    if not works:
        raise Unavailable(f"the factory cannot contain the target's code on this machine, so it will not run"
                          f" it: {reason}")
    programs = [_program(name) for name in tools]
    codebases = [_codebase(path) for path in readable]
    return _wrap(argv, checkout, network, programs, home, home_writable, codebases)


def _program(name) -> Path:
    """Where a program the codebase asked for is, on the operator's PATH."""
    if "/" in name:     # a path could name anything of the operator's; a name can only be a program
        raise Unavailable(f"the codebase's settings ask for the tool {name!r}; a tool is given by name, not by path")
    found = shutil.which(name)
    if not found:
        raise Unavailable(f"the codebase's commands need the program {name!r}, which is not on your PATH;"
                          " install it, or take it out of `tools` in the codebase's .factory.toml")
    return Path(found)


def _codebase(path) -> Path:
    """Another codebase the commands may read: a folder with its own git repository, nothing wider. A codebase is
    something the operator chose to build on; a bare folder could be any of theirs (their home, their keys)."""
    folder = Path(path)
    if not (folder / ".git").exists():
        raise Unavailable(f"the codebase's settings ask to read {path}, which is not a codebase (a folder with its"
                          " own .git); only another codebase is let in, read-only, under `readable` in .factory.toml")
    return folder.resolve()


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


def _wrap(argv, checkout, network, programs=(), home=None, home_writable=False, codebases=()) -> list[str]:
    hidden = [*HIDDEN, *(["/var/run"] if os.path.isdir("/var/run") and not os.path.islink("/var/run") else [])]
    python = sorted({sys.prefix, sys.base_prefix})      # the factory's Python and its libraries, read-only
    args = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc"]
    args += [arg for path in hidden for arg in ("--tmpfs", path)]
    args += [arg for path in python for arg in ("--ro-bind", path, path)]
    resolver = Path("/etc/resolv.conf").resolve()       # often a link into /run, which is hidden
    if network and resolver.is_file() and any(resolver.is_relative_to(folder) for folder in hidden):
        args += ["--ro-bind", str(resolver), str(resolver)]     # the network is no use without names
    args += [arg for program in programs for arg in ("--ro-bind", str(program.resolve()), str(program))]
    args += [arg for folder in codebases for arg in ("--ro-bind", str(folder), str(folder))]     # after /home is hidden
    args += ["--bind" if home_writable else "--ro-bind", str(home), str(home)] if home else []
    args += ["--bind", str(checkout), str(checkout), "--chdir", str(checkout),
             "--unshare-all", *(["--share-net"] if network else []), "--new-session", "--die-with-parent",
             "--clearenv"]
    path = [Path(sys.executable).parent, *dict.fromkeys(program.parent for program in programs),
            "/usr/local/bin", "/usr/bin", "/bin"]
    environment = {"PATH": ":".join(map(str, path)), "HOME": str(home or "/tmp"),
                   "TMPDIR": "/tmp", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
    args += [arg for name, value in environment.items() for arg in ("--setenv", name, value)]
    return [*args, "--", *argv]
