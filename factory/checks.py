"""Control: verification. The named checks applied to a step's result.

A check is a plain function, registered by name, that looks at what a step did and says
whether it passed and why not. Checks are how code, not an agent, decides whether work is
acceptable. A new check is a function with `@register("name")` above it; the registry
stamps the name on what it returns. Which checks a step gets is a rule: workflow.checks_for.
"""
from dataclasses import dataclass, field, replace

from factory import config, own_files, proc, sandbox, speckit, workspace
from factory.config import under
from factory.workflow import ACCEPT, CheckResult, verdicts

REGISTRY: dict = {}

# Applied by the driver to every step, whatever its entry says. A step cannot leave these out.
ALWAYS = ("factory_untouched", "changes_allowed")


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
        REGISTRY[name] = lambda ctx: replace(function(ctx), name=name)
        REGISTRY[name].__doc__ = function.__doc__
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
    same = own_files.fingerprint(ctx.factory_paths) == ctx.before
    return CheckResult(same, "" if same else "the factory's own code, personas, prompts or ideals were changed")


@register("changes_allowed")
def changes_allowed(ctx) -> CheckResult:
    """Every file the step changed is within what its entry lets it change (FR-032)."""
    offending = sorted(name for name in ctx.changed
                       if not _allowed(ctx.step.may_change, name, ctx.target_config, ctx.checkout))
    note = (f"this step may change {ctx.step.may_change.replace('_', ' ')} only; it changed: "
            + ", ".join(offending)) if offending else ""
    return CheckResult(not offending, note)


def _allowed(scope, name, settings, checkout) -> bool:
    if scope == "spec":     # spec kit's documents, and only where the target uses spec kit
        return speckit.available(checkout.path) and speckit.owns(name)
    if scope == "tests":
        return under(name, settings.test_paths)
    if scope == "not_tests":
        return not under(name, settings.test_paths) and name not in (".factory.toml", ".gitignore", config.IDEALS_FILE)
    if scope == "docs":
        return under(name, settings.docs_paths)
    return False    # "nothing"


@register("envelope_valid")
def envelope_valid(ctx) -> CheckResult:
    """An agent's reply ended with a JSON object that has every required key, rightly typed."""
    envelope = ctx.envelope
    if not isinstance(envelope, dict):
        return CheckResult(False, "the reply did not end with a JSON object")
    for key, kind in ctx.step.envelope.items():
        if key not in envelope:
            return CheckResult(False, f"the envelope has no `{key}`")
        value = envelope[key]
        if kind == "text" and not isinstance(value, str):
            return CheckResult(False, f"`{key}` must be text")
        if kind == "list" and not isinstance(value, list):
            return CheckResult(False, f"`{key}` must be a list")
        allowed = verdicts(ctx.step) if kind == "verdict" else kind if isinstance(kind, tuple) else None
        if allowed and value not in allowed:
            return CheckResult(False, f"`{key}` must be one of: {', '.join(allowed)}")
    return CheckResult(True)


# ---- a judging step's verdict ----

@register("verdict")
def verdict(ctx) -> CheckResult:
    """A judging step accepted the work, and its reply agrees with itself. Otherwise the note says why.

    Where a failed verdict leads is the step's routes; a reply that contradicts itself (accept,
    while naming broken ideals) is its on_fail.
    """
    envelope = ctx.envelope or {}
    broken = [str(item) for item in envelope.get("ideals_broken") or []]
    if envelope.get("verdict") == ACCEPT:
        return CheckResult(not broken, f"the verdict was accept, but these ideals were named as broken: "
                                       f"{', '.join(broken)}" if broken else "")
    said = [str(item) for key in ("requirement_changes", "unbuilt", "reasons", "ideals_broken")
            for item in envelope.get(key) or []]
    return CheckResult(False, "; ".join(said) or f"the verdict was {envelope.get('verdict')}, with no reason given")


# ---- what the test writer produced ----

@register("tests_added")
def tests_added(ctx) -> CheckResult:
    """The step changed at least one file under the test paths."""
    added = any(under(name, ctx.target_config.test_paths) for name in ctx.changed)
    return CheckResult(added, "" if added else
                       f"no test file was written under {', '.join(ctx.target_config.test_paths)}")


@register("tests_within_budget")
def tests_within_budget(ctx) -> CheckResult:
    """The tests this run added are proportionate: no more lines than the codebase's budget (FR-065)."""
    budget = ctx.target_config.test_budget_lines
    added = ctx.checkout.lines_added([n for n in ctx.changed if under(n, ctx.target_config.test_paths)])
    if not budget or added <= budget:
        return CheckResult(True, f"{added} lines of tests added")
    return CheckResult(False, f"the tests added {added} lines; this codebase's budget for one run is {budget}."
                              " Keep them proportionate, as your priorities say.")


@register("edge_cases_stated")
def edge_cases_stated(ctx) -> CheckResult:
    """The test writer listed at least one edge or failure case it covered (FR-045)."""
    cases = (ctx.envelope or {}).get("edge_cases")
    stated = isinstance(cases, list) and len(cases) > 0
    return CheckResult(stated, "" if stated else
                       "the tests must state the edge cases and failure cases they cover; none were listed")


# ---- running the target's tests ----

def run_tests(ctx) -> tuple[int | None, str, dict]:
    """Run the target's test command in the checkout, contained. Returns (exit code, output, containment).

    The command, and whether it may reach the network, are as committed in the target at the
    run's starting commit, never as in the checkout. The exit code is None if the command hit
    the time limit. Raises sandbox.Unavailable, and runs nothing, if it cannot be contained.
    """
    lines: list[str] = []
    network = ctx.target_config.test_network
    argv = sandbox.command(config.test_argv(ctx.target_config), ctx.checkout.path, network)
    done = proc.run(argv, ctx.checkout.path, ctx.timeout, lines.append, ctx.stderr_file, on_child=ctx.on_child)
    output = "\n".join(lines)[-OUTPUT_LIMIT:]
    return (None if done.timed_out else done.exit_code), output, {"network": network}


OUTPUT_LIMIT = 6000     # how much of a test run's output is kept and passed on
SUMMARY_LINES = 5       # how many of its last lines a failure's note carries


def _tests_judged(ctx, judge) -> CheckResult:
    """Run the tests, then let `judge(exit code)` say (passed, note). Output and containment are kept."""
    code, output, contained = run_tests(ctx)
    if code is None:
        return CheckResult(False, f"the test command did not finish within {ctx.timeout:g} seconds",
                           output=output, timed_out=True, contained=contained)
    passed, note = judge(code)
    if not passed and output.strip():       # the reason a person reads ends with what the tests last said
        note += ":\n" + "\n".join([line for line in output.splitlines() if line.strip()][-SUMMARY_LINES:])
    return CheckResult(passed, note, output=output, contained=contained)


@register("baseline")
def baseline(ctx) -> CheckResult:
    """Before anything changes: the existing tests pass, or there are none."""
    none = ctx.target_config.no_tests_exit_code
    return _tests_judged(ctx, lambda code: (True, "no prior tests") if code == none else
                         (True, "") if code == 0 else (False, "the existing tests were already failing"))


@register("tests_fail_first")
def tests_fail_first(ctx) -> CheckResult:
    """The new tests fail before the change is built. "No tests found" is not a failing test."""
    none = ctx.target_config.no_tests_exit_code
    return _tests_judged(ctx, lambda code: (
        (False, "the new tests pass before anything was built, so they do not describe the change") if code == 0
        else (False, "the test command found no tests to run; the new tests were not collected") if code == none
        else (True, "")))


@register("tests_pass")
def tests_pass(ctx) -> CheckResult:
    """Every test passes: the new ones and the ones that were already there."""
    return _tests_judged(ctx, lambda code: (code == 0, "" if code == 0 else "the tests fail"))
