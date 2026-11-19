"""Control: verification. The named checks applied to a step's result.

A check is a plain function, registered by name, that looks at what a step did and says
whether it passed and why not. Checks are how code, not an agent, decides whether work is
acceptable. A new check is a function with `@register("name")` above it.
"""
from dataclasses import dataclass, field

import os

from factory import config, proc, speckit, workspace

REGISTRY: dict = {}

# Applied by the driver to every step, whatever its entry says. A step cannot leave these out.
ALWAYS = ("factory_untouched", "changes_allowed")   # plus envelope_valid for agent steps


@dataclass
class CheckResult:
    name: str
    passed: bool
    note: str = ""      # why it failed, or a short remark; may hold test output
    timed_out: bool = False     # the check ran a command that hit the time limit


@dataclass
class CheckContext:
    """What a check is given to look at."""
    run: object                 # the run record
    step: object                # the workflow Step
    checkout: object            # the run's Workspace
    target_config: object       # the target's settings at the run's starting commit
    changed: set                # files the step changed in the checkout, from git
    envelope: dict | None       # the agent's parsed envelope, if any
    before: str                 # the factory fingerprint taken before the step
    factory_paths: list = field(default_factory=config.factory_paths)
    stderr_file: object = None  # where a command the check runs sends its standard error
    on_child: object = None     # told the process group of a command the check runs
    timeout: float | None = None


def register(name):
    """Make a check available to step entries under `name`."""
    def add(function):
        REGISTRY[name] = function
        return function
    return add


def get(name):
    if name not in REGISTRY:
        raise LookupError(f"there is no check named {name}; known checks: {', '.join(sorted(REGISTRY))}")
    return REGISTRY[name]


# ---- applied to every step ----

@register("factory_untouched")
def factory_untouched(ctx) -> CheckResult:
    """The factory's own code, personas, prompts and the ideals are as they were (FR-030)."""
    same = workspace.fingerprint(ctx.factory_paths) == ctx.before
    return CheckResult("factory_untouched", same,
                       "" if same else "the factory's own code, personas, prompts or ideals were changed")


@register("changes_allowed")
def changes_allowed(ctx) -> CheckResult:
    """Every file the step changed is within what its entry lets it change (FR-032)."""
    offending = sorted(name for name in ctx.changed
                       if not _allowed(ctx.step.may_change, name, ctx.target_config, ctx.checkout))
    note = (f"this step may change {ctx.step.may_change.replace('_', ' ')} only; it changed: "
            + ", ".join(offending)) if offending else ""
    return CheckResult("changes_allowed", not offending, note)


def under(name, paths) -> bool:
    """Is a file one of these paths, or inside one of these folders?"""
    return any(name == p.rstrip("/") or name.startswith(p.rstrip("/") + "/") for p in paths)


def _allowed(scope, name, settings, checkout=None) -> bool:
    if scope == "spec":     # spec kit's documents, and only where the target uses spec kit
        return (checkout is not None and speckit.available(checkout.path)
                and (under(name, ("specs/",)) or name == speckit.FEATURE_FILE))
    if scope == "tests":
        return under(name, settings.test_paths)
    if scope == "not_tests":
        return not under(name, settings.test_paths) and name not in (".factory.toml", ".gitignore")
    if scope == "docs":
        return under(name, settings.docs_paths)
    return False    # "nothing"


@register("envelope_valid")
def envelope_valid(ctx) -> CheckResult:
    """An agent's reply ended with a JSON object that has every required key, rightly typed."""
    def result(note=""):
        return CheckResult("envelope_valid", not note, note)

    envelope = ctx.envelope
    if not isinstance(envelope, dict):
        return result("the reply did not end with a JSON object")
    for key, kind in ctx.step.envelope.items():
        if key not in envelope:
            return result(f"the envelope has no `{key}`")
        value = envelope[key]
        if kind == "text" and not isinstance(value, str):
            return result(f"`{key}` must be text")
        if kind == "list" and not isinstance(value, list):
            return result(f"`{key}` must be a list")
        allowed = ("accept", "reject") if kind == "verdict" else kind if isinstance(kind, tuple) else None
        if allowed and value not in allowed:
            return result(f"`{key}` must be one of: {', '.join(allowed)}")
    if envelope.get("ideals_broken") and envelope.get("verdict") == "accept":
        broken = ", ".join(str(item) for item in envelope["ideals_broken"])
        return result(f"the review named broken ideals ({broken}) but gave the verdict accept")
    return result()


# ---- the steps' own checks ----

OUTPUT_LIMIT = 6000     # how much of a test run's output is kept and passed on


def run_tests(ctx) -> tuple[int | None, str]:
    """Run the target's test command in the checkout. Returns (exit code, output).

    The command is the one committed in the target at the run's starting commit, never one
    from the checkout. The exit code is None if the command hit the time limit.
    """
    lines: list[str] = []
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    done = proc.run(config.test_argv(ctx.target_config), ctx.checkout.path, ctx.timeout, lines.append,
                    ctx.stderr_file, env=environment, on_child=ctx.on_child)
    output = "\n".join(lines)[-OUTPUT_LIMIT:]
    return (None if done.timed_out else done.exit_code), output


def _timed_out(name, ctx) -> CheckResult:
    return CheckResult(name, False, f"the test command did not finish within {ctx.timeout:g} seconds",
                       timed_out=True)


@register("baseline")
def baseline(ctx) -> CheckResult:
    """Before anything changes: the existing tests pass, or there are none."""
    code, output = run_tests(ctx)
    if code is None:
        return _timed_out("baseline", ctx)
    if code == ctx.target_config.no_tests_exit_code:
        return CheckResult("baseline", True, "no prior tests")
    if code == 0:
        return CheckResult("baseline", True, output)
    return CheckResult("baseline", False, f"the existing tests were already failing:\n{output}")


@register("tests_added")
def tests_added(ctx) -> CheckResult:
    """The step changed at least one file under the test paths."""
    added = any(under(name, ctx.target_config.test_paths) for name in ctx.changed)
    paths = ", ".join(ctx.target_config.test_paths)
    return CheckResult("tests_added", added, "" if added else f"no test file was written under {paths}")


@register("tests_within_budget")
def tests_within_budget(ctx) -> CheckResult:
    """The tests this run added are proportionate: no more lines than the codebase's budget (FR-065)."""
    budget = ctx.target_config.test_budget_lines
    added = ctx.checkout.lines_added([n for n in ctx.changed if under(n, ctx.target_config.test_paths)])
    if not budget or added <= budget:
        return CheckResult("tests_within_budget", True, f"{added} lines of tests added")
    return CheckResult("tests_within_budget", False,
                       f"the tests added {added} lines; this codebase's budget for one run is {budget}. Test each"
                       " behaviour once, at the level where it lives; use parametrised cases for variations of one"
                       " rule; reuse the helpers already there; do not re-test what existing tests cover.")


@register("edge_cases_stated")
def edge_cases_stated(ctx) -> CheckResult:
    """The test writer listed at least one edge or failure case it covered (FR-045)."""
    cases = (ctx.envelope or {}).get("edge_cases")
    stated = isinstance(cases, list) and len(cases) > 0
    return CheckResult("edge_cases_stated", stated, "" if stated else
                       "the tests must state the edge cases and failure cases they cover; none were listed")


@register("tests_fail_first")
def tests_fail_first(ctx) -> CheckResult:
    """The new tests fail before the change is built. "No tests found" is not a failing test."""
    code, output = run_tests(ctx)
    if code is None:
        return _timed_out("tests_fail_first", ctx)
    if code == 0:
        return CheckResult("tests_fail_first", False,
                           "the new tests pass before anything was built, so they do not describe the change")
    if code == ctx.target_config.no_tests_exit_code:
        return CheckResult("tests_fail_first", False,
                           "the test command found no tests to run; the new tests were not collected")
    return CheckResult("tests_fail_first", True, output)


@register("tests_pass")
def tests_pass(ctx) -> CheckResult:
    """Every test passes: the new ones and the ones that were already there."""
    code, output = run_tests(ctx)
    if code is None:
        return _timed_out("tests_pass", ctx)
    return CheckResult("tests_pass", code == 0, output)


@register("verdict_accept")
def verdict_accept(ctx) -> CheckResult:
    """The review's verdict is accept. Otherwise the note carries its reasons."""
    envelope = ctx.envelope or {}
    if envelope.get("verdict") == "accept":
        return CheckResult("verdict_accept", True)
    reasons = [str(reason) for reason in envelope.get("reasons") or []]
    broken = [str(ideal) for ideal in envelope.get("ideals_broken") or []]
    note = "; ".join(reasons) + (f" — ideals broken: {'; '.join(broken)}" if broken else "")
    return CheckResult("verdict_accept", False, note or "the review rejected the result without giving a reason")


@register("verdict")
def verdict(ctx) -> CheckResult:
    """A judging step accepted the work. Otherwise the note says why, and the step's routes say where next."""
    envelope = ctx.envelope or {}
    if envelope.get("verdict") == "accept":
        return CheckResult("verdict", True)
    said = [str(item) for key in ("requirement_changes", "unbuilt", "reasons", "ideals_broken")
            for item in envelope.get(key) or []]
    return CheckResult("verdict", False, "; ".join(said) or f"the verdict was {envelope.get('verdict')}, with no reason given")
