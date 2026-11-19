"""What a step entry is, and the three checks applied to every step (contracts/workflow.md)."""
import pytest

from factory import checks, own_files, tables, workflow, workspace
from factory.checks import CheckContext
from factory.config import TargetConfig
from factory.workflow import End, Rework, Step


def context(step, changed=(), envelope=None, before="", factory_paths=()):
    return CheckContext(run=None, step=step, checkout=None, target_config=TargetConfig(),
                        changed=set(changed), envelope=envelope, before=before,
                        factory_paths=list(factory_paths))


def agent_step(**kw):
    return Step(name="extra", kind="agent", persona="planner", on_pass="finish", **kw)


@pytest.mark.fr("FR-037")
def test_an_entry_that_says_nothing_gets_the_most_restrictive_values():
    step = agent_step()
    assert step.capabilities == "read" and step.may_change == "nothing"
    assert step.inputs == () and step.checks == () and step.envelope == {}
    assert step.on_fail == End("needs-me") and step.commit_after is False
    assert step.timeout is None and step.model is None
    code = Step(name="count", kind="code", on_pass="finish")
    assert code.persona is None and code.may_change == "nothing"


@pytest.mark.fr("FR-042")
def test_an_agent_step_must_name_a_persona_and_a_code_step_has_none():
    with pytest.raises(ValueError, match="persona"):
        Step(name="extra", kind="agent", on_pass="finish")
    with pytest.raises(ValueError, match="persona"):
        Step(name="count", kind="code", persona="planner", on_pass="finish")
    for bad in ({"kind": "robot"}, {"capabilities": "read+shell"}, {"may_change": "anything"}):
        with pytest.raises(ValueError):
            Step(**{"name": "x", "kind": "agent", "persona": "planner", "on_pass": "finish", **bad})
    assert Rework("build").step == "build" and End("rejected", "why").reason == "why"


@pytest.mark.fr("FR-037")
def test_checks_are_registered_and_found_by_name():
    @checks.register("always_fine")
    def always_fine(ctx):
        return checks.CheckResult(True)

    try:
        found = checks.get("always_fine")(context(agent_step()))
        assert found.passed and found.name == "always_fine"         # the registry stamps the name
        with pytest.raises(LookupError, match="no_such_check"):
            checks.get("no_such_check")
    finally:
        checks.REGISTRY.pop("always_fine")
    assert {"envelope_valid", "changes_allowed", "factory_untouched"} <= set(checks.REGISTRY)
    assert checks.ALWAYS == ("factory_untouched", "changes_allowed")


SHAPE = {"summary": "text", "files": "list", "verdict": ("accept", "reject")}


@pytest.mark.fr("FR-015")
@pytest.mark.parametrize("envelope, passes, note_has", [
    ({"summary": "ok", "files": [], "verdict": "accept"}, True, ""),
    ({"summary": "ok", "files": ["a"], "verdict": "reject", "extra": 1}, True, ""),
    (None, False, "JSON object"),
    ({"files": [], "verdict": "accept"}, False, "summary"),
    ({"summary": "ok", "files": "a.py", "verdict": "accept"}, False, "files"),
    ({"summary": 7, "files": [], "verdict": "accept"}, False, "summary"),
    ({"summary": "ok", "files": [], "verdict": "maybe"}, False, "verdict"),
])
def test_envelope_valid_checks_keys_and_types(envelope, passes, note_has):
    result = checks.get("envelope_valid")(context(agent_step(envelope=SHAPE), envelope=envelope))
    assert result.name == "envelope_valid" and result.passed is passes
    assert note_has in result.note


@pytest.mark.fr("FR-012")
@pytest.mark.fr("FR-022")
@pytest.mark.fr("FR-058")
@pytest.mark.parametrize("envelope, passes, said", [
    ({"verdict": "accept", "reasons": ["fine"], "ideals_broken": []}, True, []),
    ({"verdict": "accept", "reasons": ["fine"], "ideals_broken": ["layers"]}, False, ["accept", "layers"]),
    ({"verdict": "reject", "reasons": ["no heading", "wrong file"], "ideals_broken": ["layers are mixed"]}, False,
     ["no heading", "wrong file", "layers are mixed"]),
    ({"verdict": "replan", "requirement_changes": ["a new page"], "unbuilt": ["T009"]}, False, ["a new page", "T009"]),
    ({"verdict": "reject", "reasons": []}, False, ["no reason"]),
])
def test_a_judging_step_passes_only_on_an_accept_that_agrees_with_itself(envelope, passes, said):
    review = workflow.get("review", tables.STEPS)
    result = checks.get("verdict")(context(review, envelope=envelope))
    assert result.passed is passes and all(words in result.note for words in said), result.note
    assert checks.get("envelope_valid")(context(review, envelope={**envelope, "verdict": "maybe",
                                                                 "reasons": [], "ideals_broken": []})).passed is False


@pytest.mark.fr("FR-032")
@pytest.mark.parametrize("scope, changed, offending", [
    ("nothing", [], []),
    ("nothing", ["app.py"], ["app.py"]),
    ("tests", ["tests/test_app.py", "tests/unit/test_x.py"], []),
    ("tests", ["tests/test_app.py", "app.py", "testsuite.py"], ["app.py", "testsuite.py"]),
    ("not_tests", ["app.py", "src/deep/mod.py", "CHANGELOG.md"], []),
    ("not_tests", ["tests/test_app.py"], ["tests/test_app.py"]),            # this run's test
    ("not_tests", ["tests/test_old.py", "tests/conftest.py"], ["tests/conftest.py", "tests/test_old.py"]),
    ("not_tests", ["app.py", ".factory.toml", ".gitignore"], [".factory.toml", ".gitignore"]),
    ("docs", ["docs/guide.md", "CHANGELOG.md"], []),
    ("docs", ["docs/guide.md", "app.py", "CHANGELOG.md.bak"], ["CHANGELOG.md.bak", "app.py"]),
])
def test_changes_allowed_holds_each_step_to_its_scope(scope, changed, offending):
    result = checks.get("changes_allowed")(context(agent_step(may_change=scope), changed=changed))
    assert result.passed is (not offending)
    for name in offending:
        assert name in result.note
    assert workflow.SCOPES == ("nothing", "tests", "not_tests", "docs", "spec")


@pytest.mark.fr("FR-030")
def test_factory_untouched_compares_fingerprints(tmp_path):
    package, ideals = tmp_path / "factory", tmp_path / "ideals.md"
    package.mkdir()
    (package / "driver.py").write_text("code\n")
    ideals.write_text("layers\n")
    paths = [package, ideals]
    before = own_files.fingerprint(paths)
    check = checks.get("factory_untouched")
    assert check(context(agent_step(), before=before, factory_paths=paths)).passed
    ideals.write_text("tampered\n")
    result = check(context(agent_step(), before=before, factory_paths=paths))
    assert not result.passed and "changed" in result.note
