"""The sprint: a dialogue, one approval, then build to the end with a sprint review and a retro (FR-093).

Also the three factory fixes the first retro asked for that apply to every cycle (FR-094).
"""
import pytest

from factory import config, operations, run_record, tables, workflow
from factory.store import open_store
from tests.conftest import (ARCHITECT, BUILD, DOCUMENT, PLAN, WRITE_TESTS, aligned_round, commit_files, drive_with, git,
                            planner_says, speaks, to_the_end)
from tests.fake_agent import FakeAgent

ACCEPT = {"envelope": {"verdict": "accept", "unbuilt": [], "details": ["named it hello.py"], "requirement_changes": [],
                       "reasons": ["it matches the plan"], "ideals_broken": ["two modules say the same thing"]}}
RETRO = {"envelope": {"summary": "fine", "worked": ["one approval"], "did_not": [], "opportunities": [], "threats": []}}


def sprint(**changes):
    """A whole sprint: one round of the dialogue that ends aligned (FR-119), then the build to the end."""
    entries = {"write_tests": WRITE_TESTS, "build": BUILD, "architecture_review": ARCHITECT, "document": DOCUMENT,
               "converge": ACCEPT, "retro": RETRO}
    entries.update(changes)
    return [*aligned_round(), *(entries[n] for n in entries)]


@pytest.fixture
def sprint_target(target):
    commit_files(target, {".factory.toml": config.DEFAULT_FACTORY_TOML.replace('cycle = "auto"', 'cycle = "sprint"')})
    return target


@pytest.mark.fr("FR-093")
@pytest.mark.parametrize("spec_kit, cycle, expected", [
    (False, "auto", tables.STEPS), (True, "auto", tables.SPEC_KIT_STEPS),
    (False, "sprint", tables.SPRINT_STEPS), (True, "sprint", tables.SPRINT_STEPS),   # chosen over spec kit
])
def test_a_codebase_chooses_its_cycle(spec_kit, cycle, expected):
    assert tables.table_for(spec_kit, "change", cycle) is expected
    tidy = tables.SPRINT_TIDY_CODE if cycle == "sprint" else tables.TIDY_CODE    # planned in a dialogue (FR-119)
    assert tables.table_for(spec_kit, "tidy-code", cycle) is tidy


@pytest.mark.fr("FR-093")
def test_the_sprint_waits_once_and_ends_with_the_sprint_review_and_the_retro():
    steps = tables.SPRINT_STEPS
    assert [s.name for s in steps if s.on_pass == workflow.WAIT] == ["dialogue_check"]
    assert [s.name for s in steps][-3:] == ["converge", "retro", "finish"]
    review = workflow.get("converge", steps)
    assert review.speckit == () and not review.ideals_stop and set(review.routes) == {"rework"}
    assert "plan" in review.inputs and "red_output" in review.inputs


@pytest.mark.fr("FR-093")
def test_a_whole_sprint_on_a_codebase_that_asks_for_it(home, sprint_target, fake_notify):
    fake = FakeAgent(sprint())
    run, waits = to_the_end(sprint_target, fake)
    assert run.outcome == "accepted" and waits == 1           # a broken ideal is reported, not a stop
    record = git(sprint_target, "show", f"{run.branch}:{run_record.name(run)}")
    for said in ("## Sprint review", "two modules say the same thing", "## Time and cost"):
        assert said in record
    assert fake.calls[-1]["persona"].startswith("# Facilitator")


@pytest.mark.fr("FR-094")
def test_the_judges_see_the_red_run_as_well_as_the_green(home, sprint_target, fake_notify):
    fake = FakeAgent(sprint())
    to_the_end(sprint_target, fake)
    for task in ("# Task: review the change as an architect", "# Task: is what was built what was approved?"):
        prompt = next(c["prompt"] for c in fake.calls if c["prompt"].startswith(task))
        assert "## The tests before the build" in prompt, task


@pytest.mark.fr("FR-094")
def test_a_resumed_step_is_told_why_it_stopped_and_the_record_is_written_again(home, sprint_target, fake_notify):
    happy = sprint()
    fake = FakeAgent(happy[:5] + [{"error": "You've hit your 5-hour limit"}])
    drive_with(fake)
    run = operations.request("Add a greeting", sprint_target)
    run = operations.approve(operations.agree(run.id).id)
    assert run.outcome == "needs-me"
    fake.script = happy[5:]
    run = operations.resume(run.id)
    assert "5-hour limit" in fake.calls[6]["prompt"]                     # the build, run again, knows why
    assert "Resumed at build" in git(sprint_target, "log", "--format=%s", run.branch)


# ---- the plan check, and the record of the tests (FR-095) ----

POINT = "the plan says the CHECK refuses it, but NOT NULL is checked first"
AMENDED = "Add hello.py that prints hello; NOT NULL is checked first."


@pytest.mark.fr("FR-095")
@pytest.mark.fr("FR-104")
def test_a_sprints_plan_is_checked_in_the_dialogue_before_the_one_approval_and_the_check_is_not_a_gate():
    """Since FR-119 the plan check speaks in the dialogue: it raises points on the planner's plan of its round, which
    the planner takes or declines in the next, in place of the steps check_plan and amend_plan."""
    steps = tables.SPRINT_STEPS
    check = workflow.get("dialogue_check", steps)
    assert (check.persona, check.capabilities, check.may_change, check.model) == ("reviewer", "read", "nothing",
                                                                                  "standard")
    assert not check.routes and {"blocking", "notes"} <= set(check.envelope)
    assert {"draft", "constitution", "ideals"} <= set(check.inputs)
    assert check.on_pass == workflow.WAIT and check.on_approve == "baseline" and check.revise_from == "dialogue_analyst"
    planner = workflow.get("dialogue_planner", steps)
    assert (planner.persona, planner.capabilities, planner.may_change) == ("planner", "read", "nothing")
    assert "declined" in planner.envelope and "plan_lines_within_length" in planner.smells


@pytest.mark.fr("FR-095")
@pytest.mark.fr("FR-104")
def test_the_checks_points_go_to_the_planner_who_amends_before_the_asker_is_asked(home, sprint_target, fake_notify):
    script = sprint()
    fake = FakeAgent([speaks(), planner_says(), speaks(blocking=()), speaks(blocking=[POINT]),
                      speaks(), planner_says(AMENDED), speaks(blocking=()), speaks(blocking=()), *script[4:]])
    drive_with(fake)
    run = operations.request("Add a greeting", sprint_target)
    assert operations.plan(run.id).text.startswith(AMENDED)                    # amended, then shown once
    amending = fake.calls[5]["prompt"]
    assert PLAN["plan"] in amending and POINT in amending
    run = operations.approve(operations.agree(run.id).id)
    assert run.outcome == "accepted"


@pytest.mark.fr("FR-095")
def test_the_record_holds_the_tests_before_and_after_the_build(home, sprint_target, fake_notify):
    run, _ = to_the_end(sprint_target, FakeAgent(sprint()))
    record = git(sprint_target, "show", f"{run.branch}:{run_record.name(run)}")
    tests = record[record.index("## The tests before and after the build"):]
    assert "### Before the build" in tests and "### After the build" in tests and "passed" in tests


@pytest.mark.fr("FR-095")
@pytest.mark.parametrize("prompt", ["plan.md", "dialogue_planner.md"])
def test_the_planner_is_asked_to_name_departures_and_a_test_for_every_refusal(prompt):
    text = (config.PROMPTS_DIR / prompt).read_text()
    assert "differs from" in text and "every refusal" in text


@pytest.mark.fr("FR-095")
def test_the_plan_check_is_shown_the_plan_it_checks(home, sprint_target, fake_notify):
    """Run 29: the check was handed '(none)', because no plan had yet been shown to the operator."""
    script = sprint()
    fake = FakeAgent(script)
    drive_with(fake)
    operations.request("Add a greeting", sprint_target)
    checked = next(c["prompt"] for c in fake.calls if c["prompt"].startswith("# Task: check the plan in the dialogue"))
    assert PLAN["plan"] in checked


# ---- from run 30's retro (FR-096) ----

@pytest.mark.fr("FR-096")
def test_a_long_test_run_keeps_its_beginning_as_well_as_its_end():
    from factory import checks
    lines = [f"line {n}" for n in range(5000)]
    kept = checks.kept_output(lines)
    assert kept.startswith("line 0") and kept.endswith("line 4999") and "lines left out" in kept
    assert len(kept) <= checks.OUTPUT_LIMIT + 100
    assert checks.kept_output(["short"]) == "short"


@pytest.mark.fr("FR-096")
@pytest.mark.parametrize("prompt, says", [
    ("plan.md", "Do not predict which tests"),
    ("plan.md", "in the form the code will use"),
    ("dialogue_check.md", "name the one the plan should take"),
])
def test_the_prompts_carry_the_retros_lessons(prompt, says):
    assert says in (config.PROMPTS_DIR / prompt).read_text()


@pytest.mark.fr("FR-098")
@pytest.mark.parametrize("prompt, says", [
    ("dialogue_check.md", "from that test's own setup"),  # bttr_erp run 56: a file number vouched for by another row
    ("dialogue_check.md", "read as a regular expression"),  # run 56: '(3)' passed to match=
    ("dialogue_check.md", "every kind of input the rule covers"),  # run 55: a cast measured for VARCHAR, wrong for CHAR
    ("dialogue_check.md", "the remedy"),  # run 54: a refusal whose remedy led to the loss it prevents
    ("write_tests.md", "You cannot run the tests"),                # runs 53 to 56: the test writer has no shell
    ("build.md", "test_defect"),
    ("mend_tests.md", "Do not weaken"),
])
def test_the_prompts_carry_what_bttr_erps_runs_53_to_56_taught(prompt, says):
    assert says in (config.PROMPTS_DIR / prompt).read_text()


@pytest.mark.fr("FR-099")
def test_the_judges_diff_leaves_out_the_runs_own_record(home, sprint_target, fake_notify):
    """The record holds the request and the plan, which the architect and the final review are already given."""
    fake = FakeAgent(sprint())
    run, _ = to_the_end(sprint_target, fake)
    assert run.outcome == "accepted"
    architect = [call["prompt"] for call in fake.calls if call["persona"].startswith("# Architect")][-1]   # not the
    # architect of the dialogue, who speaks before anything is built
    final_review = [call["prompt"] for call in fake.calls if call["persona"].startswith("# Reviewer")][-1]
    for prompt in (architect, final_review):
        assert "diff --git a/hello.py" in prompt and "diff --git a/docs/runs/" not in prompt
    assert "docs/runs/" in git(run.workspace, "diff", "--name-only", run.base_commit)      # it is still in the branch


@pytest.mark.fr("FR-099")
@pytest.mark.parametrize("step, needs", [("retro", ("ideals", "constitution")),
                                         ("dialogue_planner", ("test_paths", "docs_paths")),
                                         ("dialogue_check", ("test_paths", "docs_paths"))])
def test_the_retro_is_given_the_rules_and_the_planners_where_each_step_may_write(step, needs):
    entry = workflow.get(step, tables.SPRINT_STEPS)
    assert set(needs) <= set(entry.inputs)
    text = (config.PROMPTS_DIR / f"{step}.md").read_text()
    assert all("{{" + name + "}}" in text for name in needs)


@pytest.mark.fr("FR-099")
@pytest.mark.parametrize("prompt, says", [
    ("plan.md", "Give no step a file it may not write"),       # bttr_erp runs 52 and 53: a requirements row, a CHANGELOG
    ("dialogue_check.md", "a file that step may not write"),
    ("retro.md", "outranks"),                                  # run 53: a parity ideal against the constitution
    ("architecture_review.md", "backlog-done.md"),             # runs 53, 55, 56: a backlog too long to read or search
])
def test_the_prompts_carry_the_smaller_lessons_of_runs_52_to_56(prompt, says):
    assert says in (config.PROMPTS_DIR / prompt).read_text()


@pytest.mark.fr("FR-102")
def test_what_was_asked_and_answered_in_planning_reaches_the_plan_check_and_the_final_review(home, sprint_target, fake_notify):
    """bttr_erp run 60: the plan check contradicted a measurement it had never been shown."""
    asked = "What does a read of the period column return?"
    script = sprint()
    fake = FakeAgent([speaks(), planner_says(measure=[asked]), speaks(blocking=()), speaks(blocking=()), *script])
    drive_with(fake)
    run = operations.request("Add a greeting", sprint_target)
    run = operations.answer(run.id, "A psycopg Range, measured on 18.6.")
    run = operations.approve(operations.agree(run.id).id)
    assert run.outcome == "accepted", run.reason
    reviewers = [call["prompt"] for call in fake.calls if call["persona"].startswith("# Reviewer")]
    for prompt in (reviewers[1], reviewers[-1]):                    # the plan check of round 2, and the final review
        assert asked in prompt
        assert "A psycopg Range, measured on 18.6." in prompt and "operator" in reviewers[-1]
    builder = next(call["prompt"] for call in fake.calls if call["persona"].startswith("# Code writer"))
    assert "A psycopg Range, measured on 18.6." not in builder       # the plan carries what the builder needs


@pytest.mark.fr("FR-102")
@pytest.mark.parametrize("prompt, says", [
    ("dialogue_check.md", "the answer stands"),
    ("converge.md", "the answer stands"),
])
def test_the_judges_are_told_a_measured_answer_outranks_the_request(prompt, says):
    assert says in (config.PROMPTS_DIR / prompt).read_text()


@pytest.mark.fr("FR-104")
@pytest.mark.parametrize("prompt, says", [
    ("dialogue_check.md", "what makes it fail before the build"),  # bttr_erp run 62: tests that already passed
    ("dialogue_check.md", "a table missing from it"),  # run 62: a new list with no fallback
    ("dialogue_check.md", "module docstring"),  # run 58: a docstring the change made untrue
    ("dialogue_planner.md", "Decline a point"),
    ("document.md", "docs/runs/"),                                 # runs 62 and 63: the account was overwritten
])
def test_the_prompts_carry_what_runs_58_to_63_taught(prompt, says):
    assert says in (config.PROMPTS_DIR / prompt).read_text()


@pytest.mark.fr("FR-106")
@pytest.mark.parametrize("prompt, says", [
    ("dialogue_check.md", "would still pass if the rule it names were broken"),  # run 69: a key from the wrong table
    ("dialogue_check.md", "the whole package"),  # run 69: a reworded phrase left in another package
    ("write_tests.md", "Never drop a case the plan lists"),          # run 69: the only case of its kind was dropped
])
def test_the_prompts_carry_what_run_69_taught(prompt, says):
    assert says in (config.PROMPTS_DIR / prompt).read_text()
