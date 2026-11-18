"""Shared fixtures, and the rule that every test names the requirement it covers (constitution S8)."""
import subprocess

import pytest


def pytest_collection_modifyitems(config, items):
    unmarked = [item.nodeid for item in items if item.get_closest_marker("fr") is None]
    if unmarked:
        raise pytest.UsageError(
            "every test must carry @pytest.mark.fr(\"FR-nnn\"); unmarked:\n  " + "\n  ".join(unmarked)
        )


def git(cwd, *args):
    """Run git in a test repository and return its output."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A temporary factory home directory, set as TOMFACTORY_HOME."""
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("TOMFACTORY_HOME", str(path))
    return path


def make_target(path, extra_files=None):
    """A git repository with one commit holding the default target files."""
    from factory import config

    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", "Test Operator")
    git(path, "config", "user.email", "operator@example.invalid")
    (path / ".factory.toml").write_text(config.DEFAULT_FACTORY_TOML)
    (path / ".gitignore").write_text(config.DEFAULT_GITIGNORE)
    for name, text in (extra_files or {}).items():
        file = path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "base")
    return path


@pytest.fixture
def target(tmp_path):
    """A temporary target codebase: a git repository with a committed .factory.toml."""
    return make_target(tmp_path / "target")


@pytest.fixture
def fake_notify(monkeypatch):
    """Replace the desktop notification with a recorder; returns the list of (title, body)."""
    sent = []

    def record(title, body):
        sent.append((title, body))
        return True

    monkeypatch.setattr("factory.notify.send", record, raising=False)
    return sent


def in_process(fake):
    """A launcher that carries the run forward here and now, with a fake agent.

    Operations normally launch a detached driver process. Tests pass this instead, so a
    whole run happens inside the test and can be inspected straight afterwards.
    """
    from factory import driver

    def launcher(store, run, state, step):
        store.runs.set_state(run.id, state, current_step=step)
        driver.advance(store, run.id, adapter=fake)

    return launcher


PLAN = {"plan": "Add hello.py that prints hello.", "ideals_addressed": ["keeps the layers apart"],
        "conflicts": []}
