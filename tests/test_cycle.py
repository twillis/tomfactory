"""Whole runs through the fake agent, with a real target, real git and the real test command.

Each test scripts what the five personas "do" and asserts what the factory makes of it.
"""
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

    assert git(target, "rev-list", "--count", f"{run.base_commit}..{run.branch}") == "4"
    subjects = git(target, "log", "--format=%s", f"{run.base_commit}..{run.branch}").splitlines()
    assert subjects == [f"factory: document (run {run.id})", f"factory: architecture_review (run {run.id})",
                        f"factory: test (run {run.id})", f"factory: red (run {run.id})"]
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
        build={"envelope": {"summary": "bye", "files_changed": ["bye.py"]},
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


@pytest.mark.fr("FR-011")
@pytest.mark.fr("FR-017")
def test_a_build_that_fails_three_times_ends_needs_me(cycle):
    wrong = dict(BUILD, files={"hello.py": WRONG})
    run, _, store, target = cycle(script(build=[wrong, wrong, wrong]))
    assert run.outcome == "needs-me"
    assert "build" in run.reason and "3 times" in run.reason and "goodbye" in run.reason
    assert [s.attempt for s in store.query("steps", {"run_id": run.id}) if s.name == "build"] == [1, 2, 3]
    assert "test_greets" in record(store, run, "test").checks[-1]["note"]
    assert "review" not in names(store, run)
    assert cycle.notify[-1][0] == f"Run {run.id}: needs-me"
    assert git(target, "rev-list", "--count", f"{run.base_commit}..{run.branch}") == "1"    # the tests are kept


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


@pytest.mark.fr("FR-007")
def test_a_test_file_that_is_never_collected_does_not_count_as_failing_tests(cycle):
    uncollected = dict(WRITE_TESTS, files={"tests/helper.py": "assert False\n"})
    run, fake, store, _ = cycle(script(write_tests=[uncollected, WRITE_TESTS]))
    assert run.outcome == "accepted"
    assert "no tests" in record(store, run, "red", 0).checks[-1]["note"]
    assert "no tests" in fake.calls[2]["prompt"]


@pytest.mark.fr("FR-012")
@pytest.mark.fr("FR-015")
@pytest.mark.fr("FR-017")
def test_a_rejecting_review_ends_the_run_rejected(cycle):
    reject = {"envelope": {"verdict": "reject", "reasons": ["the greeting has no capital letter"], "ideals_broken": []}}
    run, _, store, target = cycle(script(review=reject))
    assert run.outcome == "rejected" and "no capital letter" in run.reason
    assert names(store, run)[-1] == "review" and "finish" not in names(store, run)
    assert git(target, "rev-list", "--count", f"{run.base_commit}..{run.branch}") == "4"   # the work is kept
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


@pytest.mark.fr("FR-032")
def test_a_test_writer_that_writes_outside_the_tests_is_undone(cycle):
    overreach = dict(WRITE_TESTS, files={"tests/test_hello.py": TEST, "hello.py": CODE})
    run, _, store, _ = cycle(script(write_tests=overreach)[:2])
    assert run.outcome == "needs-me" and "hello.py" in run.reason
    assert git(run.workspace, "status", "--porcelain") == ""


@pytest.mark.fr("FR-014")
@pytest.mark.fr("FR-017")
def test_a_step_that_times_out_ends_needs_me_naming_the_step_and_the_limit(cycle):
    run, _, store, _ = cycle(script(build={"timed_out": True})[:3])
    assert run.outcome == "needs-me" and "build" in run.reason and "900 seconds" in run.reason
    assert record(store, run, "build").failure == "timeout"
    assert cycle.notify[-1][0] == f"Run {run.id}: needs-me"


@pytest.mark.fr("FR-045")
@pytest.mark.fr("FR-011")
def test_a_test_writer_that_never_states_edge_cases_ends_needs_me(cycle):
    silent = dict(WRITE_TESTS, envelope=dict(WRITE_TESTS["envelope"], edge_cases=[]))
    run, fake, store, _ = cycle(script(write_tests=[silent, silent, silent])[:4])
    assert run.outcome == "needs-me" and "write_tests" in run.reason and "3 times" in run.reason
    assert [s.failure for s in store.query("steps", {"run_id": run.id}) if s.name == "write_tests"] == ["check"] * 3
    assert "edge_cases_stated" in fake.calls[2]["prompt"]


@pytest.mark.fr("FR-016")
def test_an_agent_error_ends_needs_me_and_keeps_the_work_so_far(cycle):
    run, _, store, target = cycle(script(build={"error": "usage limit reached"})[:3])
    assert run.outcome == "needs-me" and "usage limit reached" in run.reason
    assert git(target, "rev-list", "--count", f"{run.base_commit}..{run.branch}") == "1"
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


@pytest.mark.fr("FR-016")
@pytest.mark.fr("FR-011")
def test_an_edit_the_agent_program_refuses_inside_the_checkout_stops_the_run_at_once(cycle):
    """Found on the first real run: retrying cannot fix a refusal, so do not spend attempts on it."""
    def refused(call):
        return {"envelope": dict(WRITE_TESTS["envelope"], test_files=[]),
                "denials": [{"action": "write", "path": f"{call['cwd']}/tests/test_hello.py"}]}

    run, fake, store, _ = cycle(script(write_tests=refused)[:2])
    assert run.outcome == "needs-me"
    assert "refused" in run.reason and "tests/test_hello.py" in run.reason
    assert [s.name for s in store.query("steps", {"run_id": run.id})].count("write_tests") == 1, "it must not retry"
    assert record(store, run, "write_tests").failure == "error"


@pytest.mark.fr("FR-031")
def test_a_refused_edit_outside_the_checkout_is_the_guard_working_not_an_error(cycle):
    outside = dict(BUILD, denials=[{"action": "write", "path": "/etc/passwd"}])
    run, _, store, _ = cycle(script(build=outside))
    assert run.outcome == "accepted"
    denied = [e for e in records.events_after(store, run.id, limit=5000) if e.kind == "denied"]
    assert denied and denied[0].payload["path"] == "/etc/passwd"


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
@pytest.mark.parametrize("entry, failure", [
    ({"text": "I have thoughts but no JSON."}, "malformed"),
    ({"timed_out": True}, "timeout"),
    ({"error": "usage limit reached"}, "error"),
])
def test_an_architect_that_fails_is_recorded_and_the_run_carries_on(cycle, entry, failure):
    run, _, store, _ = cycle(script(architecture_review=entry))
    assert run.outcome == "accepted", run.reason
    review = record(store, run, "architecture_review")
    assert (review.passed, review.failure, review.attempt) == (False, failure, 1)       # recorded, not retried
    assert names(store, run) == ORDER


@pytest.mark.fr("FR-049")
@pytest.mark.fr("FR-050")
def test_what_a_failed_architect_wrote_does_not_slip_into_the_branch(cycle):
    """A failed advisory step may have left a half-written file. It must not be committed by the next step."""
    half = {"text": "I ran out of time.", "files": {"docs/backlog.md": "- a half-finished thou"}}
    run, _, store, target = cycle(script(architecture_review=half))
    assert run.outcome == "accepted"
    files = git(target, "ls-tree", "-r", "--name-only", run.branch).split()
    assert "docs/backlog.md" not in files and "CHANGELOG.md" in files
    assert git(target, "rev-list", "--count", f"{run.base_commit}..{run.branch}") == "3"    # tests, change, docs


@pytest.mark.fr("FR-050")
@pytest.mark.fr("FR-032")
def test_an_architect_that_edits_code_is_undone_and_the_run_stops(cycle):
    meddling = dict(ARCHITECT, files={"hello.py": "def greet(name=''):\n    return 'refactored'\n"})
    run, _, store, _ = cycle(script(architecture_review=meddling)[:4])
    assert run.outcome == "needs-me" and "architecture_review" in run.reason and "hello.py" in run.reason
    assert git(run.workspace, "show", "HEAD:hello.py") == CODE.strip()


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
    assert fake.calls[1]["persona"] == fake.calls[1]["persona"] and "testing specialist" in fake.calls[1]["persona"].lower()


@pytest.mark.fr("FR-066")
def test_tidying_the_tests_may_not_touch_the_code_and_tidying_the_code_may_not_touch_the_tests(home, tmp_path, fake_notify):
    sneaky = dict(TRIMMED, files={**TRIMMED["files"], "hello.py": WRONG})
    run, _, _, _ = tidy(home, tmp_path, fake_notify, "tidy-tests", [{"envelope": PLAN}, sneaky])
    assert run.outcome == "needs-me" and "hello.py" in run.reason
    weakened = dict(TIDIED, files={**TIDIED["files"], "tests/test_hello.py": "def test_nothing():\n    assert True\n"})
    run, _, _, _ = tidy(home, tmp_path, fake_notify, "tidy-code", [{"envelope": PLAN}, weakened], name="second")
    assert run.outcome == "needs-me" and "tests/test_hello.py" in run.reason


@pytest.mark.fr("FR-066")
def test_tidying_the_code_must_leave_every_test_passing(home, tmp_path, fake_notify):
    broke = dict(TIDIED, files={"hello.py": WRONG})
    run, fake, store, target = tidy(home, tmp_path, fake_notify, "tidy-code",
                                    [{"envelope": PLAN}, broke, TIDIED, REVIEW])
    assert run.outcome == "accepted", run.reason
    assert names(store, run) == ["plan", "baseline", "tidy_code", "test", "tidy_code", "test", "review", "finish"]
    assert "assert 'goodbye' == 'hello'" in fake.calls[2]["prompt"]             # told what it broke
    assert "GREETING" in git(target, "show", f"{run.branch}:hello.py")


@pytest.mark.fr("FR-066")
def test_a_tidy_run_is_refused_if_the_tests_do_not_pass_to_begin_with(home, tmp_path, fake_notify, monkeypatch):
    monkeypatch.setitem(EXISTING, "hello.py", WRONG)
    run, fake, _, _ = tidy(home, tmp_path, fake_notify, "tidy-tests", [{"envelope": PLAN}])
    assert run.outcome == "needs-me" and "already failing" in run.reason and len(fake.calls) == 1


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
def test_resuming_is_refused_unless_the_run_stopped_as_needs_me_and_can_carry_on(cycle, home, monkeypatch, capsys):
    accepted, _, _, target = cycle(script())
    with pytest.raises(operations.Refused, match="only a run that ended as needs-me"):
        operations.resume(accepted.id)

    stopped, _, _, _ = cycle(script(build={"error": "usage limit"})[:3], target=target)
    drive_with(FakeAgent([{"envelope": PLAN}]))
    other = operations.request("Something else", target)
    with pytest.raises(operations.Refused, match=f"run {other.id} has not ended"):
        operations.resume(stopped.id)
    operations.abandon(other.id)

    from factory import cli
    monkeypatch.setattr(operations, "launch", in_process(FakeAgent(script()[2:])))
    assert cli.main(["resume", str(stopped.id)]) == 0 and "accepted" in capsys.readouterr().out

    gone, _, _, _ = cycle(script(build={"error": "usage limit"})[:3], target=target)
    Workspace(gone.workspace, gone.target, gone.branch, gone.base_commit).remove()
    with pytest.raises(operations.Refused, match="checkout no longer exists"):
        operations.resume(gone.id)


@pytest.mark.fr("FR-066")
@pytest.mark.parametrize("kind, held_still", [("tidy-code", "The tests are held still"),
                                              ("tidy-tests", "The code is held still")])
def test_the_planner_and_reviewer_are_told_what_a_tidy_holds_still(home, tmp_path, fake_notify, kind, held_still):
    """Found on run 15: told nothing, the planner planned new tests in a tidy of the code."""
    step = TIDIED if kind == "tidy-code" else TRIMMED
    run, fake, _, _ = tidy(home, tmp_path, fake_notify, kind, [{"envelope": PLAN}, step, REVIEW])
    assert run.outcome == "accepted", run.reason
    planner, reviewer = fake.calls[0]["prompt"], fake.calls[2]["prompt"]
    assert held_still in planner and held_still in reviewer


@pytest.mark.fr("FR-066")
def test_a_change_tells_the_planner_it_is_a_change(cycle):
    run, fake, _, _ = cycle(script())
    assert "This run is a change" in fake.calls[0]["prompt"] and "held still" not in fake.calls[0]["prompt"]
