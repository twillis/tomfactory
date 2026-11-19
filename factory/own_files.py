"""Effect: the factory's own files. Fingerprint, snapshot and restore what a run must never change.

A run must not change the factory's code, personas, prompts or the operator's ideals
(FR-030). Before each step the driver takes a fingerprint of them; if one changed, it puts
back the snapshot taken when the run began. This module decides nothing.
"""
import hashlib
import pathlib
import shutil


def _cache(name) -> bool:
    """Python's own caches, which never count as a change: written whenever code is imported."""
    return name == "__pycache__" or name.endswith(".pyc")


def _files(path: pathlib.Path):
    """The files that count under a path: everything except caches."""
    if path.is_file():
        return [(path.name, path)]
    return [(str(f.relative_to(path)), f) for f in sorted(path.rglob("*"))
            if f.is_file() and not any(_cache(part) for part in f.relative_to(path).parts)]


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
            shutil.copytree(path, dest / str(index), ignore=lambda folder, names: [n for n in names if _cache(n)])
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
