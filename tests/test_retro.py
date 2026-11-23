"""The retro a spec kit run ends with: facts measured by code, judgement by the team (FR-091, FR-092)."""
import shutil

import pytest

from factory import operations, records, run_record, tables, workflow
from factory.store import open_store
from tests.conftest import ARCHITECT, BUILD, DOCUMENT, git
from tests.fake_agent import FakeAgent
from tests.test_speckit import ACCEPT, REQUEST, kit_script, kit_target, requested_at_a_known_time  # noqa: F401
from tests.conftest import drive_with, to_the_end

pytestmark = pytest.mark.skipif(shutil.which("specify") is None, reason="the specify command is not installed")

RETRO_FILE = "docs/retros/{stem}.md"


def retro_entry(stem, fails=False):
    """What the facilitator "does": write the retro note, or fail."""
    if fails:
        return {"error": "the agent program fell over"}
    return {"envelope": {"summary": "a clean sprint", "worked": ["one approval"], "did_not": ["a long plan"],
                         "opportunities": ["a shorter spec"], "threats": ["the test budget"]},
            "files": {RETRO_FILE.format(stem=stem): "---\nkind: retro\n---\n# Retro\n"}}


@pytest.mark.fr("FR-091")
def test_the_retro_is_the_last_agent_step_of_a_sprint_and_never_stops_it():
    kit = tables.SPEC_KIT_STEPS
    retro = workflow.get("retro", kit)
    assert workflow.get("converge", kit).on_pass == "retro" and retro.on_pass == "finish"
    assert retro.advisory and retro.persona == "facilitator" and retro.may_change == "docs"
    assert retro.model == "light"                                     # it summarises what code measured
    assert {"run_facts", "friction", "operator_feedback", "findings"} <= set(retro.inputs)


@pytest.mark.fr("FR-091")
@pytest.mark.fr("FR-092")
@pytest.mark.parametrize("fails", [False, True], ids=["written", "fails"])
def test_a_sprint_ends_with_a_retro_and_its_record_with_time_and_cost(home, kit_target, fake_notify, fails):
    seen = []

    def facilitator(call):
        seen.append(call["prompt"])
        stem = run_record.name(records.open_run(open_store(home))).removeprefix("docs/runs/").removesuffix(".md")
        return retro_entry(stem, fails)

    happy = kit_script(retro=[])
    tester = dict(happy[5], envelope=dict(happy[5]["envelope"], friction=["the plan named no test file"]))
    script = happy[:5] + happy[2:5] + [tester] + happy[6:]          # the plan is sent back once
    drive_with(FakeAgent(script + [facilitator]))
    run = operations.request(REQUEST, kit_target)
    run = operations.revise(run.id, "Fewer tasks, please.")
    while run.state == "awaiting_approval":
        run = operations.approve(run.id)
    assert run.outcome == "accepted"                                   # a failed retro is on record, not a stop
    prompt = seen[0]
    assert "Fewer tasks, please." in prompt                            # the operator's words, verbatim
    assert "the plan named no test file" in prompt                     # an agent's friction, in its own words
    assert "| write_tests |" in prompt and "minutes" in prompt         # the facts, measured by code
    stem = run.branch.removeprefix("factory/")
    on_branch = git(kit_target, "ls-tree", "-r", "--name-only", run.branch).split()
    assert (RETRO_FILE.format(stem=stem) in on_branch) is not fails
    record = git(kit_target, "show", f"{run.branch}:docs/runs/{stem}.md")
    facts = record[record.index("## Time and cost"):]
    for said in ("| specify |", "| build |", "| converge |", "Total", "Waiting for the operator"):
        assert said in facts, said


@pytest.mark.fr("FR-092")
def test_every_agent_is_told_it_may_say_what_made_its_step_harder():
    from factory import config
    assert "friction" in (config.PROMPTS_DIR / "fragments" / "reply.md").read_text()
