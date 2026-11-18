"""Data: where things are, the target codebase's settings, and the operator's ideals."""
import os
import pathlib
import shlex
import sys
import tomllib
from dataclasses import dataclass

from factory import proc

PACKAGE_DIR = pathlib.Path(__file__).resolve().parent
PERSONAS_DIR = PACKAGE_DIR.parent / "personas"
PROMPTS_DIR = PACKAGE_DIR.parent / "prompts"

DEFAULT_FACTORY_TOML = '''\
# How the factory works on this codebase. Read from the commit a run starts at,
# never from a run's checkout, so an agent cannot change what "passing" means.
test_command = "python -m pytest -q -p no:cacheprovider"
no_tests_exit_code = 5          # the test command's exit code for "no tests found"
test_paths = ["tests/"]         # where tests live; only the test writer may change these
docs_paths = ["docs/", "CHANGELOG.md"]   # where the documenter may write
step_timeout_seconds = 900      # the time limit for any one step
'''

DEFAULT_GITIGNORE = "__pycache__/\n.pytest_cache/\n*.pyc\n.venv/\n"


class ConfigError(Exception):
    """Something about the target or the home directory is not usable; the message says what."""


@dataclass(frozen=True)
class TargetConfig:
    test_command: str = "python -m pytest -q -p no:cacheprovider"
    no_tests_exit_code: int = 5
    test_paths: tuple = ("tests/",)
    docs_paths: tuple = ("docs/", "CHANGELOG.md")
    step_timeout_seconds: int = 900


def home() -> pathlib.Path:
    """The factory's home directory, created on first use."""
    path = pathlib.Path(os.environ.get("TOMFACTORY_HOME") or pathlib.Path.home() / ".tomfactory")
    path.mkdir(parents=True, exist_ok=True)
    return path


def head_commit(target) -> str:
    """The commit a target codebase is at now."""
    if not pathlib.Path(target).is_dir():
        raise ConfigError(f"{target} is not a git repository")
    code, out, _ = proc.capture(["git", "rev-parse", "HEAD"], cwd=target)
    if code != 0:
        raise ConfigError(f"{target} is not a git repository with at least one commit")
    return out.strip()


def read_target_config(target, commit) -> TargetConfig:
    """The target's settings as committed at `commit`; missing keys take the defaults."""
    code, out, _ = proc.capture(["git", "show", f"{commit}:.factory.toml"], cwd=target)
    if code != 0:
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
