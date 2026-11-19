"""Data: where things are, the target codebase's settings, and the operator's ideals."""
import json
import os
import pathlib
import shlex
import sys
import tomllib
from dataclasses import dataclass, field, fields

from factory import workspace

PACKAGE_DIR = pathlib.Path(__file__).resolve().parent
PERSONAS_DIR = PACKAGE_DIR.parent / "personas"
PROMPTS_DIR = PACKAGE_DIR.parent / "prompts"

DEFAULT_GITIGNORE = "__pycache__/\n.pytest_cache/\n*.pyc\n.venv/\n"


def under(name, paths) -> bool:
    """Is a file one of these paths, or inside one of these folders?"""
    return any(name == p.rstrip("/") or name.startswith(p.rstrip("/") + "/") for p in paths)


class ConfigError(Exception):
    """Something about the target or the home directory is not usable; the message says what."""


def _setting(default, says):
    return field(default=default, metadata={"says": says})


@dataclass(frozen=True)
class TargetConfig:
    """How the factory works on one codebase. Each default and its meaning is written here once."""
    test_command: str = _setting("python -m pytest -q -p no:cacheprovider", "how to run its tests")
    no_tests_exit_code: int = _setting(5, "the test command's exit code for \"no tests found\"")
    test_paths: tuple = _setting(("tests/",), "where tests live; only the test writer may change these")
    docs_paths: tuple = _setting(("docs/", "CHANGELOG.md"), "where the documenter may write")
    step_timeout_seconds: int = _setting(900, "the time limit for any one step")
    test_budget_lines: int = _setting(300, "the most lines of tests one run may add; 0 means no limit")
    test_network: bool = _setting(False, "true lets its tests reach the network; they are contained either way")


def _toml(value) -> str:
    return json.dumps(list(value) if isinstance(value, tuple) else value)       # TOML reads these as JSON writes them


DEFAULT_FACTORY_TOML = (
    "# How the factory works on this codebase. Read from the commit a run starts at,\n"
    "# never from a run's checkout, so an agent cannot change what \"passing\" means.\n"
    + "".join(f"{f'{s.name} = {_toml(s.default)}':<31} # {s.metadata['says']}\n" for s in fields(TargetConfig)))


def home() -> pathlib.Path:
    """The factory's home directory, created on first use."""
    path = pathlib.Path(os.environ.get("TOMFACTORY_HOME") or pathlib.Path.home() / ".tomfactory")
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_target_config(target, commit) -> TargetConfig:
    """The target's settings as committed at `commit`; missing keys take the defaults."""
    out = workspace.committed(target, commit, ".factory.toml")
    if out is None:
        raise ConfigError(f"{target} has no committed .factory.toml; create one with"
                          " `factory init-target` or commit one by hand")
    try:
        values = tomllib.loads(out)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{target}/.factory.toml is not valid TOML: {error}") from error
    known = {name: values[name] for name in TargetConfig.__dataclass_fields__ if name in values}
    for name in ("test_paths", "docs_paths"):
        if name in known:
            known[name] = tuple(known[name])
    return TargetConfig(**known)


def test_argv(settings: TargetConfig) -> list[str]:
    """The test command as a list of words. No shell is involved.

    A leading `python` means the Python that is running the factory.
    """
    words = shlex.split(settings.test_command)
    if words and words[0] == "python":
        words[0] = sys.executable
    return words


def ideals_path() -> pathlib.Path:
    return home() / "ideals.md"


def read_ideals() -> str:
    """The operator's ideals as written, or an empty string if none have been stated."""
    path = ideals_path()
    return path.read_text() if path.exists() else ""


def factory_paths() -> list[pathlib.Path]:
    """What a run must never change: the factory's code, personas, prompts and the ideals."""
    return [PACKAGE_DIR, PERSONAS_DIR, PROMPTS_DIR, ideals_path()]
