"""Personas: who carries out each agent step (FR-042 to FR-044)."""
import pathlib
import re

import pytest

from factory import config

HEADINGS = ["## Expertise", "## Priorities", "## Must not"]


def sections(name):
    """A persona file's text under each of its three headings."""
    text = (config.PERSONAS_DIR / f"{name}.md").read_text()
    assert re.findall(r"^## .*$", text, re.M) == HEADINGS, f"{name}.md must have exactly {HEADINGS}"
    parts = re.split(r"^## .*$", text, flags=re.M)[1:]
    assert all(part.strip() for part in parts), f"{name}.md has an empty section"
    return dict(zip(("expertise", "priorities", "must_not"), parts))


@pytest.mark.fr("FR-042")
def test_the_planner_states_expertise_priorities_and_what_it_must_not_do():
    planner = sections("planner")
    assert "ideals" in planner["priorities"].lower()
    assert "change" in planner["must_not"].lower()


@pytest.mark.fr("FR-042")
def test_all_six_personas_exist_with_the_three_headings():
    from factory import workflow
    named = {step.persona for step in workflow.STEPS if step.kind == "agent"}
    assert named == {"planner", "test_writer", "code_writer", "architect", "reviewer", "documenter"}
    with_spec_kit = {step.persona for step in workflow.table_for(True) if step.kind == "agent"}
    assert with_spec_kit == named | {"analyst"}             # spec kit's specify and clarify have their own persona
    for name in with_spec_kit:
        sections(name)
    assert {f.stem for f in config.PERSONAS_DIR.glob("*.md")} == with_spec_kit | {"lead"}   # the lead answers questions
    assert "answer" in sections("lead")["expertise"].lower()


@pytest.mark.fr("FR-043")
def test_the_test_writer_is_directed_to_edge_and_failure_cases_and_away_from_implementation():
    writer = sections("test_writer")
    assert "edge case" in writer["priorities"].lower() and "failure case" in writer["priorities"].lower()
    assert "implementation" in writer["must_not"].lower()
    priorities = writer["priorities"].lower()
    assert "once" in priorities and "level" in priorities and "parametri" in priorities     # FR-065: proportionate
    assert "budget" in priorities
    import re
    own = [line for line in writer["priorities"].splitlines() if re.match(r"\d+\. ", line)]
    assert any(line.lower().split(". ", 1)[1].startswith("parametrise") for line in own), \
        "parametrised tests must be a priority of their own, not a clause inside another"
    assert "test" in sections("code_writer")["must_not"].lower()


@pytest.mark.fr("FR-044")
def test_the_reviewer_changes_nothing_and_judges_against_the_ideals():
    reviewer = sections("reviewer")
    assert "change" in reviewer["must_not"].lower()
    assert "ideal" in reviewer["priorities"].lower()


@pytest.mark.fr("FR-048")
def test_the_architect_reviews_for_maintenance_and_never_blocks():
    architect = sections("architect")
    expertise, priorities, must_not = (architect[k].lower() for k in ("expertise", "priorities", "must_not"))
    assert "lisp" in expertise and "paradigm" in expertise
    assert "repeated" in priorities and "backlog" in priorities
    assert "suggest" in priorities and "warn" in priorities
    assert "code" in must_not and "reject" in must_not      # it changes no code and blocks nothing
