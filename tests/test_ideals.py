"""Ideals: stated once by the operator, and every run is held to them (Story 4)."""
import pytest

from factory import cli, config, operations, records
from factory.store import open_store
from tests.conftest import BUILD, drive_with, git, PLAN, script
from tests.fake_agent import FakeAgent

IDEAL = "Well-defined layers with explicit interfaces between them."
NONE_STATED = "No ideals have been stated."


def prompts(fake):
    return dict(zip(["plan", "write_tests", "build", "architecture_review", "document", "review"],
                    (c["prompt"] for c in fake.calls)))


@pytest.mark.fr("FR-021")
@pytest.mark.fr("FR-022")
@pytest.mark.fr("FR-024")
def test_stated_ideals_reach_the_plan_the_build_and_the_review_and_are_kept_on_the_run(cycle, home):
    (home / "ideals.md").write_text(IDEAL + "\n")
    run, fake, store, _ = cycle(script())
    sent = prompts(fake)
    for step in ("plan", "build", "architecture_review", "review"):
        assert IDEAL in sent[step] and NONE_STATED not in sent[step], f"the {step} prompt lacks the ideals"
    assert run.ideals == IDEAL + "\n"
    assert operations.show(run.id).run.ideals == IDEAL + "\n"
    assert records.current_plan(store, run.id).ideals_addressed == PLAN["ideals_addressed"]


@pytest.mark.fr("FR-023")
@pytest.mark.fr("FR-030")
def test_editing_the_ideals_changes_the_next_run_and_nothing_else(cycle, home):
    ideals = home / "ideals.md"
    ideals.write_text("First ideal.\n")
    first, _, _, target = cycle(script())
    git(target, "worktree", "remove", "--force", first.workspace)      # dealt with, without merging: the operator
    git(target, "branch", "-q", "-D", first.branch)                     # removed it, so the next is not held (FR-161)
    assert ideals.read_text() == "First ideal.\n"              # a run never changes them
    ideals.write_text("Second ideal.\n")
    second, fake, _, _ = cycle(script(), target=target)
    assert first.ideals == "First ideal.\n" and second.ideals == "Second ideal.\n"
    assert "Second ideal." in prompts(fake)["review"] and "First ideal." not in prompts(fake)["review"]
    assert operations.show(first.id).run.ideals == "First ideal.\n"       # the earlier run keeps its own


@pytest.mark.fr("FR-020")
@pytest.mark.fr("FR-024")
def test_with_no_ideals_stated_a_run_completes_and_says_so(cycle, home):
    assert not (home / "ideals.md").exists()
    run, fake, _, _ = cycle(script())
    assert run.outcome == "accepted" and run.ideals == ""
    assert NONE_STATED in prompts(fake)["plan"] and NONE_STATED in prompts(fake)["review"]


@pytest.mark.fr("FR-022")
def test_a_review_that_names_a_broken_ideal_rejects_and_the_reason_names_it(cycle, home):
    (home / "ideals.md").write_text(IDEAL + "\n")
    broken = {"envelope": {"verdict": "reject", "reasons": ["the page builds its own SQL"],
                           "ideals_broken": ["layers: the page reaches the database directly"]}}
    run, _, _, _ = cycle(script(review=broken))
    assert run.outcome == "rejected"
    assert "layers: the page reaches the database directly" in run.reason and "builds its own SQL" in run.reason


@pytest.mark.fr("FR-022")
def test_a_broken_ideal_can_never_be_accepted(cycle, home):
    (home / "ideals.md").write_text(IDEAL + "\n")
    contradictory = {"envelope": {"verdict": "accept", "reasons": ["good enough"],
                                  "ideals_broken": ["layers are mixed"]}}
    run, fake, store, _ = cycle(script(review=[contradictory] * 3))
    assert run.outcome == "needs-me" and "review" in run.reason and "layers are mixed" in run.reason
    assert [s.failure for s in store.query("steps", {"run_id": run.id}) if s.name == "review"] == ["check"] * 3
    assert "finish" not in [s.name for s in store.query("steps", {"run_id": run.id})]


@pytest.mark.fr("FR-021")
def test_conflicts_the_plan_states_are_shown_to_the_operator(cycle, home, capsys, monkeypatch):
    conflicted = dict(PLAN, conflicts=["The request wants one file; the ideals want layers."])
    target = operations.init_target(home.parent / "conflict-target")
    drive_with(FakeAgent([{"envelope": conflicted}]))
    run = operations.request("One file please", target)
    assert operations.plan(run.id).conflicts == conflicted["conflicts"]
    assert cli.main(["plan"]) == 0
    assert "The request wants one file; the ideals want layers." in capsys.readouterr().out


@pytest.mark.fr("FR-020")
def test_the_operator_can_see_where_the_ideals_are_and_what_they_say(home, capsys):
    path, text = operations.ideals()
    assert path == config.ideals_path() == home / "ideals.md" and text == ""
    (home / "ideals.md").write_text(IDEAL + "\n")
    assert operations.ideals() == (home / "ideals.md", IDEAL + "\n")
    assert cli.main(["ideals"]) == 0
    out = capsys.readouterr().out
    assert str(home / "ideals.md") in out and IDEAL in out


# ---- a codebase's own ideals (FR-082) ----

@pytest.mark.fr("FR-082")
def test_a_codebase_that_states_its_own_ideals_holds_every_run_to_those(cycle, home):
    (home / "ideals.md").write_text("PERSONAL: mine alone.\n")
    run, fake, _, _ = cycle(script(), files={"IDEALS.md": "SHARED: the team's.\n"})
    assert run.outcome == "accepted" and run.ideals.strip() == "SHARED: the team's."
    assert "SHARED: the team's." in fake.calls[0]["prompt"] and "PERSONAL" not in fake.calls[0]["prompt"]


@pytest.mark.fr("FR-082")
def test_no_step_may_rewrite_the_codebases_ideals(cycle):
    softened = dict(BUILD, files={**BUILD["files"], "IDEALS.md": "Anything goes.\n"})
    run, _, _, _ = cycle(script(build=softened)[:3], files={"IDEALS.md": "SHARED: the team's.\n"})
    assert run.outcome == "needs-me" and "IDEALS.md" in run.reason
