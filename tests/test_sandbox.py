"""Target code runs contained (feature 002). The stand-in test in fixtures/probe measures it."""
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

import pytest

from factory import checks, config, operations, proc, sandbox
from factory.checks import CheckContext
from factory.workflow import Step
from factory.workspace import Workspace
from tests.conftest import git
from tests.test_cycle import cycle, record, script  # noqa: F401  (cycle is a fixture)

PROBE = pathlib.Path(__file__).parent / "fixtures" / "probe" / "test_probe.py"
MARKER = "tomfactory-escape-probe"
CAPABILITIES = ["read the operator's private keys", "read the factory's records", "read the factory's code",
                "reach the internet", "reach the docker socket", "see the operator's environment",
                "see a network beyond loopback"]
# "write outside its checkout" is not in the list: inside, /tmp is private, so a write there succeeds and
# is thrown away. Whether a write lasts can only be seen from outside (FR-070).


def holes(report):
    """The capabilities the probe had, among those that must be closed when contained."""
    return [name for name in CAPABILITIES if report[name]]


def leftovers():
    """Processes started by a probe that are still running, by process id."""
    found = subprocess.run(["pgrep", "-f", MARKER], capture_output=True, text=True).stdout.split()
    return [int(pid) for pid in found]


def kill_leftovers():
    for pid in leftovers():
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass


@pytest.fixture
def operator_home(tmp_path):
    """A stand-in for the operator's home, with private keys and the factory's records in it."""
    home = tmp_path / "operator-home"
    (home / ".ssh").mkdir(parents=True)
    (home / ".ssh" / "id_ed25519").write_text("not a real key")
    (home / ".tomfactory").mkdir()
    (home / ".tomfactory" / "factory.db").write_text("not a real database")
    return home


@pytest.fixture
def probe(tmp_path, operator_home, monkeypatch):
    """Run test files in a fresh target through the factory's own test path; return what happened."""
    monkeypatch.setenv("TOMFACTORY_CANARY", "a secret the operator keeps in the environment")
    made = []

    def run(files=None, network=False, timeout=60, on_child=None):
        made.append(1)
        target = operations.init_target(tmp_path / f"target-{len(made)}")
        probe_text = PROBE.read_text().replace("@OPERATOR_HOME@", str(operator_home)).replace(
            "@FACTORY@", str(config.PACKAGE_DIR.parent))
        for name, text in {"tests/test_probe.py": probe_text, **(files or {})}.items():
            (target / name).parent.mkdir(parents=True, exist_ok=True)
            (target / name).write_text(text)
        if network:
            (target / ".factory.toml").write_text(config.DEFAULT_FACTORY_TOML.replace("test_network = false",
                                                                                  "test_network = true"))
        git(target, "add", "-A")
        git(target, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "probe")
        checkout = Workspace.create(target, tmp_path / f"ws-{len(made)}", f"factory/{len(made)}-probe")
        groups = []
        context = CheckContext(run=None, step=Step("test", "code", on_pass="x"), checkout=checkout,
                               target_config=config.read_target_config(target, checkout.base_commit), changed=set(),
                               envelope=None, before="", stderr_file=open(tmp_path / f"err-{len(made)}", "w"),
                               on_child=on_child or groups.append, timeout=timeout)
        code, output, contained = checks.run_tests(context)
        report_file = checkout.path / "probe-report.json"
        report = json.loads(report_file.read_text()) if report_file.exists() else None
        return {"code": code, "output": output, "contained": contained, "report": report, "checkout": checkout}

    kill_leftovers()
    yield run
    kill_leftovers()                               # leave nothing behind, whatever a test found


@pytest.mark.fr("FR-077")
def test_the_probe_is_honest_uncontained(operator_home, tmp_path, monkeypatch):
    """Uncontained, the stand-in test does find the holes, so its "no" means something contained."""
    monkeypatch.setenv("TOMFACTORY_CANARY", "x")
    (tmp_path / "plain").mkdir()
    text = PROBE.read_text().replace("@OPERATOR_HOME@", str(operator_home)).replace("@FACTORY@", str(config.PACKAGE_DIR.parent))
    (tmp_path / "plain" / "test_probe.py").write_text(text)
    with open(os.devnull, "w") as err:
        proc.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_probe.py"],
                 tmp_path / "plain", 60, lambda line: None, err)
    found = holes(json.loads((tmp_path / "plain" / "probe-report.json").read_text()))
    for name in ("read the operator's private keys", "read the factory's records", "read the factory's code",
                 "see the operator's environment", "see a network beyond loopback"):
        assert name in found
    assert (operator_home / "written-by-an-agent's-test").exists()
    assert leftovers(), "uncontained, the probe's detached process does outlive it"
    kill_leftovers()
    pathlib.Path("/tmp/tomfactory-probe-marker").unlink(missing_ok=True)


@pytest.fixture(scope="module")
def contained(tmp_path_factory):
    """The probe, run once contained through the factory's own test path, for the table below."""
    tmp_path = tmp_path_factory.mktemp("contained")
    with pytest.MonkeyPatch.context() as patch:
        home = tmp_path / "operator-home"
        (home / ".ssh").mkdir(parents=True)
        (home / ".ssh" / "id_ed25519").write_text("not a real key")
        (home / ".tomfactory").mkdir()
        (home / ".tomfactory" / "factory.db").write_text("not a real database")
        run = probe.__wrapped__(tmp_path, home, patch)
        ran = next(run)()
        next(run, None)
    return ran


@pytest.mark.fr("FR-068")
@pytest.mark.fr("FR-069")
@pytest.mark.fr("FR-071")
@pytest.mark.fr("FR-073")
@pytest.mark.fr("FR-077")
@pytest.mark.parametrize("capability", CAPABILITIES)
def test_contained_target_code_cannot(contained, capability):
    assert contained["code"] == 0, contained["output"]
    assert contained["report"][capability] is False


@pytest.mark.fr("FR-070")
def test_a_write_outside_the_checkout_does_not_last(probe, operator_home):
    pathlib.Path("/tmp/tomfactory-probe-marker").unlink(missing_ok=True)
    ran = probe()
    assert ran["report"]["write outside its checkout"] is True                  # it tried, and it seemed to work
    assert not pathlib.Path("/tmp/tomfactory-probe-marker").exists()           # but nothing lasted outside
    assert not (operator_home / "written-by-an-agent's-test").exists()


HANG = ("import subprocess, sys, time\n\ndef test_hang():\n"
        "    subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', '%s'], start_new_session=True)\n"
        "    time.sleep(%%d)\n" % MARKER)


@pytest.mark.fr("FR-072")
@pytest.mark.parametrize("ending", ["ends", "times out", "is stopped"])
def test_nothing_the_code_starts_outlives_the_step(probe, ending):
    groups, seen = [], []
    files = {"tests/test_hang.py": HANG % (2 if ending == "ends" else 60)}
    timeout = 5 if ending == "times out" else 60
    worker = threading.Thread(target=lambda: probe(files, timeout=timeout, on_child=groups.append))
    worker.start()
    deadline = time.monotonic() + 40
    while worker.is_alive() and time.monotonic() < deadline:
        if leftovers():
            seen.append(True)
            if ending == "is stopped" and any(groups):
                proc.stop_group(next(group for group in groups if group))
        time.sleep(0.1)
    worker.join(timeout=10)
    assert seen, "the escaping process was never seen running, so this would prove nothing"
    time.sleep(0.5)
    assert leftovers() == []


@pytest.mark.fr("FR-078")
def test_a_suite_with_a_local_server_and_temporary_files_passes_contained(probe):
    suite = ("import http.server, tempfile, threading, urllib.request\n\n"
             "def test_serve_and_fetch():\n"
             "    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), http.server.SimpleHTTPRequestHandler)\n"
             "    threading.Thread(target=server.serve_forever, daemon=True).start()\n"
             "    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_address[1]}/') as reply:\n"
             "        assert reply.status == 200\n"
             "    server.shutdown()\n\n"
             "def test_temporary_files():\n"
             "    with tempfile.NamedTemporaryFile('w+') as f:\n"
             "        f.write('x'); f.seek(0); assert f.read() == 'x'\n")
    ran = probe({"tests/test_suite.py": suite})
    assert ran["code"] == 0 and "3 passed" in ran["output"], ran["output"]


@pytest.mark.fr("FR-068")
def test_containing_a_command_costs_well_under_a_second(tmp_path):
    started = time.monotonic()
    done = subprocess.run(sandbox.command(["true"], tmp_path), capture_output=True)
    assert done.returncode == 0 and time.monotonic() - started < 1.0


# ---- refusing rather than running uncontained (FR-074) ----

@pytest.fixture
def no_containment(tmp_path, monkeypatch):
    """A machine where bubblewrap is present but refuses to work."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "bwrap").write_text("#!/bin/sh\necho 'bwrap: setting up uid map: Permission denied' >&2\nexit 1\n")
    (bin_dir / "bwrap").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    sandbox.available.cache_clear()
    yield
    sandbox.available.cache_clear()


@pytest.mark.fr("FR-074")
def test_without_containment_the_tests_are_not_run_and_the_run_says_why(cycle, no_containment):
    marker = "tests/ran-uncontained"
    canary = f"import pathlib\n\ndef test_canary():\n    pathlib.Path('{marker}').write_text('x')\n"
    run, _, store, _ = cycle(script()[:1], files={"tests/test_canary.py": canary})
    assert run.outcome == "needs-me" and run.current_step == "baseline"
    assert "cannot contain" in run.reason and "Permission denied" in run.reason
    assert record(store, run, "baseline").failure == "error"
    assert not (pathlib.Path(run.workspace) / marker).exists()


@pytest.mark.fr("FR-074")
def test_the_machine_check_reports_containment(no_containment, home, monkeypatch):
    monkeypatch.setenv("TOMFACTORY_AGENT", "tests.test_cli:healthy_agent")
    line = next(item for item in operations.doctor() if item.name == "containment")
    assert line.ok is False and "Permission denied" in line.detail
    sandbox.available.cache_clear()
    monkeypatch.undo()
    monkeypatch.setenv("TOMFACTORY_AGENT", "tests.test_cli:healthy_agent")
    assert next(item for item in operations.doctor() if item.name == "containment").ok is True


# ---- the network, per codebase (FR-075, FR-076) ----

@pytest.mark.fr("FR-075")
def test_a_codebase_that_allows_the_network_gets_it_and_nothing_else(probe):
    ran = probe(network=True)
    assert ran["report"]["see a network beyond loopback"] is True and ran["contained"] == {"network": True}
    assert holes(ran["report"]) in ([], ["reach the internet"], ["see a network beyond loopback"],
                                    ["reach the internet", "see a network beyond loopback"])
    assert [name for name in holes(ran["report"]) if name not in ("reach the internet", "see a network beyond loopback")] == []


@pytest.mark.fr("FR-075")
def test_allowing_the_network_in_the_checkout_alone_changes_nothing(probe, tmp_path):
    ran = probe()
    (ran["checkout"].path / ".factory.toml").write_text(config.DEFAULT_FACTORY_TOML.replace(
        "test_network = false", "test_network = true"))                       # as an agent might
    settings = config.read_target_config(ran["checkout"].target, ran["checkout"].base_commit)
    assert settings.test_network is False


@pytest.mark.fr("FR-076")
def test_each_step_that_ran_the_targets_code_records_that_it_was_contained(cycle):
    run, _, store, _ = cycle(script())
    for name in ("baseline", "red", "test"):
        assert record(store, run, name).produced["contained"] == {"network": False}, name
    assert "contained" not in (record(store, run, "build").produced or {})


# ---- the protection stays in place (FR-077) ----

@pytest.mark.fr("FR-077")
def test_a_weakened_containment_is_caught_and_the_hole_named(probe, monkeypatch):
    monkeypatch.setattr(sandbox, "HIDDEN", ("/home", "/run"))     # a change that forgets to hide /tmp
    ran = probe()
    assert "read the operator's private keys" in holes(ran["report"])    # the stand-in home lives under /tmp
