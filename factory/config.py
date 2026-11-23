"""Data: where things are, the target codebase's settings, and the operator's ideals."""
import hashlib
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
    setup_command: str = _setting("", "run before its tests, contained, with the network: installs what it needs")
    tools: tuple = _setting((), "programs on your PATH its commands may use, by name")
    cycle: str = _setting("auto", "auto: spec kit where it is set up, else plain; sprint: one plan, then build to the end")
    tests_readable_command: str = _setting("python -m compileall -q tests",
                                           "fails if new tests cannot even be read as code; \"\" for none")
    line_length: int = _setting(0, "the longest line a step may add to code or tests; 0 means no limit")
    coverage_report: str = _setting("", "the coverage.py JSON report its test command writes; \"\" if not measured")
    coverage_floor: float = _setting(0.0, "a smell when coverage after a run is below this percent; 0 for none")
    coverage_drop: float = _setting(0.0, "a smell when a run lowers coverage by more than this many points; 0 for none")
    climbs_to: str = _setting("standard", "the highest grade a retried step climbs to (FR-109)")
    # [steps.<name>] tables: per-step overrides (FR-112). Not written into a new codebase's file: none are needed.
    steps: dict = field(default_factory=dict, metadata={"says": "", "unlisted": True})


def _toml(value) -> str:
    return json.dumps(list(value) if isinstance(value, tuple) else value)       # TOML reads these as JSON writes them


DEFAULT_FACTORY_TOML = (
    "# How the factory works on this codebase. Read from the commit a run starts at,\n"
    "# never from a run's checkout, so an agent cannot change what \"passing\" means.\n"
    + "".join(f"{f'{s.name} = {_toml(s.default)}':<31} # {s.metadata['says']}\n" for s in fields(TargetConfig)
              if not s.metadata.get("unlisted")))


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
    for name in ("test_paths", "docs_paths", "tools"):
        if name in known:
            known[name] = tuple(known[name])
    if known.get("climbs_to", "standard") not in ("light", "middle", "standard", "strongest"):
        raise ConfigError(f"{target}/.factory.toml: climbs_to must be light, middle, standard or strongest")
    return TargetConfig(**known)


def _argv(command) -> list[str]:
    """A command as a list of words. No shell is involved.

    A leading `python` means the Python that is running the factory.
    """
    words = shlex.split(command)
    if words and words[0] == "python":
        words[0] = sys.executable
    return words


def test_argv(settings: TargetConfig) -> list[str]:
    return _argv(settings.test_command)


def setup_argv(settings: TargetConfig) -> list[str]:
    return _argv(settings.setup_command)


def tests_readable_argv(settings: TargetConfig) -> list[str]:
    return _argv(settings.tests_readable_command)


def codebase_home(target) -> pathlib.Path:
    """The folder the factory keeps for one codebase: what its setup command fetched, and nothing of the operator's.

    It stands in for a home directory, so an installer's cache lands in it whatever the language.
    """
    target = pathlib.Path(target).resolve()
    path = home() / "codebases" / f"{target.name}-{hashlib.sha256(str(target).encode()).hexdigest()[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ideals_path() -> pathlib.Path:
    return home() / "ideals.md"


IDEALS_FILE = "IDEALS.md"       # a codebase's own ideals, committed in it; they replace the operator's


def ideals_for(target, commit) -> str:
    """The ideals a run on this codebase is held to: its own if it states any, else the operator's."""
    shared = workspace.committed(target, commit, IDEALS_FILE)
    return shared if shared and shared.strip() else read_ideals()


def read_ideals() -> str:
    """The operator's ideals as written, or an empty string if none have been stated."""
    path = ideals_path()
    return path.read_text() if path.exists() else ""


def factory_paths() -> list[pathlib.Path]:
    """What a run must never change: the factory's code, personas, prompts and the ideals."""
    return [PACKAGE_DIR, PERSONAS_DIR, PROMPTS_DIR, ideals_path()]
