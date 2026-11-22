"""The plain sprint: one plan, one approval, then build to the end with a sprint review and a retro (FR-093).

Also the three factory fixes the first retro asked for that apply to every cycle (FR-094).
"""
import pytest

from factory import config, operations, run_record, tables, workflow
from factory.store import open_store
from tests.conftest import ARCHITECT, BUILD, DOCUMENT, PLAN, WRITE_TESTS, commit_files, drive_with, git, to_the_end
from tests.fake_agent import FakeAgent

ACCEPT = {"envelope": {"verdict": "accept", "unbuilt": [], "details": ["named it hello.py"], "requirement_changes": [],
                       "reasons": ["it matches the plan"], "ideals_broken": ["two modules say the same thing"]}}
RETRO = {"envelope": {"summary": "fine", "worked": ["one approval"], "did_not": [], "opportunities": [], "threats": []}}


def sprint(**changes):
    entries = {"plan": {"envelope": PLAN}, "check_plan": {"envelope": {"findings": []}}, "write_tests": WRITE_TESTS, "build": BUILD, "architecture_review": ARCHITECT,
               "document": DOCUMENT, "converge": ACCEPT, "retro": RETRO}
    entries.update(changes)
    return [entries[n] for n in ("plan", "check_plan", "write_tests", "build", "architecture_review", "document", "converge", "retro")]


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
    assert tables.table_for(spec_kit, "tidy-code", cycle) is tables.TIDY_CODE      # a tidy is a tidy whatever the cycle


@pytest.mark.fr("FR-093")
def test_the_sprint_waits_once_and_ends_with_the_sprint_review_and_the_retro():
    steps = tables.SPRINT_STEPS
    assert [s.name for s in steps if s.on_pass == workflow.WAIT] == ["check_plan"]
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
    fake = FakeAgent(happy[:3] + [{"error": "You've hit your 5-hour limit"}])
    drive_with(fake)
    run = operations.request("Add a greeting", sprint_target)
    run = operations.approve(run.id)
    assert run.outcome == "needs-me"
    fake.script = happy[3:]
    run = operations.resume(run.id)
    assert "5-hour limit" in fake.calls[4]["prompt"]                     # the build, run again, knows why
    assert "factory: resumed (run" in git(sprint_target, "log", "--format=%s", run.branch)


# ---- the plan check, and the record of the tests (FR-095) ----

CHECKED = {"envelope": {"findings": ["the plan says the CHECK refuses it, but NOT NULL is checked first"]}}


@pytest.mark.fr("FR-095")
def test_a_sprints_plan_is_checked_before_the_one_approval_and_the_check_is_not_a_gate():
    steps = tables.SPRINT_STEPS
    check = workflow.get("check_plan", steps)
    assert workflow.get("plan", steps).on_pass == "check_plan"
    assert check.on_pass == workflow.WAIT and check.on_approve == "baseline" and check.revise_from == "plan"
    assert (check.capabilities, check.may_change, check.model) == ("read", "nothing", "standard")
    assert not check.routes and {"plan", "constitution", "ideals"} <= set(check.inputs)


@pytest.mark.fr("FR-095")
def test_what_the_operator_approves_is_the_planners_plan_with_the_checks_findings(home, sprint_target, fake_notify):
    script = sprint()
    drive_with(FakeAgent(script[:1] + [CHECKED] + script[2:]))
    run = operations.request("Add a greeting", sprint_target)
    shown = operations.plan(run.id).text
    assert PLAN["plan"] in shown and "NOT NULL is checked first" in shown
    run = operations.approve(run.id)
    assert run.outcome == "accepted"


@pytest.mark.fr("FR-095")
def test_the_record_holds_the_tests_before_and_after_the_build(home, sprint_target, fake_notify):
    script = sprint()
    run, _ = to_the_end(sprint_target, FakeAgent(script[:1] + [CHECKED] + script[2:]))
    record = git(sprint_target, "show", f"{run.branch}:{run_record.name(run)}")
    tests = record[record.index("## The tests before and after the build"):]
    assert "### Before the build" in tests and "### After the build" in tests and "passed" in tests


@pytest.mark.fr("FR-095")
def test_the_planner_is_asked_to_name_departures_and_a_test_for_every_refusal():
    text = (config.PROMPTS_DIR / "plan.md").read_text()
    assert "differs from" in text and "every refusal" in text


@pytest.mark.fr("FR-095")
def test_the_plan_check_is_shown_the_plan_it_checks(home, sprint_target, fake_notify):
    """Run 29: the check was handed '(none)', because no plan had yet been shown to the operator."""
    script = sprint()
    fake = FakeAgent(script)
    drive_with(fake)
    operations.request("Add a greeting", sprint_target)
    checked = next(c["prompt"] for c in fake.calls if c["prompt"].startswith("# Task: check the plan"))
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
    ("check_plan.md", "name the one the plan should take"),
])
def test_the_prompts_carry_the_retros_lessons(prompt, says):
    assert says in (config.PROMPTS_DIR / prompt).read_text()


@pytest.mark.fr("FR-098")
@pytest.mark.parametrize("prompt, says", [
    ("check_plan.md", "from that test's own setup"),               # bttr_erp run 56: a file number vouched for by another row
    ("check_plan.md", "read as a regular expression"),             # run 56: '(3)' passed to match=
    ("check_plan.md", "every kind of input the rule covers"),      # run 55: a cast measured for VARCHAR, wrong for CHAR
    ("check_plan.md", "the remedy"),                               # run 54: a refusal whose remedy led to the loss it prevents
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
    architect = next(call["prompt"] for call in fake.calls if call["persona"].startswith("# Architect"))
    final_review = [call["prompt"] for call in fake.calls if call["persona"].startswith("# Reviewer")][-1]
    for prompt in (architect, final_review):
        assert "diff --git a/hello.py" in prompt and "diff --git a/docs/runs/" not in prompt
    assert "docs/runs/" in git(run.workspace, "diff", "--name-only", run.base_commit)      # it is still in the branch


@pytest.mark.fr("FR-099")
@pytest.mark.parametrize("step, needs", [("retro", ("ideals", "constitution")), ("plan", ("test_paths", "docs_paths")),
                                         ("check_plan", ("test_paths", "docs_paths"))])
def test_the_retro_is_given_the_rules_and_the_planners_where_each_step_may_write(step, needs):
    entry = workflow.get(step, tables.SPRINT_STEPS)
    assert set(needs) <= set(entry.inputs)
    text = (config.PROMPTS_DIR / f"{step}.md").read_text()
    assert all("{{" + name + "}}" in text for name in needs)


@pytest.mark.fr("FR-099")
@pytest.mark.parametrize("prompt, says", [
    ("plan.md", "Give no step a file it may not write"),       # bttr_erp runs 52 and 53: a requirements row, a CHANGELOG
    ("check_plan.md", "a file that step may not write"),
    ("retro.md", "outranks"),                                  # run 53: a parity ideal against the constitution
    ("architecture_review.md", "backlog-done.md"),             # runs 53, 55, 56: a backlog too long to read or search
])
def test_the_prompts_carry_the_smaller_lessons_of_runs_52_to_56(prompt, says):
    assert says in (config.PROMPTS_DIR / prompt).read_text()


@pytest.mark.fr("FR-102")
def test_what_was_asked_and_answered_in_planning_reaches_the_plan_check_and_the_final_review(home, sprint_target, fake_notify):
    """bttr_erp run 60: the plan check contradicted a measurement it had never been shown."""
    asks = {"envelope": {"measure": "What does a read of the period column return?"}}
    fake = FakeAgent([asks, *sprint()])
    run, _ = to_the_end(sprint_target, fake)
    assert run.state == "awaiting_approval" and run.current_step == "plan"
    run = operations.answer(run.id, "A psycopg Range, measured on 18.6.")
    while run.state == "awaiting_approval":
        run = operations.approve(run.id)
    assert run.outcome == "accepted", run.reason
    reviewers = [call["prompt"] for call in fake.calls if call["persona"].startswith("# Reviewer")]
    for prompt in (reviewers[0], reviewers[-1]):                    # the plan check, and the final review
        assert "What does a read of the period column return?" in prompt
        assert "A psycopg Range, measured on 18.6." in prompt and "operator" in prompt
    builder = next(call["prompt"] for call in fake.calls if call["persona"].startswith("# Code writer"))
    assert "A psycopg Range, measured on 18.6." not in builder       # the plan carries what the builder needs


@pytest.mark.fr("FR-102")
@pytest.mark.parametrize("prompt, says", [
    ("check_plan.md", "the answer stands"),
    ("converge.md", "the answer stands"),
])
def test_the_judges_are_told_a_measured_answer_outranks_the_request(prompt, says):
    assert says in (config.PROMPTS_DIR / prompt).read_text()
