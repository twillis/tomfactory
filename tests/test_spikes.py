"""Spikes: a run whose product is an answer, not a change (FR-113 to FR-118, from specification 004).

A spike plans, writes a probe, has the factory run it, writes its findings and a one-paragraph retro, and ends
answered or inconclusive. Nothing it builds is merged.
"""
import re
import sqlite3

import pytest

from factory import config, operations, records, tables, workflow
from factory import store as store_module
from factory.operations import Refused
from factory.store import open_store
from factory.workflow import END_AS_FOUND, End, Run, StepResult, CheckResult
from tests.conftest import commit_files, git, to_the_end
from tests.fake_agent import FakeAgent

PROBING = config.DEFAULT_FACTORY_TOML.replace('probe_command = ""', 'probe_command = "python {path}"')
APP = "ROOTS = ['tenant', 'ref']\n"
PROBE_CODE = "from app import ROOTS\n\nprint('roots:', len(ROOTS))\nprint('person' in ROOTS)\n"
PRINTED = "roots: 2\nFalse"

PLAN = {"envelope": {"plan": "Count the roots, and look for a person among them.",
                     "question": "Is there a person root yet?", "guess": "no",
                     "yes": "it prints True", "no": "it prints False", "cannot_tell": "it fails to import"}}


def probe(code=PROBE_CODE, name="probe_person.py", cost=0.0):
    """The probe step: a probe file, and a change to the code beside it, which a spike may make."""
    return {"envelope": {"summary": "a probe that counts the roots", "probe_file": name,
                         "files_changed": [name, "app.py"]},
            "files": {name: code, "app.py": APP + "PERSON = None\n"}, "cost": cost}


NOTE = (f"# Is there a person root yet?\n\nThe probe counted the roots:\n\n```python\n{PROBE_CODE}```\n\n"
        f"It printed:\n\n```text\n{PRINTED}\n```\n\nNo person root yet.\n")


def note_path(call):
    return re.search(r"docs/spikes/[\w.-]+\.md", call["prompt"]).group(0)


def findings(note=NOTE, outcome="answered", extra=None):
    """The findings step: the note, written where the prompt says, and the outcome."""
    def write(call):
        return {"envelope": {"summary": "there is no person root yet", "outcome": outcome,
                             "reason": "the probe printed False"},
                "files": {note_path(call): note, **(extra or {})}}
    return write


def retro(call):
    name = re.search(r"docs/retros/[\w.-]+\.md", call["prompt"]).group(0)
    return {"envelope": {"summary": "answered for nothing"},
            "files": {name: "Answered, at no cost: the probe printed what the plan said it would.\n"}}


def spike(home, tmp_path, entries, toml=PROBING, name="spike-target"):
    target = commit_files(operations.init_target(tmp_path / name), {".factory.toml": toml, "app.py": APP})
    fake = FakeAgent(entries)
    run, waits = to_the_end(target, fake, "Is there a person root yet?", run_kind="spike")
    return run, fake, open_store(home), target, waits


def names(store, run):
    return [s.name for s in store.query("steps", {"run_id": run.id})]


def subjects(target, run):
    return git(target, "log", "--reverse", "--format=%s", f"{run.base_commit}..{run.branch}").splitlines()


# ---- the table (FR-113) ----

@pytest.mark.fr("FR-113")
def test_a_spike_goes_plan_probe_run_findings_retro_end_and_never_waits():
    steps = tables.SPIKE_STEPS
    assert [s.name for s in steps] == ["spike_plan", "probe", "run_probe", "write_findings", "spike_retro", "finish"]
    assert all(s.on_pass not in (workflow.WAIT, workflow.END_ACCEPTED) for s in steps)
    assert workflow.get("finish", steps).on_pass == END_AS_FOUND
    for spec_kit in (False, True):
        for cycle in tables.CYCLES:
            assert tables.table_for(spec_kit, "spike", cycle) is steps
    assert "spike" in operations.run_kinds()


@pytest.mark.fr("FR-113")
def test_none_of_the_change_cycles_gates_apply_to_a_spike():
    steps = tables.SPIKE_STEPS
    gates = {"tests_fail_first", "tests_added", "edge_cases_stated", "tests_pass", "baseline"}
    assert not gates & {name for s in steps for name in s.checks}
    assert not any(s.smells for s in steps)                                   # no budget, no line length
    assert not {"architect", "documenter", "test_writer", "code_writer"} & {s.persona for s in steps}
    assert workflow.get("probe", steps).may_change == "checkout"
    assert workflow.get("write_findings", steps).may_change == "docs"


@pytest.mark.fr("FR-113")
@pytest.mark.parametrize("toml, named", [
    (config.DEFAULT_FACTORY_TOML, "probe_command"),
    (config.DEFAULT_FACTORY_TOML.replace('probe_command = ""', 'probe_command = "python probe.py"'), "{path}"),
    (PROBING.replace('docs_paths = ["docs/", "CHANGELOG.md"]', 'docs_paths = ["notes/"]'), "docs/spikes/"),
])
def test_a_spike_the_codebase_cannot_run_is_refused_before_anything_is_paid_for(home, tmp_path, toml, named):
    target = commit_files(operations.init_target(tmp_path / "no-probe"), {".factory.toml": toml, "app.py": APP})
    with pytest.raises(Refused, match=re.escape(named)):
        operations.request("Is there a person root yet?", target, run_kind="spike")
    assert open_store(home).query("runs") == []


# ---- a whole spike (FR-113 to FR-116, FR-118) ----

@pytest.mark.fr("FR-113")
@pytest.mark.fr("FR-114")
@pytest.mark.fr("FR-115")
@pytest.mark.fr("FR-116")
@pytest.mark.fr("FR-118")
def test_a_spike_answers_its_question_and_files_the_findings_on_its_own_branch(home, tmp_path, fake_notify):
    run, fake, store, target, waits = spike(home, tmp_path, [PLAN, probe(), findings(), retro])

    assert (run.outcome, run.reason) == ("answered", "the probe printed False")
    assert names(store, run) == ["spike_plan", "probe", "run_probe", "write_findings", "spike_retro", "finish"]
    assert waits == 0                                               # the plan does not wait for approval
    assert "Prospector" in fake.calls[0]["persona"] and fake.calls[0]["persona"] == fake.calls[2]["persona"]
    assert "python {path}" in fake.calls[1]["prompt"]               # the probe is told how it will be run
    told = fake.calls[2]["prompt"]                                  # the findings are given what the factory ran
    assert PRINTED in told and "exited 0" in told and "docs/spikes/" in told
    ran = [s for s in store.query("steps", {"run_id": run.id}) if s.name == "run_probe"][0]
    assert ran.produced["contained"] == {"network": False}

    name = run.branch.removeprefix("factory/")
    on_branch = git(target, "ls-tree", "-r", "--name-only", run.branch).split()
    assert {"probe_person.py", f"docs/spikes/{name}.md", f"docs/retros/{name}.md"} <= set(on_branch)
    assert "PERSON = None" in git(target, "show", f"{run.branch}:app.py")      # the probe may change the code
    assert git(target, "show", "main:app.py") == APP.strip()                    # and none of it is merged
    assert subjects(target, run) == ["Probe: a probe that counts the roots", "Findings: there is no person root yet",
                                     "Retro: answered for nothing", "Answered: Is there a person root yet?"]
    record = git(target, "show", f"{run.branch}:docs/runs/{name}.md")
    last = git(target, "log", "-1", "--format=%B", run.branch)
    for said in (record, last):
        assert "Nothing this spike built is in the codebase" in said
        assert f"docs/spikes/{name}.md" in said and run.branch in said and "review" in said
    assert "Is there a person root yet?" in record and "it prints False" in record     # the spike's plan, kept


# ---- the probe, run by the factory (FR-114) ----

@pytest.mark.fr("FR-114")
def test_a_probe_that_exits_non_zero_has_still_measured_something(home, tmp_path, fake_notify):
    refused = "print('refused: no person root')\nraise SystemExit(1)\n"
    note = f"# Refused\n\n```python\n{refused}```\n\n```text\nrefused: no person root\n```\n"
    run, fake, store, _, _ = spike(home, tmp_path, [PLAN, probe(refused), findings(note), retro])
    assert run.outcome == "answered", run.reason
    assert "exited 1" in fake.calls[2]["prompt"] and "refused: no person root" in fake.calls[2]["prompt"]


CANNOT_RUN = [
    ("its file is not there", lambda: probe(name="nowhere.py") | {"files": {}}, "no such file"),
    ("nothing ran", lambda: probe("raise SystemExit(5)\n"), "nothing ran"),
    ("it did not finish", lambda: probe("import time\ntime.sleep(30)\n"), "did not finish within 1"),
]


@pytest.mark.fr("FR-114")
@pytest.mark.parametrize("why, broken, said", CANNOT_RUN, ids=[case[0] for case in CANNOT_RUN])
def test_a_probe_that_cannot_run_is_mended_once_then_the_spike_is_inconclusive(home, tmp_path, fake_notify,
                                                                               why, broken, said):
    toml = PROBING + "\n[steps.run_probe]\ntimeout = 1\n"
    run, fake, store, _, _ = spike(home, tmp_path, [PLAN, broken(), probe(), findings(), retro], toml, "mended")
    assert run.outcome == "answered", run.reason
    assert names(store, run)[:5] == ["spike_plan", "probe", "run_probe", "probe", "run_probe"]
    assert said in fake.calls[2]["prompt"]                          # the mend is told what happened

    run, _, store, _, _ = spike(home, tmp_path, [PLAN, broken(), broken()], toml, "twice")
    assert run.outcome == "inconclusive" and "could not be run" in run.reason and said in run.reason
    assert names(store, run) == ["spike_plan", "probe", "run_probe", "probe", "run_probe"]


# ---- the findings note, checked by the factory (FR-115) ----

WRONG_NOTES = [
    ("code that is not on the branch", NOTE.replace("print('person' in ROOTS)", "print('person' in ROOTS, 1)"),
     None, "print('person' in ROOTS, 1)"),
    ("output the probe did not print", NOTE.replace("roots: 2", "roots: 3"), None, "roots: 3"),
    ("code only the findings step wrote", NOTE + "\n```python\nPERSON_ROOT = True\n```\n",
     {"docs/person.py": "PERSON_ROOT = True\n"}, "PERSON_ROOT = True"),
]


@pytest.mark.fr("FR-115")
@pytest.mark.parametrize("why, wrong, extra, said", WRONG_NOTES, ids=[case[0] for case in WRONG_NOTES])
def test_a_note_that_quotes_what_is_not_there_is_sent_back_once(home, tmp_path, fake_notify, why, wrong, extra, said):
    run, fake, store, _, _ = spike(home, tmp_path, [PLAN, probe(), findings(wrong, extra=extra), findings(), retro],
                                   name="once")
    assert run.outcome == "answered", run.reason
    assert names(store, run).count("write_findings") == 2
    assert said in fake.calls[3]["prompt"]                          # told which block was wrong

    run, _, store, _, _ = spike(home, tmp_path, [PLAN, probe(), findings(wrong, extra=extra),
                                                 findings(wrong, extra=extra)], name="twice")
    assert run.outcome == "inconclusive" and said in run.reason
    assert "spike_retro" not in names(store, run)


@pytest.mark.fr("FR-115")
def test_findings_that_are_not_where_the_note_belongs_are_sent_back(home, tmp_path, fake_notify):
    elsewhere = {"envelope": {"summary": "s", "outcome": "answered", "reason": "r"},
                 "files": {"docs/findings.md": NOTE}}
    run, fake, store, _, _ = spike(home, tmp_path, [PLAN, probe(), elsewhere, findings(), retro])
    assert run.outcome == "answered", run.reason
    assert "there is no findings note at docs/spikes/" in fake.calls[3]["prompt"]


# ---- how a spike ends (FR-116) ----

@pytest.mark.fr("FR-116")
@pytest.mark.parametrize("found, ends", [
    ({"outcome": "answered", "reason": "it printed False"}, End("answered", "it printed False")),
    ({"outcome": "inconclusive", "reason": "it printed nothing"}, End("inconclusive", "it printed nothing")),
    ({}, "needs-me"),
])
def test_a_spike_ends_as_its_findings_say(found, ends):
    finish = workflow.get("finish", tables.SPIKE_STEPS)
    then = workflow.next_step(finish, StepResult(True), {}, 3, found)
    assert then == ends if isinstance(ends, End) else then.outcome == ends


@pytest.mark.fr("FR-116")
def test_only_a_spike_ends_answered_or_inconclusive_and_a_spike_is_never_accepted_or_rejected():
    def ends(table):
        found = {s.on_pass for s in table}
        for s in table:
            for route in [s.on_fail, *s.routes.values()]:
                found.add(route.outcome if isinstance(route, End) else getattr(route, "then", None))
        return {getattr(end, "outcome", end) for end in found}
    for table in tables.TABLES:
        spike_table = table is tables.SPIKE_STEPS
        assert workflow.ends_as_found(table) == spike_table
        assert not (set(workflow.FOUND) & ends(table)) or spike_table
        assert not ({workflow.END_ACCEPTED, "rejected"} & ends(table)) or not spike_table
    abandoned = workflow.after_wait("abandon", tables.SPIKE_STEPS[0], tables.SPIKE_STEPS)
    assert abandoned == End("inconclusive", "abandoned by operator")
    assert workflow.after_wait("abandon", tables.STEPS[0], tables.STEPS).outcome == "rejected"


@pytest.mark.fr("FR-116")
def test_a_spike_abandoned_at_a_question_is_inconclusive(home, tmp_path, fake_notify):
    asks = {"envelope": {"question": "Which of the two roots should a person hang from?"}}
    unsure = {"envelope": {"answer": "The documents do not say.", "confident": "no"}}
    run, _, _, _, _ = spike(home, tmp_path, [asks, unsure])
    assert run.state == "awaiting_approval"
    ended = operations.abandon(run.id)
    assert (ended.outcome, ended.reason) == ("inconclusive", "abandoned by operator")


@pytest.mark.fr("FR-116")
def test_the_store_accepts_exactly_the_outcomes_the_rules_name_and_an_older_home_gains_them(home):
    db = sqlite3.connect(home / "factory.db")
    db.executescript(store_module.BASE)
    db.execute("INSERT INTO runs (request, target, base_commit, state, created_at)"
               " VALUES ('r', '/t', 'c', 'planning', 'now')")
    db.execute("PRAGMA user_version = 4")
    db.commit()
    db.close()
    gw = open_store(home)
    made = gw.db.execute("SELECT sql FROM sqlite_master WHERE name = 'runs'").fetchone()[0]
    listed = re.search(r"outcome\s+TEXT\s+CHECK \(outcome IN \(([^)]*)\)\)", made).group(1)
    assert tuple(name.strip(" '") for name in listed.split(",")) == workflow.OUTCOMES
    assert set(workflow.FOUND) <= set(workflow.OUTCOMES)
    ended = records.end(gw, 1, "answered", "it printed False")
    assert (ended.outcome, ended.request) == ("answered", "r")                 # the run it had is kept
    assert gw.db.execute("SELECT name FROM sqlite_master WHERE name = 'one_open_run'").fetchone()
    with pytest.raises(sqlite3.IntegrityError):
        gw.update("runs", {"id": 1}, {"outcome": "finished"})


# ---- the budget (FR-117) ----

@pytest.mark.fr("FR-117")
@pytest.mark.parametrize("table, step, spent, cap, over", [
    (tables.SPIKE_STEPS, "write_findings", 5.0, 5.0, True),                   # at the cap
    (tables.SPIKE_STEPS, "write_findings", 4.99, 5.0, False),
    (tables.SPIKE_STEPS, "run_probe", 9.0, 5.0, False),                 # only before an agent step
    (tables.SPIKE_STEPS, "write_findings", 9.0, 0.0, False),                  # 0: no cap
    (tables.STEPS, "build", 90.0, 5.0, False),                          # only a spike is boxed
])
def test_before_each_agent_step_a_spike_at_its_budget_ends_inconclusive(table, step, spent, cap, over):
    then = workflow.over_budget(table, workflow.get(step, table), spent, cap, ["spike_plan", "probe", "run_probe"])
    assert (then is not None) == over
    if over:
        assert then.outcome == "inconclusive"
        assert "$5.00" in then.reason and "$5.00 spent" in then.reason and "spike_plan, probe, run_probe" in then.reason


@pytest.mark.fr("FR-117")
def test_a_spike_stops_at_its_budget_saying_what_it_had(home, tmp_path, fake_notify):
    assert config.TargetConfig().spike_budget_dollars == 5.0
    toml = PROBING.replace("spike_budget_dollars = 5.0", "spike_budget_dollars = 1.0")
    run, fake, store, _, _ = spike(home, tmp_path, [PLAN | {"cost": 0.6}, probe(cost=0.5)], toml)
    assert run.outcome == "inconclusive"
    assert names(store, run) == ["spike_plan", "probe", "run_probe"]
    assert "$1.00" in run.reason and "$1.10 spent" in run.reason and "spike_plan, probe, run_probe" in run.reason


# ---- who does it, and the retro (FR-118) ----

@pytest.mark.fr("FR-118")
def test_the_spike_has_its_own_persona_and_a_one_paragraph_retro():
    from tests.test_personas import sections
    own = sections("spike")
    assert "ugliest" in own["expertise"].lower() and "surpris" in own["priorities"].lower()
    steps = tables.SPIKE_STEPS
    assert {s.persona for s in steps if s.name in ("spike_plan", "probe", "write_findings")} == {"spike"}
    retro_step = workflow.get("spike_retro", steps)
    assert (retro_step.persona, retro_step.model, retro_step.advisory) == ("facilitator", "light", True)
    assert "one paragraph" in (config.PROMPTS_DIR / "spike_retro.md").read_text()
    assert "`spike_plan`" in (config.PACKAGE_DIR.parent / "docs" / "roster.md").read_text()


@pytest.mark.fr("FR-118")
def test_a_failed_retro_does_not_stop_a_spike(home, tmp_path, fake_notify):
    run, _, store, _, _ = spike(home, tmp_path, [PLAN, probe(), findings(), {"error": "usage limit"}])
    assert run.outcome == "answered", run.reason
    assert names(store, run)[-2:] == ["spike_retro", "finish"]


# ---- the route a capped rework takes when it has had its tries (FR-114) ----

@pytest.mark.fr("FR-114")
def test_a_capped_rework_may_end_the_run_when_it_has_had_its_tries():
    run_probe = workflow.get("run_probe", tables.SPIKE_STEPS)
    cannot = StepResult(False, "check", CheckResult(False, "no such file: x.py", name="probe_ran"))
    assert workflow.next_step(run_probe, cannot, {"probe": 1}, 3) == Run("probe")
    ended = workflow.next_step(run_probe, cannot, {"probe": 2}, 3)
    assert ended.outcome == "inconclusive" and "no such file: x.py" in ended.reason


@pytest.mark.fr("FR-114")
@pytest.mark.parametrize("code, cannot", [(2, True), (4, False)], ids=["a listed code", "an unlisted code"])
def test_a_codebase_names_the_exit_codes_that_mean_its_probe_never_ran(home, tmp_path, fake_notify, code, cannot):
    toml = PROBING.replace("probe_cannot_run_exit_codes = []", "probe_cannot_run_exit_codes = [2, 5]")
    exits = probe(f"print('collection failed')\nraise SystemExit({code})\n")
    note = f"# Exit\n\n```python\nraise SystemExit({code})\n```\n"
    run, fake, store, _, _ = spike(home, tmp_path, [PLAN, exits] + ([probe()] if cannot else []) + [
        findings(NOTE if cannot else note), retro], toml)
    assert run.outcome == "answered", run.reason
    assert (names(store, run).count("probe") == 2) == cannot
    if cannot:
        assert f"exited {code}" in fake.calls[2]["prompt"] and "nothing ran" in fake.calls[2]["prompt"]
    assert config.TargetConfig().probe_cannot_run_exit_codes == ()       # when absent: no_tests_exit_code alone
