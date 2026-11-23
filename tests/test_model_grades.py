"""Model grades: a step starts on its own grade, and a retry climbs one grade at a time (FR-088, FR-109)."""
from dataclasses import replace

import pytest

from factory import agent, operations, tables, workflow
from factory.run_record import facts
from factory.store import open_store
from tests.conftest import ARCHITECT, BUILD, DOCUMENT, drive_with, PLAN, REVIEW, WRITE_TESTS
from tests.fake_agent import FakeAgent


@pytest.mark.fr("FR-109")
@pytest.mark.parametrize("own, tries, grade", [
    ("light", 0, "light"), ("light", 1, "middle"), ("light", 2, "standard"), ("light", 5, "standard"),
    ("middle", 0, "middle"), ("middle", 1, "standard"), ("middle", 3, "standard"),
    ("standard", 0, "standard"), ("standard", 2, "standard"),         # never climbs to the strongest by itself
    ("strongest", 0, "strongest"), ("strongest", 2, "strongest"),     # only a step that starts there runs there
])
def test_a_retry_climbs_one_grade_and_never_past_the_standard_one(own, tries, grade):
    step = replace(tables.LEAD, model=own)
    assert workflow.grade_for(step, tries) == grade


@pytest.mark.fr("FR-109")
def test_every_grade_names_a_model():
    assert set(agent.MODELS) == set(workflow.GRADES)


@pytest.mark.fr("FR-109")
def test_a_documenter_that_fails_runs_again_on_a_stronger_model_and_the_record_says_which(home, target, fake_notify):
    no_summary = {"envelope": {"files_changed": []}}                     # not the reply the documenter owes
    fake = drive_with(FakeAgent([{"envelope": PLAN}, WRITE_TESTS, BUILD, ARCHITECT, no_summary, DOCUMENT, REVIEW]))
    run = operations.request("Add a greeting", target)
    run = operations.approve(run.id)
    assert run.outcome == "accepted", run.reason
    assert [call["model"] for call in fake.calls] == ["standard", "standard", "standard", "standard", "light", "middle", "standard"]
    table = "\n".join(facts(open_store(home), run))
    assert "| Model |" in table and "| document | 1 | light |" in table and "| document | 2 | middle |" in table
