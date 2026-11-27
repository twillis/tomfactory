"""Effect: git, and files on disk.

A run works in its own checkout (a git worktree on its own branch), so the operator's
working copy is never touched. This is the only module that runs git. It decides nothing.
"""
import hashlib
import pathlib
import re
import shutil

from factory import proc

AUTHOR = ["-c", "user.name=tomfactory", "-c", "user.email=tomfactory@localhost"]
MAIN_NOW = ".factory-main"      # in a checkout: standing documents as on the codebase's main line now (FR-134)
BUILT_ON = ".factory-built-on"  # in a checkout: the docs of the codebases it is built on, as committed now (FR-164)


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
    def create(cls, target, path, branch, base) -> "Workspace":
        """Make a new checkout on a new branch, starting from the given commit of the target."""
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        _git(target, "worktree", "add", "-q", "-b", branch, str(path), base)
        return cls(path, target, branch, base)

    @classmethod
    def of(cls, run) -> "Workspace":
        """A run's checkout, as its record describes it."""
        return cls(run.workspace, run.target, run.branch, run.base_commit)

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

    def long_lines_added(self, names, limit) -> list[str]:
        """Each line these files have gained since the last commit that is longer than `limit`, as
        "file:line (n)". A new file counts in full."""
        found = []
        for name in sorted(names):
            file = self.path / name
            if not file.is_file():
                continue
            lines = file.read_text(errors="replace").splitlines()
            for number in self.added_lines(name):
                if number <= len(lines) and len(lines[number - 1]) > limit:
                    found.append(f"{name}:{number} ({len(lines[number - 1])})")
        return found

    def added_lines(self, name) -> list[int]:
        """The numbers of the lines a file has gained since the last commit. A new file counts in full; a file that
        is not there has gained none."""
        file = self.path / name
        if not file.is_file():
            return []
        if _git(self.path, "ls-files", "--error-unmatch", name, ok=(0, 1))[0] != 0:
            return list(range(1, len(file.read_text(errors="replace").splitlines()) + 1))   # all of it is new
        return _added_line_numbers(_git(self.path, "diff", "-U0", "HEAD", "--", name)[1])

    def head(self) -> str:
        return _git(self.path, "rev-parse", "HEAD")[1].strip()

    def delete(self, names) -> list[str]:
        """Delete these files from the checkout, as an agent asked (FR-135); return the ones deleted. A path that
        is not a file here is left as it is. Which paths may be asked for is decided before, by the checks."""
        gone = []
        for name in names:
            file = self.path / name
            if file.is_file() or file.is_symlink():
                file.unlink()
                gone.append(name)
        return gone

    def mirror_main(self, names) -> tuple[str, list[str]]:
        """Copy these files and folders, as committed at the codebase's head now, into MAIN_NOW in the checkout,
        read-only, in place of any copy made before (FR-134). A .gitignore of `*` inside keeps the folder out of
        git, so no step's change, commit or undo includes it. Returns the head and the files copied."""
        return _mirror(self.target, self.path / MAIN_NOW, names)

    def mirror_built_on(self, entries) -> list[tuple[str, str, list[str]]]:
        """Copy another codebase's docs, as committed at its head now, into BUILT_ON/<its folder's name> in the
        checkout, read-only and out of git as MAIN_NOW is (FR-164). `entries` are "<codebase path>:<file or folder>",
        the path from this codebase's folder or whole. Returns, for each codebase, its name, its head and the files
        copied. Only what is committed is copied: its source is never named here unless an entry names it."""
        folder = self.path / BUILT_ON
        shutil.rmtree(folder, ignore_errors=True)
        wanted = {}
        for entry in entries:
            codebase, name = entry.rsplit(":", 1)
            wanted.setdefault((pathlib.Path(self.target) / codebase).resolve(), []).append(name)
        copied = [(codebase.name, *_mirror(codebase, folder / codebase.name, names, keep_out=False))
                  for codebase, names in wanted.items()]
        folder.mkdir(exist_ok=True)
        (folder / ".gitignore").write_text("*\n")
        return copied

    def lines_since_base(self, paths) -> tuple[int, int, list[str]]:
        """What the run has done under these paths since it started: lines added, lines removed, files deleted."""
        added = removed = 0
        if not paths:
            return 0, 0, []
        for line in _git(self.path, "diff", "--numstat", self.base_commit, "--", *paths)[1].splitlines():
            plus, minus = line.split("\t")[:2]
            added, removed = added + int(plus if plus.isdigit() else 0), removed + int(minus if minus.isdigit() else 0)
        deleted = _git(self.path, "diff", "--name-only", "--diff-filter=D", self.base_commit, "--", *paths)[1].split()
        return added, removed, deleted

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

    def move_to(self, commit) -> None:
        """Start the checkout again from `commit`, the codebase's head now: only for a run that has built nothing on
        its branch yet (FR-125)."""
        _git(self.path, "reset", "-q", "--hard", commit)
        _git(self.path, "clean", "-fdq")
        self.base_commit = commit

    def moved(self, since, to) -> str:
        """What the codebase gained between two commits: each commit's subject, and the files that changed."""
        log = _git(self.path, "log", "--format=%h %s", f"{since}..{to}")[1].strip()
        changed = _git(self.path, "diff", "--stat", since, to)[1].rstrip()
        return f"From {since[:10]} to {to[:10]}:\n\n{log}\n\n{changed}"

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

    def commit_only(self, name, message) -> str | None:
        """Commit this one file, whatever else is changed. Returns the commit id, or None if it is unchanged."""
        _git(self.path, "add", "--", name)
        if _git(self.path, "diff", "--cached", "--quiet", "--", name, ok=(0, 1))[0] == 0:
            return None
        _git(self.path, *AUTHOR, "commit", "-q", "-m", message, "--", name)
        return _git(self.path, "rev-parse", "HEAD")[1].strip()

    def log_since_base(self) -> list[str]:
        """The run's commits so far, oldest first, each as its short id and subject."""
        return _git(self.path, "log", "--reverse", "--format=%h %s", f"{self.base_commit}..HEAD")[1].splitlines()

    def diff_since_base(self, leaving_out=None) -> str:
        """The run's whole change so far, as a diff against where it started, without the file `leaving_out`."""
        without = [f":(exclude){leaving_out}"] if leaving_out else []
        return _git(self.path, "diff", self.base_commit, "--", ".", *without)[1]

    def on_branch(self) -> list[str]:
        """The names of the files in the checkout's last commit."""
        return [name for name in _git(self.path, "ls-tree", "-r", "-z", "--name-only", "HEAD")[1].split("\0") if name]

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


HUNK = re.compile(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", re.M)


def _added_line_numbers(diff) -> list[int]:
    """The numbers, in the new file, of the lines a zero-context diff adds."""
    numbers = []
    for start, count in HUNK.findall(diff):
        numbers.extend(range(int(start), int(start) + int(count or 1)))
    return numbers


def changed(before: dict[str, str], after: dict[str, str]) -> set[str]:
    """The files whose state differs between two `dirty()` readings."""
    return {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}


# ---- a codebase, outside any run's checkout ----

def _mirror(source, folder, names, keep_out=True) -> tuple[str, list[str]]:
    """Copy `names` (files and folders), as committed at `source`'s head now, into `folder`, read-only, in place of
    any copy made before; with `keep_out`, a .gitignore of `*` inside keeps the folder out of git. Returns the head
    and the files copied."""
    head = head_of(source)
    shutil.rmtree(folder, ignore_errors=True)
    listed = _git(source, "ls-tree", "-r", "-z", "--name-only", head, "--", *names)[1].split("\0")
    copied = [name for name in listed if name]
    for name in copied:
        file = folder / name
        file.parent.mkdir(parents=True, exist_ok=True)
        text = _git(source, "show", f"{head}:{name}")[1]
        file.write_text(text + "\n" if text else "")         # what git printed, line by line
        file.chmod(0o444)
    folder.mkdir(parents=True, exist_ok=True)
    if keep_out:
        (folder / ".gitignore").write_text("*\n")
    return head, copied


def diff_numstat(target, base, branch) -> tuple[int, str]:
    """`git diff --numstat` of `branch` against `base` in the codebase `target`: (exit code, output); a code other
    than 0 where either is gone (FR-165)."""
    return _git(target, "diff", "--numstat", "--no-renames", base, branch, ok=(0, 128))


def head_of(target) -> str:
    """The commit a codebase is at now."""
    if not pathlib.Path(target).is_dir():
        raise WorkspaceError(f"{target} is not a git repository")
    code, out = _git(target, "rev-parse", "HEAD", ok=(0, 128))
    if code != 0:
        raise WorkspaceError(f"{target} is not a git repository with at least one commit")
    return out.strip()


def is_merged(target, branch) -> bool:
    """Whether `branch` is in the codebase's current commit (FR-161): merged into the branch it is on now. A branch
    that no longer exists counts as dealt with, since only its owner removes it."""
    code, _ = _git(target, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", ok=(0, 1))
    if code != 0:
        return True
    code, _ = _git(target, "merge-base", "--is-ancestor", branch, "HEAD", ok=(0, 1))
    return code == 0


def committed(target, commit, name) -> str | None:
    """A file's text as committed at `commit`, or None if it was not there."""
    code, out = _git(target, "show", f"{commit}:{name}", ok=(0, 128))
    return out if code == 0 else None


def slug(text, words=5) -> str:
    """A name safe for git and folders: the first few words of `text`, lower case. "" if none are usable."""
    joined = " ".join(text.split()[:words]).lower()
    return re.sub(r"[^a-z0-9]+", "-", joined).strip("-")[:40].strip("-")
