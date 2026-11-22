"""Whole runs through the fake agent, with a real target, real git and the real test command.

Each test scripts what the five personas "do" and asserts what the factory makes of it.
"""
import pathlib
import shutil

import pytest

from factory import config, operations, records, workspace
from factory.store import open_store
from factory.workspace import Workspace
from tests.conftest import commit_files, to_the_end, ARCHITECT, BUILD, CODE, DOCUMENT, drive_with, git, in_process, names, ORDER, PLAN, record, REVIEW, script, TEST, WRITE_TESTS, WRONG
from tests.fake_agent import FakeAgent

@pytest.mark.fr("FR-034")
@pytest.mark.fr("FR-006")
@pytest.mark.fr("FR-009")
@pytest.mark.fr("FR-013")
@pytest.mark.fr("FR-015")
@pytest.mark.fr("FR-017")
@pytest.mark.fr("FR-018")
@pytest.mark.fr("FR-019")
@pytest.mark.fr("FR-025")
@pytest.mark.fr("FR-030")
def test_the_happy_path_from_an_empty_target(cycle):
    run, fake, store, target = cycle(script())
    assert names(store, run) == ORDER
    assert (run.outcome, bool(run.reason)) == ("accepted", True)
    assert "no prior tests" in record(store, run, "baseline").checks[-1]["note"]

    red, green = record(store, run, "red"), record(store, run, "test")
    assert red.passed and "ModuleNotFoundError" in red.produced["output"]       # failed first, for the right reason
    assert green.passed and "2 passed" in green.produced["output"]

    assert git(target, "rev-list", "--count", f"{run.base_commit}..{run.branch}") == "6"
    subjects = git(target, "log", "--format=%s", f"{run.base_commit}..{run.branch}").splitlines()
    assert subjects == ["Accepted: Add hello.py that prints hello.",          # FR-103: what each holds
                        "Docs: Added a greeting.", "Backlog: sound, with one thing to tidy later",
                        "Build: added greet", "Tests: greeting tests", "Plan: Add hello.py that prints hello."]
    assert git(target, "show", f"{run.branch}:hello.py") == CODE.strip()
    assert "Added a greeting" in git(target, "show", f"{run.branch}:CHANGELOG.md")
    assert record(store, run, "document").produced["summary"] == "Added a greeting."

    assert len(fake.calls) == 6, "tests are run by code; no agent is asked whether they passed"
    assert cycle.notify[-1] == (f"Run {run.id}: accepted", run.reason)
    assert store.get("runs", run.id).outcome == "accepted"                          # still there afterwards
    kinds = [e.kind for e in records.events_after(store, run.id, limit=5000)]
    assert kinds.count("step_start") == 10 and kinds.count("step_end") == 10
    assert kinds.count("commit") == 4 and kinds.count("check") >= 10 * 2
    assert [e.kind for e in records.events_after(store, run.id, limit=5000)][-1] == "notify"


@pytest.mark.fr("FR-035")
def test_a_second_request_goes_through_the_same_cycle_and_runs_the_first_ones_tests(cycle):
    first, _, store, target = cycle(script())
    git(target, "merge", "-q", "--ff-only", first.branch)
    bye_test = "from bye import farewell\n\n\ndef test_farewell():\n    assert farewell() == 'bye'\n"
    second, _, store, _ = cycle(script(
        write_tests={"envelope": {"summary": "farewell", "test_files": ["tests/test_bye.py"], "edge_cases": ["none given"]},
                     "files": {"tests/test_bye.py": bye_test}},
        build={"envelope": {"summary": "bye", "files_changed": ["bye.py"], "verdict": "accept", "reasons": []},
               "files": {"bye.py": "def farewell():\n    return 'bye'\n"}}), target=target, request="Add a farewell")
    assert second.outcome == "accepted" and names(store, second) == ORDER
    baseline = record(store, second, "baseline")
    assert "2 passed" in baseline.produced["output"] and "no prior tests" not in baseline.produced["output"]
    assert "3 passed" in record(store, second, "test").produced["output"]


@pytest.mark.fr("FR-010")
@pytest.mark.fr("FR-028")
def test_a_failed_build_is_sent_back_with_the_failure(cycle):
    wrong = dict(BUILD, files={"hello.py": WRONG})
    run, fake, store, _ = cycle(script(build=[wrong, BUILD]))
    assert run.outcome == "accepted"
    assert names(store, run) == ["plan", "baseline", "write_tests", "red", "build", "test", "build", "test",
                                 "architecture_review", "document", "review", "finish"]
    builds = [s for s in store.query("steps", {"run_id": run.id}) if s.name == "build"]
    assert [b.attempt for b in builds] == [1, 2]
    retry = fake.calls[3]["prompt"]
    assert "tests_pass" in retry and "assert 'goodbye' == 'hello'" in retry      # the failing output, passed back
    assert "tests/test_hello.py" in fake.calls[2]["prompt"]                      # told which tests to satisfy
    first_test = record(store, run, "test", 0)
    assert first_test.passed is False and first_test.failure == "check"


# A test that expects what the plan does not: no build can pass it, and the builder may not touch it.
WRONG_TEST = dict(WRITE_TESTS, files={"tests/test_hello.py": TEST.replace("== 'hello'\n\n\ndef", "== 'hullo'\n\n\ndef")})
DEFECT = dict(BUILD, envelope=dict(BUILD["envelope"], verdict="test_defect",
                                   reasons=["test_greets expects 'hullo'; the plan says hello"]))
MENDED = {"envelope": {"summary": "the expected greeting was misspelled", "mended": ["tests/test_hello.py"]},
          "files": {"tests/test_hello.py": TEST}}
NOT_MENDED = {"envelope": {"summary": "the test is as the plan gives it", "mended": []}}


@pytest.mark.fr("FR-097")
def test_a_builder_that_reports_a_test_no_build_can_pass_sends_it_to_the_test_writer_once(cycle):
    run, fake, store, _ = cycle(script(write_tests=WRONG_TEST, build=[DEFECT, MENDED]))
    assert run.outcome == "accepted"
    assert names(store, run) == ["plan", "baseline", "write_tests", "red", "build", "mend_tests", "test",
                                 "architecture_review", "document", "review", "finish"]   # no second build, no red
    mend = fake.calls[3]
    assert mend["persona"].startswith("# Test writer")
    assert "test_greets expects 'hullo'; the plan says hello" in mend["prompt"]           # told what the builder found
    assert record(store, run, "build").failure == "check" and record(store, run, "test").passed
    assert (pathlib.Path(run.workspace) / "hello.py").read_text() == CODE                  # the build's work was kept


@pytest.mark.fr("FR-097")
def test_a_second_report_of_a_defective_test_is_not_chased(cycle):
    again = dict(DEFECT, files={})
    run, _, store, _ = cycle(script(write_tests=WRONG_TEST, build=[DEFECT, NOT_MENDED, again, again]))
    assert run.outcome == "needs-me" and "build step has run 3 times" in run.reason
    assert names(store, run)[4:] == ["build", "mend_tests", "test", "build", "test", "build", "test"]


@pytest.mark.fr("FR-097")
def test_the_test_writer_mending_a_test_may_not_touch_the_code(cycle):
    meddled = dict(MENDED, files={"tests/test_hello.py": TEST, "hello.py": WRONG})
    run, _, store, _ = cycle(script(write_tests=WRONG_TEST, build=[DEFECT, meddled]))
    assert run.outcome == "needs-me" and "mend_tests step changed what it may not" in run.reason


LONG = "def greet(name=''):\n    return 'hello'  # " + "x" * 60 + "\n"


@pytest.mark.fr("FR-101")
def test_a_line_longer_than_the_codebase_allows_is_sent_back_naming_it(cycle):
    limited = {".factory.toml": config.DEFAULT_FACTORY_TOML.replace("line_length = 0", "line_length = 60")}
    run, fake, store, _ = cycle(script(build=[dict(BUILD, files={"hello.py": LONG}), BUILD]), files=limited)
    assert run.outcome == "accepted"
    assert names(store, run)[4:7] == ["build", "build", "test"]                # found before the tests were run
    first = record(store, run, "build", 0)
    assert first.failure == "check" and "lines_within_length" in [c["name"] for c in first.checks if not c["passed"]]
    retry = fake.calls[3]["prompt"]
    assert "hello.py:2" in retry and "60" in retry                              # told which line, and the limit


@pytest.mark.fr("FR-101")
def test_no_line_length_is_asked_of_a_codebase_that_sets_none(cycle):
    run, _, store, _ = cycle(script(build=dict(BUILD, files={"hello.py": LONG})))
    assert run.outcome == "accepted" and names(store, run).count("build") == 1


@pytest.mark.fr("FR-103")
def test_each_commit_says_what_it_holds_and_which_run_made_it(cycle):
    titled = {"envelope": dict(PLAN, plan="# Greet the reader\n\nAdd hello.py that prints hello.")}
    long = dict(BUILD, envelope=dict(BUILD["envelope"], summary="added greet " + "and a great deal more " * 8))
    run, _, _, target = cycle(script(plan=titled, build=long), request="Add a greeting.\nOne file is enough.")
    log = git(target, "log", "--format=%s%x00%b%x01", f"{run.base_commit}..{run.branch}").split("\x01")
    commits = [entry.strip().split("\x00") for entry in log if entry.strip()]
    subjects = [subject for subject, _ in commits]
    assert subjects[-1] == "Plan: Greet the reader"                       # a plan is named by its heading
    assert subjects[0] == "Accepted: Greet the reader"
    build = next(s for s in subjects if s.startswith("Build: "))
    assert len(build) <= 72 and build.endswith("…")                         # a long summary is cut at a word
    for _, body in commits:
        assert f"Run {run.id}: Add a greeting." in body and f"Factory-Run: {run.id}" in body
    steps = [line.split(": ", 1)[1] for _, body in commits for line in body.splitlines() if line.startswith("Factory-Step: ")]
    assert steps == ["finish", "document", "architecture_review", "test", "red", "plan"]
    record = next(body for subject, body in commits if subject.startswith("Accepted: "))
    assert "it matches the request" in record and "minutes of steps" in record        # the run, in brief


@pytest.mark.fr("FR-103")
def test_a_build_sent_back_is_named_by_what_it_built_and_the_record_says_why(cycle):
    first = dict(BUILD, envelope=dict(BUILD["envelope"], summary="added greet"), files={"hello.py": WRONG})
    fix = dict(BUILD, envelope=dict(BUILD["envelope"], summary="corrected the greeting's word"))
    run, _, _, target = cycle(script(build=[first, fix]))
    subjects = git(target, "log", "--format=%s", f"{run.base_commit}..{run.branch}").splitlines()
    assert "Build: added greet" in subjects                                   # the build, not its last fix
    record = git(target, "show", f"{run.branch}:docs/runs/{run.branch.removeprefix('factory/')}.md")
    assert "| test | 1 | check: tests_pass |" in record                       # why it went back
    assert "## What changed" in record and "Added a greeting." in record       # the documenter's account, kept


LONG_PLAN = {"envelope": dict(PLAN, plan="Add hello.py:\n\n```python\nGREETING = '" + "h" * 70 + "'\n```\n")}


@pytest.mark.fr("FR-104")
def test_a_plan_whose_code_is_longer_than_the_codebase_allows_is_written_again(cycle):
    limited = {".factory.toml": config.DEFAULT_FACTORY_TOML.replace("line_length = 0", "line_length = 60")}
    run, fake, store, _ = cycle(script(plan=[LONG_PLAN, {"envelope": PLAN}]), files=limited)
    assert run.outcome == "accepted"
    assert names(store, run)[:2] == ["plan", "plan"]
    assert "60" in fake.calls[1]["prompt"] and "lines_within_length" in fake.calls[1]["prompt"]


@pytest.mark.fr("FR-011")
def test_the_attempt_limit_set_on_the_request_is_the_one_used(cycle):
    wrong = dict(BUILD, files={"hello.py": WRONG})
    run, _, store, _ = cycle(script(build=[wrong, wrong]), attempts=2)
    assert run.outcome == "needs-me" and "2 times" in run.reason


@pytest.mark.fr("FR-007")
def test_tests_that_pass_before_anything_is_built_are_written_again(cycle):
    trivial = dict(WRITE_TESTS, files={"tests/test_hello.py": "def test_nothing():\n    assert True\n"})
    run, fake, store, _ = cycle(script(write_tests=[trivial, WRITE_TESTS]))
    assert run.outcome == "accepted"
    assert names(store, run)[:6] == ["plan", "baseline", "write_tests", "red", "write_tests", "red"]
    assert "pass before" in fake.calls[2]["prompt"]
    assert record(store, run, "red", 0).passed is False and record(store, run, "red", 1).passed


@pytest.mark.fr("FR-012")
@pytest.mark.fr("FR-015")
@pytest.mark.fr("FR-017")
def test_a_rejecting_review_ends_the_run_rejected(cycle):
    reject = {"envelope": {"verdict": "reject", "reasons": ["the greeting has no capital letter"], "ideals_broken": []}}
    run, _, store, target = cycle(script(review=reject))
    assert run.outcome == "rejected" and "no capital letter" in run.reason
    assert names(store, run)[-1] == "review" and "finish" not in names(store, run)
    assert git(target, "rev-list", "--count", f"{run.base_commit}..{run.branch}") == "6"   # the work is kept, and its record
    assert cycle.notify[-1] == (f"Run {run.id}: rejected", run.reason)


@pytest.mark.fr("FR-032")
@pytest.mark.parametrize("files, named", [
    ({"hello.py": CODE, "tests/test_hello.py": "def test_weakened():\n    assert True\n"}, "tests/test_hello.py"),
    ({"hello.py": CODE, "tests/test_extra.py": "def test_x():\n    assert True\n"}, "tests/test_extra.py"),
    ({"hello.py": CODE, "tests/test_old.py": None}, "tests/test_old.py"),
    ({"hello.py": CODE, "tests/conftest.py": "collect_ignore = ['test_hello.py']\n"}, "tests/conftest.py"),
    ({"hello.py": CODE, ".factory.toml": 'test_command = "true"\n'}, ".factory.toml"),
])
def test_a_code_writer_that_touches_the_tests_is_undone_and_the_run_stops(cycle, files, named):
    old = {"tests/test_old.py": "def test_old():\n    assert True\n"}
    run, _, store, target = cycle(script(build=dict(BUILD, files=files))[:3], files=old)
    assert run.outcome == "needs-me" and named in run.reason and "build" in run.reason
    assert record(store, run, "build").failure == "guard"
    assert git(run.workspace, "status", "--porcelain") == ""                 # undone
    assert git(run.workspace, "show", "HEAD:tests/test_hello.py") == TEST.strip()
    guard = [e for e in records.events_after(store, run.id, limit=5000) if e.kind == "guard"]
    assert guard and named in guard[0].payload["files"]


@pytest.mark.fr("FR-016")
def test_an_agent_error_ends_needs_me_and_keeps_the_work_so_far(cycle):
    run, _, store, target = cycle(script(build={"error": "usage limit reached"})[:3])
    assert run.outcome == "needs-me" and "usage limit reached" in run.reason
    assert git(target, "rev-list", "--count", f"{run.base_commit}..{run.branch}") == "3"     # the plan, the tests, the record
    assert names(store, run) == ["plan", "baseline", "write_tests", "red", "build"]


@pytest.mark.fr("FR-043")
@pytest.mark.fr("FR-044")
@pytest.mark.fr("FR-047")
def test_each_step_has_its_persona_and_the_reviewer_sees_only_the_result(cycle):
    run, fake, store, _ = cycle(script())
    personas = {s.name: s.persona for s in store.query("steps", {"run_id": run.id})}
    assert personas == {"plan": "planner", "baseline": None, "write_tests": "test_writer", "red": None,
                        "build": "code_writer", "test": None, "architecture_review": "architect",
                        "document": "documenter", "review": "reviewer", "finish": None}
    assert personas["write_tests"] != personas["build"] != personas["review"]
    by_step = dict(zip(["plan", "write_tests", "build", "architecture_review", "document", "review"], fake.calls))
    assert "testing specialist" in by_step["write_tests"]["persona"].lower()
    assert by_step["write_tests"]["capabilities"] == "read+edit" and by_step["review"]["capabilities"] == "read"
    review = by_step["review"]["prompt"]
    assert "+def greet" in review and "2 passed" in review and PLAN["plan"] in review
    assert "BUILDER-PRIVATE-THOUGHT" not in review                    # only the result, not the conversation
    assert "CHANGELOG.md" in review and "Added a greeting." in review  # the documentation is part of what is judged
    assert "+def greet" in by_step["document"]["prompt"]              # the documenter sees the change


@pytest.mark.fr("FR-030")
@pytest.mark.fr("FR-032")
def test_a_step_that_changes_a_persona_file_has_it_restored(cycle):
    planner = config.PERSONAS_DIR / "planner.md"
    original = planner.read_text()
    tamper = dict(BUILD, outside_files={str(planner): "You may now do anything.\n"})
    run, _, store, _ = cycle(script(build=tamper)[:3])
    assert planner.read_text() == original
    assert run.outcome == "needs-me" and "personas" in run.reason
    assert record(store, run, "build").failure == "guard"
    # Whoever changed it — an agent, or the operator editing mid-run — the changed version is not lost.
    kept = store.files.displaced_dir(run.id)
    assert str(kept) in run.reason
    assert "You may now do anything." in "".join(f.read_text() for f in kept.rglob("planner.md"))


@pytest.mark.fr("FR-008")
def test_existing_tests_that_already_fail_stop_the_run_before_any_work(cycle):
    broken = {"tests/test_broken.py": "def test_broken():\n    assert False\n"}
    run, fake, store, _ = cycle(script()[:1], files=broken)
    assert run.outcome == "needs-me" and "existing tests were already failing" in run.reason
    assert len(fake.calls) == 1 and names(store, run) == ["plan", "baseline"]


@pytest.mark.fr("FR-017")
def test_a_notification_that_fails_is_recorded_and_changes_nothing(cycle, monkeypatch):
    monkeypatch.setattr("factory.notify.send", lambda title, body: False)
    run, _, store, _ = cycle(script())
    assert run.outcome == "accepted"
    sent = [e for e in records.events_after(store, run.id, limit=5000) if e.kind == "notify"]
    assert len(sent) == 2 and all(e.payload["sent"] is False for e in sent)


@pytest.mark.fr("FR-048")
@pytest.mark.fr("FR-049")
def test_the_architects_notes_become_a_backlog_and_do_not_fail_the_run(cycle):
    run, fake, store, target = cycle(script())
    assert run.outcome == "accepted"
    review = record(store, run, "architecture_review")
    assert (review.persona, review.passed) == ("architect", True)
    assert review.produced["suggestions"] == ["the greeting text is repeated; give it one home"]   # on the record
    assert "greeting text is repeated" in git(target, "show", f"{run.branch}:docs/backlog.md")     # in the codebase
    architect = fake.calls[3]
    assert architect["capabilities"] == "read+edit" and "lisp" in architect["persona"].lower()
    assert "+def greet" in architect["prompt"] and "docs/" in architect["prompt"]      # it sees the change
    assert "docs/backlog.md" in fake.calls[5]["prompt"]                                # and the reviewer sees the backlog


@pytest.mark.fr("FR-049")
@pytest.mark.fr("FR-050")
def test_what_a_failed_architect_wrote_does_not_slip_into_the_branch(cycle):
    """A failed advisory step may have left a half-written file. It must not be committed by the next step."""
    half = {"text": "I ran out of time.", "files": {"docs/backlog.md": "- a half-finished thou"}}
    run, _, store, target = cycle(script(architecture_review=half))
    assert run.outcome == "accepted"
    files = git(target, "ls-tree", "-r", "--name-only", run.branch).split()
    assert "docs/backlog.md" not in files and "CHANGELOG.md" in files
    assert git(target, "rev-list", "--count", f"{run.base_commit}..{run.branch}") == "5"    # plan, tests, change, docs, record


# ---- tidying: a change that must not alter behaviour (FR-066) ----

EXISTING = {"hello.py": CODE,
            "tests/test_hello.py": TEST + "\n\ndef test_greets_again():\n    assert greet() == 'hello'\n"}
TRIMMED = {"envelope": {"summary": "removed a duplicate", "removed": ["test_greets_again"], "kept": ["test_greets"]},
           "files": {"tests/test_hello.py": TEST}}
TIDIED = {"envelope": {"summary": "named the greeting", "files_changed": ["hello.py"]},
          "files": {"hello.py": "GREETING = 'hello'\n\n\ndef greet(name=''):\n    return GREETING\n"}}


def tidy(home, tmp_path, fake_notify, kind, entries, name="tidy-target"):
    target = commit_files(operations.init_target(tmp_path / name), EXISTING)
    fake = FakeAgent(entries)
    run, _ = to_the_end(target, fake, "Tidy up", run_kind=kind)
    return run, fake, open_store(home), target


@pytest.mark.fr("FR-066")
def test_tidying_the_tests_needs_no_failing_test_and_leaves_the_code_alone(home, tmp_path, fake_notify):
    run, fake, store, target = tidy(home, tmp_path, fake_notify, "tidy-tests", [{"envelope": PLAN}, TRIMMED, REVIEW])
    assert run.outcome == "accepted", run.reason
    assert names(store, run) == ["plan", "baseline", "tidy_tests", "test", "review", "finish"]
    assert run.run_kind == "tidy-tests"
    assert "2 passed" in record(store, run, "test").produced["output"]          # down from three, all passing
    assert "test_greets_again" not in git(target, "show", f"{run.branch}:tests/test_hello.py")
    assert git(target, "show", f"{run.branch}:hello.py") == CODE.strip()        # the code did not change
    assert "testing specialist" in fake.calls[1]["persona"].lower()            # the test writer tidies tests


@pytest.mark.fr("FR-066")
def test_tidying_the_code_must_leave_every_test_passing(home, tmp_path, fake_notify):
    broke = dict(TIDIED, files={"hello.py": WRONG})
    run, fake, store, target = tidy(home, tmp_path, fake_notify, "tidy-code",
                                    [{"envelope": PLAN}, broke, TIDIED, REVIEW])
    assert run.outcome == "accepted", run.reason
    assert names(store, run) == ["plan", "baseline", "tidy_code", "test", "tidy_code", "test", "review", "finish"]
    assert "assert 'goodbye' == 'hello'" in fake.calls[2]["prompt"]             # told what it broke
    assert "GREETING" in git(target, "show", f"{run.branch}:hello.py")


@pytest.mark.fr("FR-065")
def test_a_test_writer_over_budget_is_sent_back_and_told_the_numbers(cycle, monkeypatch):
    monkeypatch.setattr(config, "DEFAULT_FACTORY_TOML", config.DEFAULT_FACTORY_TOML.replace(
        "test_budget_lines = 300", "test_budget_lines = 12"))
    padded = dict(WRITE_TESTS, files={"tests/test_hello.py": TEST + "\n# padding\n" * 20})
    run, fake, store, _ = cycle(script(write_tests=[padded, WRITE_TESTS]))
    assert run.outcome == "accepted"
    first = record(store, run, "write_tests", 0)
    assert first.passed is False and [c["name"] for c in first.checks if not c["passed"]] == ["tests_within_budget"]
    assert "budget" in fake.calls[2]["prompt"] and "12" in fake.calls[2]["prompt"]


@pytest.mark.fr("FR-066")
def test_a_review_that_rejects_a_tidy_sends_it_back_with_its_reasons(home, tmp_path, fake_notify):
    """Found on a real run: a precise, fixable review ended a 36-minute tidy instead of guiding a second attempt."""
    reject = {"envelope": {"verdict": "reject", "reasons": ["the empty-name rule now has no test"], "ideals_broken": []}}
    run, fake, store, _ = tidy(home, tmp_path, fake_notify, "tidy-tests",
                               [{"envelope": PLAN}, TRIMMED, reject, TRIMMED, REVIEW])
    assert run.outcome == "accepted", run.reason
    assert names(store, run) == ["plan", "baseline", "tidy_tests", "test", "review", "tidy_tests", "test", "review", "finish"]
    assert "the empty-name rule now has no test" in fake.calls[3]["prompt"]


@pytest.mark.fr("FR-065")
def test_the_test_budget_is_for_new_tests_and_a_tidy_is_told_it_does_not_apply():
    text = (config.PROMPTS_DIR / "tidy_tests.md").read_text().lower()
    assert "budget" in text and "does not apply" in text


# ---- resuming a run that stopped as needs-me (FR-067) ----

@pytest.mark.fr("FR-067")
def test_a_stopped_run_resumes_from_its_step_keeping_its_work_and_dropping_the_half_done(cycle, home):
    """Found on real runs: a usage limit stopped two runs at their last steps, after all the costly work."""
    half = {"error": "You've hit your 5-hour limit", "files": {"CHANGELOG.md": "- half writ"}}
    run, _, store, target = cycle(script(document=half)[:5])
    assert run.outcome == "needs-me" and run.current_step == "document"

    fake = FakeAgent([DOCUMENT, REVIEW])
    drive_with(fake)
    resumed = operations.resume(run.id)

    assert resumed.outcome == "accepted", resumed.reason
    assert [c["persona"] for c in fake.calls] == [fake.calls[0]["persona"], fake.calls[1]["persona"]]
    assert len(fake.calls) == 2                                   # only the steps not yet done
    assert names(store, run).count("build") == 1 and names(store, run)[-3:] == ["document", "review", "finish"]
    assert git(target, "show", f"{run.branch}:CHANGELOG.md") == "- Added a greeting."     # not the half-written one
    history = [e for e in store.query("events", {"run_id": run.id, "kind": "run_state"}) if "resumed_from" in e.payload]
    assert history and "5-hour limit" in history[0].payload["resumed_from"]["reason"]


@pytest.mark.fr("FR-067")
def test_resuming_after_failed_tests_keeps_what_the_build_wrote(cycle, home):
    """Found on bttr_erp's run 43: the build was right and a test was wrong, the builder may not change tests,
    and resuming after the operator mended the test threw the build's work away, so the tests failed again."""
    mistaken = dict(WRITE_TESTS, files={"tests/test_hello.py": TEST.replace("'hello'", "'hullo'")})
    run, _, store, target = cycle(script(write_tests=mistaken, build=[BUILD, BUILD])[:4], attempts=2)
    assert run.outcome == "needs-me" and run.current_step == "test"

    checkout = pathlib.Path(run.workspace)
    (checkout / "tests" / "test_hello.py").write_text(TEST)             # the operator mends the test, and commits it
    git(checkout, "add", "-A", "tests")
    git(checkout, "commit", "-q", "-m", "the operator's fix to a test")
    fake = FakeAgent([ARCHITECT, DOCUMENT, REVIEW])
    drive_with(fake)
    resumed = operations.resume(run.id)

    assert resumed.outcome == "accepted", resumed.reason
    assert names(store, run).count("build") == 2                        # the build is not asked again
    assert git(target, "show", f"{run.branch}:hello.py") == CODE.strip()


STOPPED = script(build={"error": "usage limit"})[:3]


def _accepted(cycle):
    return cycle(script())[0]


def _another_run_open(cycle):
    stopped, _, _, target = cycle(STOPPED)
    drive_with(FakeAgent([{"envelope": PLAN}]))
    operations.request("Something else", target)
    return stopped


def _checkout_gone(cycle):
    stopped = cycle(STOPPED)[0]
    Workspace.of(stopped).remove()
    return stopped


@pytest.mark.fr("FR-067")
@pytest.mark.parametrize("make, refused", [(_accepted, "only a run that ended as needs-me"),
                                           (_another_run_open, "has not ended"),
                                           (_checkout_gone, "checkout no longer exists")])
def test_resuming_is_refused_unless_the_run_stopped_as_needs_me_and_can_carry_on(cycle, make, refused):
    run = make(cycle)
    with pytest.raises(operations.Refused, match=refused):
        operations.resume(run.id)


@pytest.mark.fr("FR-067")
def test_resume_is_a_command(cycle, monkeypatch, capsys):
    from factory import cli
    stopped = cycle(STOPPED)[0]
    drive_with(FakeAgent(script()[2:]))
    assert cli.main(["resume", str(stopped.id)]) == 0 and "accepted" in capsys.readouterr().out




# ---- the plan travels with the code (FR-079) ----

def record_name(run):
    """The record carries the branch's own name: the time of the request and its first words (FR-081)."""
    return f"docs/runs/{run.branch.removeprefix('factory/')}.md"


@pytest.mark.fr("FR-079")
@pytest.mark.fr("FR-080")
@pytest.mark.fr("FR-081")
def test_a_run_leaves_its_record_with_the_code_from_approval_to_its_end(home, target, fake_notify):
    fake = drive_with(FakeAgent([{"envelope": PLAN}, {"envelope": dict(PLAN, plan="The second version.")}, *script()[1:]]))
    run = operations.request("Add a greeting", target)
    operations.revise(run.id, "Keep it to one file.")
    run = operations.approve(run.id)
    assert run.outcome == "accepted", run.reason
    name = record_name(run)
    at_approval = git(target, "show", f"{run.branch}~5:{name}")          # committed before the tests were written
    assert "The second version." in at_approval and "Keep it to one file." in at_approval
    assert PLAN["plan"] not in at_approval                               # the version approved, not the one sent back
    record = git(target, "show", f"{run.branch}:{name}")
    for part in ("Add a greeting", "The second version.", "keeps the layers apart", "| write_tests | 1 | passed |",
                 "accepted", "it matches the request", "Tests: greeting tests"):
        assert part in record, part
    assert git(target, "log", "--format=%s", "-1", run.branch) == "Accepted: The second version."
    assert git(target, "show", "--name-only", "--format=", run.branch).split() == [name]     # the record alone


@pytest.mark.fr("FR-080")
def test_a_run_that_stops_records_why_and_leaves_half_done_work_out(cycle):
    half = {"error": "You've hit your 5-hour limit", "files": {"CHANGELOG.md": "- half writ"}}
    run, _, _, target = cycle(script(document=half)[:5])
    assert run.outcome == "needs-me"
    record = git(target, "show", f"{run.branch}:{record_name(run)}")
    assert "needs-me" in record and "5-hour limit" in record
    assert "CHANGELOG.md" not in git(target, "show", "--name-only", "--format=", run.branch).split()


@pytest.mark.fr("FR-079")
def test_a_tidy_leaves_its_record_too(home, tmp_path, fake_notify):
    run, _, _, target = tidy(home, tmp_path, fake_notify, "tidy-tests", [{"envelope": PLAN}, TRIMMED, REVIEW])
    assert run.outcome == "accepted", run.reason
    assert PLAN["plan"] in git(target, "show", f"{run.branch}:{record_name(run)}")
