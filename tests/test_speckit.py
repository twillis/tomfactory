"""Spec kit, where the target uses it: the planner writes spec kit's documents, and the
factory's code — never an agent — runs spec kit's scripts (FR-051 to FR-053).

These tests need the `specify` command, which sets spec kit up in a new codebase.
"""
import json
import shutil

import pytest

from factory import operations, speckit
from factory.store import open_store
from factory.workspace import Workspace
from tests.conftest import PLAN, git, in_process
from tests.fake_agent import FakeAgent
from tests.test_cycle import script

pytestmark = pytest.mark.skipif(shutil.which("specify") is None, reason="the specify command is not installed")

FEATURE = "specs/001-add-a-greeting-page"
REQUEST = "Add a greeting page"


@pytest.fixture
def kit_target(tmp_path):
    return operations.init_target(tmp_path / "kit-target", spec_kit=True)


def planner(extra=None):
    """A fake planner that writes spec kit's two documents, as the real one is asked to."""
    files = {f"{FEATURE}/spec.md": "# Feature Specification: greeting\n\nFR-001: it greets.\n",
             f"{FEATURE}/plan.md": "# Implementation Plan: greeting\n\nOne module.\n"}
    return {"envelope": dict(PLAN, plan=f"Summary. Full documents: {FEATURE}/spec.md and plan.md"),
            "files": {**files, **(extra or {})}}


@pytest.mark.fr("FR-051")
def test_init_target_can_set_spec_kit_up(kit_target, tmp_path):
    assert git(kit_target, "status", "--porcelain") == ""
    tracked = git(kit_target, "ls-files").split()
    assert ".specify/scripts/bash/setup-plan.sh" in tracked and ".factory.toml" in tracked
    assert any(name.startswith(".claude/skills/speckit-plan/") for name in tracked)
    assert speckit.available(kit_target)
    assert not speckit.available(operations.init_target(tmp_path / "plain"))


@pytest.mark.fr("FR-051")
@pytest.mark.fr("FR-053")
def test_prepare_runs_the_scripts_and_returns_the_targets_own_instructions(kit_target, tmp_path):
    checkout = Workspace.create(kit_target, tmp_path / "ws", "factory/1-test")
    kit = speckit.prepare(("specify", "plan"), checkout, REQUEST)

    assert kit["context"]["feature_directory"] == FEATURE
    assert (checkout.path / FEATURE / "spec.md").read_text().startswith("# Feature Specification")
    assert "Implementation Plan" in (checkout.path / FEATURE / "plan.md").read_text()      # the templates, in place
    assert json.loads((checkout.path / ".specify" / "feature.json").read_text()) == {"feature_directory": FEATURE}
    assert kit["context"]["spec_file"] == f"{FEATURE}/spec.md" and kit["context"]["plan_file"] == f"{FEATURE}/plan.md"

    own = (kit_target / ".claude" / "skills" / "speckit-plan" / "SKILL.md").read_text()
    assert "Constitution Check" in own and "Constitution Check" in kit["instructions"]      # the target's own text
    assert "Specification Quality Validation" in kit["instructions"]                        # and specify's
    assert kit["instructions"].index("speckit-specify") < kit["instructions"].index("speckit-plan")

    again = speckit.prepare(("specify", "plan"), checkout, REQUEST)                         # a revision
    assert again["context"]["feature_directory"] == FEATURE
    assert sorted(p.name for p in (checkout.path / "specs").iterdir()) == ["001-add-a-greeting-page"]

    checkout.commit("first feature")
    later = Workspace.create(kit_target, tmp_path / "ws2", "factory/2-test")
    git(later.path, "merge", "-q", "--ff-only", "factory/1-test")
    later.base_commit = git(later.path, "rev-parse", "HEAD")
    assert speckit.prepare(("specify",), later, "Another thing entirely")["context"]["feature_directory"] \
        == "specs/002-another-thing-entirely"                                               # a new run, a new feature


@pytest.mark.fr("FR-051")
@pytest.mark.fr("FR-053")
def test_on_a_spec_kit_target_the_plan_is_spec_kits_documents(home, kit_target, fake_notify):
    fake = FakeAgent([planner(), planner({f"{FEATURE}/spec.md": "# Feature Specification: greeting, revised\n"})])
    run = operations.request(REQUEST, kit_target, launcher=in_process(fake))
    assert run.state == "awaiting_approval"

    asked = fake.calls[0]["prompt"]
    assert FEATURE in asked and "Constitution Check" in asked and "already been run" in asked
    assert fake.calls[0]["capabilities"] == "read+edit"
    committed = git(kit_target, "ls-tree", "-r", "--name-only", run.branch).split()
    assert f"{FEATURE}/spec.md" in committed and f"{FEATURE}/plan.md" in committed          # on the branch, to approve
    assert git(kit_target, "log", "-1", "--format=%s", run.branch) == f"factory: plan (run {run.id})"
    assert FEATURE in operations.plan(run.id).text
    step = open_store(home).query("steps", {"run_id": run.id})[0]
    assert step.passed and [c["name"] for c in step.checks][:2] == ["factory_untouched", "changes_allowed"]

    operations.revise(run.id, "Say it is revised.", launcher=in_process(fake))
    specs = git(kit_target, "ls-tree", "--name-only", f"{run.branch}:specs").split()
    assert specs == ["001-add-a-greeting-page"], "a revision must not start a second feature"
    assert "revised" in git(kit_target, "show", f"{run.branch}:{FEATURE}/spec.md")


@pytest.mark.fr("FR-053")
def test_a_planner_that_writes_outside_the_specification_folder_is_undone(home, kit_target, fake_notify):
    fake = FakeAgent([planner({"app.py": "print('sneaky')\n"})])
    run = operations.request(REQUEST, kit_target, launcher=in_process(fake))
    assert run.outcome == "needs-me" and "app.py" in run.reason
    assert git(run.workspace, "status", "--porcelain") == ""


@pytest.mark.fr("FR-052")
def test_without_spec_kit_a_planner_may_still_change_nothing(home, target, fake_notify):
    fake = FakeAgent([planner()])                       # tries to write under specs/ in a plain target
    run = operations.request(REQUEST, target, launcher=in_process(fake))
    assert run.outcome == "needs-me" and "specs/" in run.reason
    assert "(none)" in fake.calls[0]["prompt"] and "Constitution Check" not in fake.calls[0]["prompt"]


@pytest.mark.fr("FR-051")
def test_a_whole_run_on_a_spec_kit_target_is_accepted(home, kit_target, fake_notify):
    fake = FakeAgent([planner()] + script()[1:])
    run = operations.request(REQUEST, kit_target, launcher=in_process(fake))
    run = operations.approve(run.id, launcher=in_process(fake))
    assert run.outcome == "accepted", run.reason
    subjects = git(kit_target, "log", "--format=%s", f"{run.base_commit}..{run.branch}").splitlines()
    assert subjects[-1] == f"factory: plan (run {run.id})" and len(subjects) == 5
    assert FEATURE in fake.calls[2]["prompt"]           # the code writer is pointed at the documents
