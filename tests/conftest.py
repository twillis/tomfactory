"""Shared fixtures, and the rule that every test names the requirement it covers (constitution S8)."""
import pathlib
import re
import shutil
import subprocess

collect_ignore_glob = ["fixtures/*"]     # files copied into target codebases, not the factory's tests

import pytest

from factory import config, operations, own_files, records, workspace
from factory.store import open_store
from tests.fake_agent import FakeAgent

_patch = None       # this test's monkeypatch, so helpers can swap the launcher without being handed it


@pytest.fixture(autouse=True)
def _keep_monkeypatch(monkeypatch):
    global _patch
    _patch = monkeypatch


ROOT = pathlib.Path(__file__).resolve().parent.parent


def requirements() -> set[str]:
    """Every functional requirement, across every feature's specification. They share one numbering."""
    found = set()
    for spec in (ROOT / "specs").glob("*/spec.md"):
        found |= set(re.findall(r"^- \*\*(FR-\d{3})\*\*:", spec.read_text(), re.M))
    return found


@pytest.hookimpl(tryfirst=True)         # before -m and -k deselect anything
def pytest_collection_modifyitems(config, items):
    """The gate for constitution S8, over the tests pytest actually collected.

    Every test names the requirement it covers; and, when the whole suite is collected,
    every requirement is named by at least one test.
    """
    unmarked = [item.nodeid for item in items if item.get_closest_marker("fr") is None]
    if unmarked:
        raise pytest.UsageError(
            "every test must carry @pytest.mark.fr(\"FR-nnn\"); unmarked:\n  " + "\n  ".join(unmarked))
    whole = all(pathlib.Path(arg).resolve() in (ROOT, ROOT / "tests") for arg in config.args)
    named = {marker.args[0] for item in items for marker in item.iter_markers("fr")}
    missing = sorted(requirements() - named)
    if whole and missing:
        raise pytest.UsageError("these requirements are named by no test: " + ", ".join(missing))


def git(cwd, *args):
    """Run git in a test repository and return its output."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def merged(target, run):
    """Merge an accepted run's branch into its codebase, as the operator does; the next queued request waits for it
    (FR-161)."""
    git(target, "merge", "-q", "--no-ff", "-m", f"merge run {run.id}", run.branch)


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


def commit_files(target, files):
    """Write these files into a target and commit them. Returns the target."""
    for name, text in (files or {}).items():
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        (target / name).write_text(text)
    if files:
        git(target, "add", "-A")
        git(target, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "files")
    return target


def tree(path):
    """Every file under a directory with its bytes, ignoring git's own folder."""
    return {str(f.relative_to(path)): f.read_bytes()
            for f in sorted(path.rglob("*")) if f.is_file() and ".git" not in f.relative_to(path).parts}


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
    """A launcher that carries the run forward here and now, with a fake agent."""
    from factory import driver

    def launcher(store, run, state, step):
        records.set_state(store, run.id, state, current_step=step)
        driver.advance(store, run.id, adapter=fake)

    return launcher


def drive_with(fake):
    """From here on in this test, every run is carried forward here and now, by this fake agent.

    Operations normally hand a run to a detached driver process (operations.launch). This
    replaces that one function, so a whole run happens inside the test.
    """
    _patch.setattr(operations, "launch", in_process(fake))
    return fake


def to_the_end(target, fake, request="Add a greeting", **kw):
    """Request, then approve whenever the run waits for approval, until it ends or asks a question.

    Returns the run and how many times it was approved.
    """
    drive_with(fake)
    run, waits = operations.request(request, target, **kw), 0
    while run.state == "awaiting_approval" and records.pending_question(open_store(config.home()), run.id) is None:
        waits += 1
        if (operations.waiting(run.id) or {}).get("for") == "agreement":      # a dialogue's plan: agreed, then approved
            operations.agree(run.id)
        run = operations.approve(run.id)
    return run, waits


PLAN = {"plan": "Add hello.py that prints hello.", "ideals_addressed": ["keeps the layers apart"],
        "conflicts": []}


# ---- a dialogue's speakers (FR-119 to FR-129): what each says in one round ----

def checked(questions):
    """Why no ruling settles each question, one item each, as every speaker says (FR-156)."""
    return [f"no ruling in the standing documents settles: {q}" for q in questions]


def speaks(questions=(), measure=(), blocking=None, notes=(), cost=0.0):
    """The analyst's batch, or with `blocking` the architect's or the plan check's: what would break the build or
    contradict a ruling, and the notes the planner may take or leave (FR-130)."""
    said = {"questions": list(questions), "measure": list(measure), "rulings_checked": checked(questions)}
    if blocking is not None:
        said.update(blocking=list(blocking), notes=list(notes))
    return {"envelope": said, "cost": cost}


def merges(*groups):
    """The light model's reply to the merge of a round's questions (FR-132): each group, the question ids that ask
    the same thing, the one to keep first."""
    return {"envelope": {"merged": [list(group) for group in groups]}}


def planner_says(plan=PLAN["plan"], questions=(), measure=(), estimate="small: one file, about $5", declined=(),
                 how_much="little: the ask is plain", cost=0.0):
    """The planner's batch: aligned, with the plan and an estimate, when it asks nothing."""
    aligned = not questions and not measure
    return {"envelope": {"questions": list(questions), "measure": list(measure), "rulings_checked": checked(questions),
                         "aligned": "yes" if aligned else "no",
                         "how_much": how_much, "plan": plan if aligned else "", "estimate": estimate if aligned else "",
                         "declined": list(declined), "ideals_addressed": PLAN["ideals_addressed"], "conflicts": []},
            "cost": cost}


def aligned_round(plan=PLAN["plan"]):
    """One round in which nobody asks anything and the planner proposes aligned."""
    return [speaks(), planner_says(plan), speaks(blocking=()), speaks(blocking=())]


SPRINT_TOML = 'cycle = "sprint"'


def sprint_settings(extra=""):
    return {".factory.toml": config.DEFAULT_FACTORY_TOML.replace('cycle = "auto"', SPRINT_TOML) + extra}


# ---- a scripted run: what each persona "does", for the fake agent ----

TEST = ("from hello import greet\n\n\ndef test_greets():\n    assert greet() == 'hello'\n\n\n"
        "def test_empty_name_still_greets():\n    assert greet('') == 'hello'\n")
CODE = "def greet(name=''):\n    return 'hello'\n"
WRONG = "def greet(name=''):\n    return 'goodbye'\n"

WRITE_TESTS = {"envelope": {"summary": "greeting tests", "test_files": ["tests/test_hello.py"],
                            "edge_cases": ["an empty name"]},
               "files": {"tests/test_hello.py": TEST}}
BUILD = {"envelope": {"summary": "added greet", "files_changed": ["hello.py"], "verdict": "accept", "reasons": [],
                      "defective_tests": []},
         "files": {"hello.py": CODE},
         "events": [("agent_text", "BUILDER-PRIVATE-THOUGHT", {"text": "BUILDER-PRIVATE-THOUGHT"})]}
ARCHITECT = {"envelope": {"summary": "sound, with one thing to tidy later",
                          "suggestions": ["the greeting text is repeated; give it one home"], "warnings": []},
             "files": {"docs/backlog.md": "- the greeting text is repeated; give it one home\n"}}
REVIEW = {"envelope": {"verdict": "accept", "reasons": ["it matches the request"], "ideals_broken": []}}
DOCUMENT = {"envelope": {"summary": "Added a greeting.", "files_changed": ["CHANGELOG.md"]},
            "files": {"CHANGELOG.md": "- Added a greeting.\n"}}
ORDER = ["plan", "baseline", "write_tests", "red", "build", "test", "architecture_review", "document",
         "review", "finish"]


def script(**changes):
    """The happy script, with any step's entry replaced. A list gives one entry per attempt."""
    entries = {"plan": {"envelope": PLAN}, "write_tests": WRITE_TESTS, "build": BUILD,
               "architecture_review": ARCHITECT, "review": REVIEW, "document": DOCUMENT}
    entries.update(changes)
    flat = []
    for name in ("plan", "write_tests", "build", "architecture_review", "document", "review"):
        value = entries[name]
        flat += value if isinstance(value, list) else [value]
    return flat


@pytest.fixture
def cycle(home, tmp_path, fake_notify, monkeypatch):
    """Run a request to its end and return (run, fake, store, target). Checks FR-019 and FR-030 every time."""
    personas = tmp_path / "personas"
    shutil.copytree(config.PERSONAS_DIR, personas)      # so a test may tamper with them safely
    monkeypatch.setattr(config, "PERSONAS_DIR", personas)

    def go(entries, target=None, files=None, attempts=3, request="Add a greeting", run_kind="change"):
        if target is None:
            target = commit_files(operations.init_target(tmp_path / "target"), files)
        before, fingerprint = tree(target), own_files.fingerprint(config.factory_paths())
        fake = FakeAgent(entries)
        run, _ = to_the_end(target, fake, request, attempts=attempts, run_kind=run_kind)
        assert run.state == "ended", f"the run did not end: {run.state} at {run.current_step}"
        assert tree(target) == before, "the operator's working copy changed"                      # FR-019
        assert own_files.fingerprint(config.factory_paths()) == fingerprint, "the factory changed"  # FR-030
        assert (run.driver_pid, run.child_pgid) == (None, None)
        return run, fake, open_store(home), target

    go.notify = fake_notify
    return go


def names(store, run):
    return [s.name for s in store.query("steps", {"run_id": run.id})]


def record(store, run, name, attempt=-1):
    return [s for s in store.query("steps", {"run_id": run.id}) if s.name == name][attempt]
