"""Effect: git, and files on disk.

A run works in its own checkout (a git worktree on its own branch), so the operator's
working copy is never touched. This module also fingerprints, snapshots and restores
the files a run must never change. It decides nothing.
"""
import hashlib
import pathlib
import shutil

from factory import proc

AUTHOR = ["-c", "user.name=tomfactory", "-c", "user.email=tomfactory@localhost"]
CACHES = shutil.ignore_patterns("__pycache__", "*.pyc")


class WorkspaceError(Exception):
    """A git command failed; the message carries what git said."""


def _git(cwd, *args, ok=(0,)) -> tuple[int, str]:
    code, out, err = proc.capture(["git", *args], cwd=cwd)
    if code not in ok:
        raise WorkspaceError(f"git {' '.join(args)} failed: {err.strip() or out.strip()}")
    return code, out


class Workspace:
    """One run's checkout of the target codebase."""

    def __init__(self, path, target, branch, base_commit):
        self.path = pathlib.Path(path)
        self.target = pathlib.Path(target)
        self.branch = branch
        self.base_commit = base_commit

    @classmethod
    def create(cls, target, path, branch) -> "Workspace":
        """Make a new checkout on a new branch, starting from the target's current commit."""
        base = _git(target, "rev-parse", "HEAD")[1].strip()
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        _git(target, "worktree", "add", "-q", "-b", branch, str(path), base)
        return cls(path, target, branch, base)

    def dirty(self) -> dict[str, str]:
        """Every file that differs from the last commit, with a digest of its content.

        Files the target's .gitignore covers (caches) are not listed.
        """
        out = _git(self.path, "status", "--porcelain", "-z", "--untracked-files=all")[1]
        entries, files = out.split("\0"), {}
        while entries:
            entry = entries.pop(0)
            if not entry:
                continue
            code, name = entry[:2], entry[3:]
            names = [name, entries.pop(0)] if code[0] in "RC" else [name]  # a rename lists both
            for name in names:
                file = self.path / name
                files[name] = hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else "deleted"
        return files

    def undo(self) -> None:
        """Put the checkout back exactly as it was at its last commit."""
        _git(self.path, "reset", "-q", "--hard", "HEAD")
        _git(self.path, "clean", "-fdq")

    def lines_added(self, names) -> int:
        """How many lines these files have gained since the last commit. A new file counts in full."""
        total = 0
        for name in names:
            file = self.path / name
            if not file.is_file():
                continue
            if _git(self.path, "ls-files", "--error-unmatch", name, ok=(0, 1))[0] != 0:
                total += len(file.read_text().splitlines())         # git does not know it: all of it is new
                continue
            counted = _git(self.path, "diff", "--numstat", "HEAD", "--", name)[1].split()
            total += int(counted[0]) if counted and counted[0].isdigit() else 0
        return total

    def head(self) -> str:
        return _git(self.path, "rev-parse", "HEAD")[1].strip()

    def set_aside(self, back_to) -> str:
        """Keep everything since `back_to` on a side branch, and return the checkout to `back_to`."""
        _git(self.path, "add", "-A")
        _git(self.path, *AUTHOR, "commit", "-q", "--allow-empty", "-m", "factory: set aside")
        taken = _git(self.target, "branch", "--list", f"{self.branch}-aside-*")[1].split()
        aside = f"{self.branch}-aside-{len([name for name in taken if name not in '*+']) + 1}"
        _git(self.path, "branch", aside)
        _git(self.path, "reset", "-q", "--hard", back_to)
        _git(self.path, "clean", "-fdq")
        return aside

    def discard(self, names) -> None:
        """Put back just these files: a changed one to its last commit, a new one removed."""
        for name in names:
            if _git(self.path, "checkout", "-q", "HEAD", "--", name, ok=(0, 1))[0] != 0:
                (self.path / name).unlink(missing_ok=True)      # git did not know it: it was new

    def commit(self, message) -> str | None:
        """Commit everything not ignored. Returns the commit id, or None if nothing changed."""
        _git(self.path, "add", "-A")
        if _git(self.path, "diff", "--cached", "--quiet", ok=(0, 1))[0] == 0:
            return None
        _git(self.path, *AUTHOR, "commit", "-q", "-m", message)
        return _git(self.path, "rev-parse", "HEAD")[1].strip()

    def diff_since_base(self) -> str:
        """The run's whole change so far, as a diff against where it started."""
        return _git(self.path, "diff", self.base_commit)[1]

    def files_changed_since_base(self) -> list[str]:
        """The names of the files this run has committed changes to."""
        return _git(self.path, "diff", "--name-only", self.base_commit)[1].split()

    def remove(self) -> None:
        """Delete the checkout. The branch goes too, but only if it holds no work."""
        _git(self.target, "worktree", "remove", "--force", str(self.path), ok=(0, 128))
        _git(self.target, "worktree", "prune")
        ahead = _git(self.target, "rev-list", "--count", f"{self.base_commit}..{self.branch}", ok=(0, 128))
        if ahead[0] == 0 and ahead[1].strip() == "0":
            _git(self.target, "branch", "-q", "-D", self.branch)


def changed(before: dict[str, str], after: dict[str, str]) -> set[str]:
    """The files whose state differs between two `dirty()` readings."""
    return {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}


def _files(path: pathlib.Path):
    """The files that count under a path: everything except Python's own caches."""
    if path.is_file():
        return [(path.name, path)]
    return [(str(f.relative_to(path)), f) for f in sorted(path.rglob("*"))
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc"]


def fingerprint(paths) -> str:
    """One digest over the content of some files and folders. Changes when any of them does."""
    digest = hashlib.sha256()
    for index, path in enumerate(pathlib.Path(p) for p in paths):
        digest.update(f"[{index}:{'present' if path.exists() else 'missing'}]".encode())
        for name, file in _files(path) if path.exists() else []:
            digest.update(name.encode() + b"\0" + file.read_bytes() + b"\0")
    return digest.hexdigest()


def snapshot(paths, dest) -> None:
    """Copy some files and folders into `dest`, so they can be put back later."""
    dest = pathlib.Path(dest)
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for index, path in enumerate(pathlib.Path(p) for p in paths):
        if path.is_dir():
            shutil.copytree(path, dest / str(index), ignore=CACHES)
        elif path.is_file():
            shutil.copy2(path, dest / str(index))


def restore(paths, dest) -> None:
    """Put back what `snapshot` copied, removing anything that was not there then."""
    dest = pathlib.Path(dest)
    for index, path in enumerate(pathlib.Path(p) for p in paths):
        saved = dest / str(index)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        if saved.is_dir():
            shutil.copytree(saved, path)
        elif saved.is_file():
            shutil.copy2(saved, path)
