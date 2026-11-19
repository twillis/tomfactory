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
from tests.conftest import ARCHITECT, BUILD, DOCUMENT, drive_with, git, PLAN, WRITE_TESTS
from tests.fake_agent import FakeAgent

pytestmark = pytest.mark.skipif(shutil.which("specify") is None, reason="the specify command is not installed")

FEATURE = "specs/001-add-a-greeting-page"
REQUEST = "Add a greeting page"


@pytest.fixture
def kit_target(tmp_path):
    return operations.init_target(tmp_path / "kit-target", spec_kit=True)


ACCEPT = {"verdict": "accept", "unbuilt": [], "details": ["a dict was used where the plan said a list"],
          "requirement_changes": [], "reasons": ["it matches the approved documents"], "ideals_broken": []}
KIT_ORDER = ["specify", "clarify", "plan", "tasks", "analyze", "write_tests", "build", "architecture_review",
             "document", "converge"]


def kit_script(**changes):
    """What each persona "does" on a spec kit target, in the order they are called. A list gives one entry per call."""
    from tests.test_cycle import ARCHITECT, BUILD, DOCUMENT, WRITE_TESTS
    entries = {
        "specify": {"envelope": {"summary": "the specification is written", "assumptions": ["names are plain text"]},
                    "files": {f"{FEATURE}/spec.md": "# Feature Specification: greeting\n\nFR-001: it greets.\n"}},
        "clarify": {"envelope": {"plan": f"It greets by name. Full text: {FEATURE}/spec.md",
                                 "clarified": ["an empty name greets the world"]},
                    "files": {f"{FEATURE}/spec.md": "# Feature Specification: greeting\n\nFR-001: it greets.\n"
                                                    "\n## Clarifications\n\n- an empty name greets the world\n"}},
        "plan": {"envelope": dict(PLAN, plan=f"One module. Full text: {FEATURE}/plan.md"),
                 "files": {f"{FEATURE}/plan.md": "# Implementation Plan: greeting\n\nOne module.\n"}},
        "tasks": {"envelope": {"summary": "two tasks, the test first"},
                  "files": {f"{FEATURE}/tasks.md": "- [ ] T001 write the failing test\n- [ ] T002 make it pass\n"}},
        "analyze": {"envelope": {"plan": f"Plan and tasks agree with the specification. See {FEATURE}/",
                                 "findings": []}},
        "write_tests": WRITE_TESTS, "build": BUILD, "architecture_review": ARCHITECT, "document": DOCUMENT,
        "converge": {"envelope": ACCEPT},
    }
    entries.update(changes)
    flat = []
    for name in KIT_ORDER:
        flat += entries[name] if isinstance(entries[name], list) else [entries[name]]
    return flat


def to_the_end(target, fake, request=REQUEST):
    """Request, then approve whenever the run waits, until it ends. Returns the run and how often it waited."""
    drive_with(fake)
    run, waits = operations.request(request, target), 0
    while run.state == "awaiting_approval":
        waits += 1
        run = operations.approve(run.id)
    return run, waits


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
    checkout = Workspace.create(kit_target, tmp_path / "ws", "factory/1-test", git(kit_target, "rev-parse", "HEAD"))
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

    tasks = speckit.prepare(("tasks",), checkout, REQUEST)
    assert tasks["context"]["tasks_file"] == f"{FEATURE}/tasks.md"
    assert (checkout.path / FEATURE / "tasks.md").read_text().startswith("# Tasks:")          # the template, in place
    assert "dependency-ordered" in tasks["instructions"] or "Task Generation Rules" in tasks["instructions"]
    judged = speckit.prepare(("analyze", "checklist"), checkout, REQUEST)
    assert "### /speckit-analyze" in judged["instructions"] and "### /speckit-checklist" in judged["instructions"]
    assert judged["context"]["feature_directory"] == FEATURE
    for command in ("clarify", "implement", "converge"):
        kit = speckit.prepare((command,), checkout, REQUEST)
        assert f"### /speckit-{command}" in kit["instructions"] and kit["context"]["feature_directory"] == FEATURE
    assert "already been run" in kit["instructions"]                                        # the factory's own preface

    again = speckit.prepare(("specify", "plan"), checkout, REQUEST)                         # a revision
    assert again["context"]["feature_directory"] == FEATURE
    assert sorted(p.name for p in (checkout.path / "specs").iterdir()) == ["001-add-a-greeting-page"]

    checkout.commit("first feature")
    later = Workspace.create(kit_target, tmp_path / "ws2", "factory/2-test", git(kit_target, "rev-parse", "HEAD"))
    git(later.path, "merge", "-q", "--ff-only", "factory/1-test")
    later.base_commit = git(later.path, "rev-parse", "HEAD")
    assert speckit.prepare(("specify",), later, "Another thing entirely")["context"]["feature_directory"] \
        == "specs/002-another-thing-entirely"                                               # a new run, a new feature


@pytest.mark.fr("FR-056")
def test_each_spec_kit_stage_has_the_persona_that_uses_it():
    from factory import workflow
    kit = workflow.table_for(True, "change")
    used = {command for s in kit for command in s.speckit}
    assert {"specify", "clarify", "plan", "tasks", "analyze", "implement", "converge"} <= used
    assert all(s.kind == "agent" and s.persona for s in kit if s.speckit)        # a persona follows each one
    assert [s.name for s in kit if s.on_pass == workflow.WAIT] == ["clarify", "analyze"]   # two approvals
    names = [s.name for s in kit]
    assert "converge" in names and "review" not in names                       # converge takes the review's place


@pytest.mark.fr("FR-055")
@pytest.mark.fr("FR-056")
@pytest.mark.fr("FR-057")
def test_a_whole_run_on_a_spec_kit_target_follows_spec_kits_stages(home, kit_target, fake_notify):
    fake = FakeAgent(kit_script())
    drive_with(fake)
    run = operations.request(REQUEST, kit_target)

    assert (run.state, run.current_step) == ("awaiting_approval", "clarify")                # first: the specification
    assert FEATURE in operations.plan(run.id).text
    on_branch = git(kit_target, "ls-tree", "-r", "--name-only", run.branch).split()
    assert f"{FEATURE}/spec.md" in on_branch and f"{FEATURE}/plan.md" not in on_branch
    assert "Clarifications" in git(kit_target, "show", f"{run.branch}:{FEATURE}/spec.md")

    run = operations.approve(run.id)
    assert (run.state, run.current_step) == ("awaiting_approval", "analyze")                # second: plan and tasks
    on_branch = git(kit_target, "ls-tree", "-r", "--name-only", run.branch).split()
    assert f"{FEATURE}/plan.md" in on_branch and f"{FEATURE}/tasks.md" in on_branch
    assert "agree with the specification" in operations.plan(run.id).text

    run = operations.approve(run.id)
    assert run.outcome == "accepted", run.reason
    steps = open_store(home).query("steps", {"run_id": run.id})
    assert [s.name for s in steps] == ["specify", "clarify", "plan", "tasks", "analyze", "baseline", "write_tests",
                                       "red", "build", "test", "architecture_review", "document", "converge", "finish"]
    assert [s.persona for s in steps if s.persona] == ["analyst", "analyst", "planner", "planner", "reviewer",
                                                       "test_writer", "code_writer", "architect", "documenter",
                                                       "reviewer"]
    by_step = dict(zip(KIT_ORDER, fake.calls))
    for name, commands in {"specify": ["specify"], "clarify": ["clarify"], "plan": ["plan"], "tasks": ["tasks"],
                           "analyze": ["analyze", "checklist"], "write_tests": ["implement"], "build": ["implement"],
                           "converge": ["converge"]}.items():
        for command in commands:
            assert f"### /speckit-{command}" in by_step[name]["prompt"], f"{name} was not given /speckit-{command}"
        assert FEATURE in by_step[name]["prompt"] and "already been run" in by_step[name]["prompt"]
    assert "### /speckit-" not in by_step["document"]["prompt"]                             # no stage for these two
    assert "### /speckit-" not in by_step["architecture_review"]["prompt"]
    assert by_step["analyze"]["capabilities"] == "read" and by_step["converge"]["capabilities"] == "read"
    assert by_step["specify"]["capabilities"] == "read+edit"
    assert "Expertise" in by_step["specify"]["persona"] and "specification" in by_step["specify"]["persona"].lower()


@pytest.mark.fr("FR-057")
@pytest.mark.fr("FR-053")
def test_sending_back_returns_to_the_start_of_the_stage_that_is_waiting(home, kit_target, fake_notify):
    script = kit_script()
    spec, clar, plan, tasks, analyze = script[:5]
    fake = FakeAgent([spec, clar, spec, clar, plan, tasks, analyze, plan, tasks, analyze])
    drive_with(fake)
    run = operations.request(REQUEST, kit_target)
    run = operations.revise(run.id, "Say what happens for a missing name.")
    assert (run.state, run.current_step) == ("awaiting_approval", "clarify")
    assert "missing name" in fake.calls[2]["prompt"] and fake.calls[2]["persona"] == fake.calls[0]["persona"]

    run = operations.approve(run.id)
    run = operations.revise(run.id, "Fewer tasks.")
    assert (run.state, run.current_step) == ("awaiting_approval", "analyze")
    names = [s.name for s in open_store(home).query("steps", {"run_id": run.id})]
    assert names == ["specify", "clarify", "specify", "clarify", "plan", "tasks", "analyze", "plan", "tasks", "analyze"]
    assert "Fewer tasks." in fake.calls[7]["prompt"]                                        # the planner, not the analyst
    assert git(kit_target, "ls-tree", "--name-only", f"{run.branch}:specs").split() == ["001-add-a-greeting-page"]


@pytest.mark.fr("FR-058")
@pytest.mark.fr("FR-059")
def test_converge_sorts_differences_and_only_unbuilt_work_returns_to_the_build(home, kit_target, fake_notify):
    from tests.test_cycle import ARCHITECT, BUILD, DOCUMENT
    unbuilt = {"envelope": dict(ACCEPT, verdict="rework", unbuilt=["T002 is not done: no farewell"], reasons=[])}
    fake = FakeAgent(kit_script(converge=[unbuilt])[:-0 or None] + [BUILD, ARCHITECT, DOCUMENT, {"envelope": ACCEPT}])
    run, waits = to_the_end(kit_target, fake)
    assert run.outcome == "accepted" and waits == 2                 # a detail and unbuilt work never return to the operator
    names = [s.name for s in open_store(home).query("steps", {"run_id": run.id})]
    assert names[-7:] == ["converge", "build", "test", "architecture_review", "document", "converge", "finish"]
    assert names.count("converge") == 2 and names.count("build") == 2 and names.count("specify") == 1
    assert "T002 is not done: no farewell" in fake.calls[10]["prompt"]          # the code writer is told what is unbuilt
    first = [s for s in open_store(home).query("steps", {"run_id": run.id}) if s.name == "converge"][0]
    assert first.produced["details"] == ["a dict was used where the plan said a list"]      # the detail is on record


@pytest.mark.fr("FR-059")
@pytest.mark.fr("FR-060")
def test_a_requirement_change_returns_a_spec_kit_run_to_the_operator(home, kit_target, fake_notify):
    changed = {"envelope": dict(ACCEPT, verdict="replan", requirement_changes=["it also greets in French"], reasons=[])}
    fake = FakeAgent(kit_script(converge=[changed]) + kit_script())
    run, waits = to_the_end_of_first_build(kit_target, fake)
    assert (run.state, run.current_step) == ("awaiting_approval", "clarify"), "it must wait for the operator again"
    assert "it also greets in French" in fake.calls[10]["prompt"]               # the analyst is told what changed
    assert fake.calls[10]["persona"] == fake.calls[0]["persona"]
    aside = [b.strip(" +*") for b in git(kit_target, "branch", "--list", f"{run.branch}-aside-*").splitlines()]
    assert len(aside) == 1 and "hello.py" in git(kit_target, "ls-tree", "-r", "--name-only", aside[0]).split()
    kept = git(kit_target, "ls-tree", "-r", "--name-only", run.branch).split()
    assert "hello.py" not in kept and f"{FEATURE}/plan.md" in kept              # the build is set aside; the plan stays

    while run.state == "awaiting_approval":
        drive_with(fake)
        run = operations.approve(run.id)
    assert run.outcome == "accepted"
    assert "hello.py" in git(kit_target, "ls-tree", "-r", "--name-only", run.branch).split()   # built again, tests first
    reds = [s for s in open_store(home).query("steps", {"run_id": run.id}) if s.name == "red"]
    assert len(reds) == 2 and all(s.passed for s in reds)


def to_the_end_of_first_build(target, fake):
    drive_with(fake)
    run = operations.request(REQUEST, target)
    run = operations.approve(run.id)
    return operations.approve(run.id), 2


@pytest.mark.fr("FR-053")
def test_an_analyst_that_writes_outside_the_specification_folder_is_undone(home, kit_target, fake_notify):
    sneaky = kit_script()[0]
    fake = FakeAgent([dict(sneaky, files={**sneaky["files"], "app.py": "print('sneaky')\n"})])
    drive_with(fake)
    run = operations.request(REQUEST, kit_target)
    assert run.outcome == "needs-me" and "app.py" in run.reason
    assert git(run.workspace, "status", "--porcelain") == ""


@pytest.mark.fr("FR-052")
def test_without_spec_kit_the_plain_cycle_runs_and_the_planner_may_change_nothing(home, target, fake_notify):
    plan = kit_script()[2]                              # tries to write under specs/ in a plain target
    fake = FakeAgent([plan])
    drive_with(fake)
    run = operations.request(REQUEST, target)
    assert open_store(home).query("steps", {"run_id": run.id})[0].name == "plan"
    assert run.outcome == "needs-me" and "specs/" in run.reason
    assert "(none)" in fake.calls[0]["prompt"] and "### /speckit-" not in fake.calls[0]["prompt"]


LOCAL_RULE = "LOCAL-RULE: indent with tabs in this codebase."
FACTORY_IDEAL = "FACTORY-IDEAL: well-defined layers with explicit interfaces."


def with_constitution(target, text):
    (target / ".specify" / "memory" / "constitution.md").write_text(text)
    git(target, "add", "-A")
    git(target, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "constitution")


@pytest.mark.fr("FR-054")
def test_a_constitution_is_the_targets_own_text_and_a_blank_template_is_none(kit_target, target):
    assert "[PROJECT_NAME]" in (kit_target / ".specify" / "memory" / "constitution.md").read_text()
    assert speckit.constitution(kit_target) == ""               # spec kit's unfilled template
    assert speckit.constitution(target) == ""                   # no spec kit at all
    with_constitution(kit_target, f"# Greeter Constitution\n\n{LOCAL_RULE}\n")
    assert LOCAL_RULE in speckit.constitution(kit_target)


@pytest.mark.fr("FR-054")
def test_the_targets_constitution_comes_first_then_the_operators_ideals_then_spec_kit(home, kit_target, fake_notify):
    with_constitution(kit_target, f"# Greeter Constitution\n\n{LOCAL_RULE}\n")
    (home / "ideals.md").write_text(FACTORY_IDEAL + "\n")
    fake = FakeAgent(kit_script())
    run, _ = to_the_end(kit_target, fake)
    assert run.outcome == "accepted", run.reason
    by_step = dict(zip(KIT_ORDER, (call["prompt"] for call in fake.calls)))
    for name in ("specify", "clarify", "plan", "tasks", "analyze", "build", "architecture_review", "converge"):
        prompt = by_step[name]
        assert LOCAL_RULE in prompt and FACTORY_IDEAL in prompt, f"the {name} step lacks one of them"
        assert prompt.index(LOCAL_RULE) < prompt.index(FACTORY_IDEAL), f"{name}: the codebase's rules come first"
        assert "order of precedence" in prompt
    assert by_step["plan"].index(FACTORY_IDEAL) < by_step["plan"].index("### /speckit-plan"), "spec kit comes last"
    assert LOCAL_RULE not in by_step["document"]


@pytest.mark.fr("FR-054")
def test_with_no_constitution_the_ideals_stand_alone(home, target, fake_notify):
    (home / "ideals.md").write_text(FACTORY_IDEAL + "\n")
    fake = FakeAgent([{"envelope": PLAN}])
    drive_with(fake)
    operations.request(REQUEST, target)
    prompt = fake.calls[0]["prompt"]
    assert FACTORY_IDEAL in prompt and "This codebase has no constitution of its own." in prompt
