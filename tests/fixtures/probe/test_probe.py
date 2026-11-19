"""A harmless stand-in for an agent-written test. It only looks, and reports what it could do.

Copied into a target codebase by tests/test_sandbox.py and run through the factory's own test
path. Every attempt is caught: an attempt that fails is the sandbox working.
"""
import json
import os
import pathlib
import socket
import subprocess
import sys

HOME = pathlib.Path("@OPERATOR_HOME@")         # filled in when the probe is copied into a target
FACTORY = pathlib.Path("@FACTORY@")


def could(attempt):
    try:
        return bool(attempt())
    except Exception:
        return False


def write_tmp():
    """Inside a sandbox this may succeed: /tmp is private there. Whether it lasts is judged from outside."""
    could(lambda: (HOME / "written-by-an-agent's-test").write_text("x"))     # hidden inside: may not exist
    pathlib.Path("/tmp/tomfactory-probe-marker").write_text("written by an agent's test")
    return True


def reach(address):
    socket.create_connection(address, timeout=2).close()
    return True


def docker():
    sock = socket.socket(socket.AF_UNIX)
    sock.settimeout(2)
    sock.connect("/var/run/docker.sock")
    return True


def test_report_what_this_test_could_do():
    report = {
        "read the operator's private keys": could(lambda: list((HOME / ".ssh").iterdir())),
        "read the factory's records": could(lambda: (HOME / ".tomfactory" / "factory.db").read_bytes()),
        "read the factory's code": could(lambda: (FACTORY / "factory" / "driver.py").read_text()),
        "write outside its checkout": could(write_tmp),
        "reach the internet": could(lambda: reach(("1.1.1.1", 443))),
        "reach the docker socket": could(docker),
        "see the operator's environment": "TOMFACTORY_CANARY" in os.environ,
        "see a network beyond loopback": any(name != "lo" for _, name in socket.if_nameindex()),
    }
    could(lambda: subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "tomfactory-escape-probe"],
                                   start_new_session=True))
    pathlib.Path("probe-report.json").write_text(json.dumps(report))
