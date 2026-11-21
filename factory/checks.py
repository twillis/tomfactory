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
        if not ctx.step.ideals_stop:     # reported in the sprint review, decided by the operator at merge
            return CheckResult(True, "")
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

class SetupFailed(Exception):
    """The codebase's setup command did not finish cleanly, so its tests were not run."""

    def __init__(self, output, timed_out, contained):
        super().__init__("the setup command failed")
        self.output, self.timed_out, self.contained = output, timed_out, contained


def run_tests(ctx) -> tuple[int | None, str, dict]:
    """Run the target's test command in the checkout, contained. Returns (exit code, output, containment).

    A codebase that names a setup command has it run first, also contained: with the network,
    and able to write to the codebase's own home, which the tests that follow can only read.
    Raises SetupFailed, and runs no tests, if it fails.

    The commands, the tools they may use and whether the tests may reach the network are as
    committed in the target at the run's starting commit, never as in the checkout. The exit
    code is None if the test command hit the time limit. Raises sandbox.Unavailable, and runs
    nothing, if it cannot be contained.
    """
    settings, how = ctx.target_config, {"network": ctx.target_config.test_network}
    if settings.setup_command:
        how["setup"] = {"network": True}
        done, output = _contained(ctx, config.setup_argv(settings), True, home_writable=True)
        if done.timed_out or done.exit_code != 0:
            raise SetupFailed(output, done.timed_out, how)
    done, output = _contained(ctx, config.test_argv(settings), settings.test_network)
    return (None if done.timed_out else done.exit_code), output, how


def _contained(ctx, argv, network, home_writable=False):
    """Run one of the codebase's commands in the checkout, contained. Returns (how it ended, its output)."""
    settings, lines = ctx.target_config, []
    home = config.codebase_home(ctx.checkout.target) if settings.setup_command else None
    wrapped = sandbox.command(argv, ctx.checkout.path, network, settings.tools, home, home_writable)
    done = proc.run(wrapped, ctx.checkout.path, ctx.timeout, lines.append, ctx.stderr_file, on_child=ctx.on_child)
    return done, kept_output(lines)


def _said(note, output) -> str:
    """A reason a person reads, ending with what the command last said."""
    last = [line for line in output.splitlines() if line.strip()][-SUMMARY_LINES:]
    return note + (":\n" + "\n".join(last) if last else "")


OUTPUT_LIMIT = 20000    # how much of a test run's output is kept and passed on (FR-096)


def kept_output(lines) -> str:
    """A command's output, cut to OUTPUT_LIMIT by keeping its beginning and its end.

    The beginning says which tests ran and what failed first; the end carries the summary
    and the last error. Cutting only the front lost the first and kept a run of repeats.
    """
    text = "\n".join(lines)
    if len(text) <= OUTPUT_LIMIT:
        return text
    head, tail = text[:OUTPUT_LIMIT // 3], text[-(OUTPUT_LIMIT - OUTPUT_LIMIT // 3):]
    left_out = text.count("\n") - head.count("\n") - tail.count("\n")
    return f"{head}\n… {left_out} lines left out …\n{tail}"
SUMMARY_LINES = 5       # how many of its last lines a failure's note carries


def _tests_judged(ctx, judge) -> CheckResult:
    """Run the tests, then let `judge(exit code)` say (passed, note). Output and containment are kept."""
    try:
        code, output, contained = run_tests(ctx)
    except SetupFailed as failed:
        note = (f"the setup command did not finish within {ctx.timeout:g} seconds" if failed.timed_out
                else "the setup command failed, so the tests were not run")
        return CheckResult(False, _said(note, failed.output), output=failed.output, timed_out=failed.timed_out,
                           contained=failed.contained)
    if code is None:
        return CheckResult(False, f"the test command did not finish within {ctx.timeout:g} seconds",
                           output=output, timed_out=True, contained=contained)
    passed, note = judge(code)
    return CheckResult(passed, note if passed else _said(note, output), output=output, contained=contained)


@register("baseline")
def baseline(ctx) -> CheckResult:
    """Before anything changes: the existing tests pass, or there are none."""
    none = ctx.target_config.no_tests_exit_code
    return _tests_judged(ctx, lambda code: (True, "no prior tests") if code == none else
                         (True, "") if code == 0 else (False, "the existing tests were already failing"))


@register("tests_fail_first")
def tests_fail_first(ctx) -> CheckResult:
    """The new tests fail before the change is built. "No tests found" is not a failing test.

    Nor is a test file that cannot be read as code (FR-089): it fails whatever is built, and
    the builder, who may not touch tests, could never make it pass.
    """
    settings = ctx.target_config
    if settings.tests_readable_command:
        done, output = _contained(ctx, config.tests_readable_argv(settings), False)
        if done.timed_out or done.exit_code != 0:
            return CheckResult(False, _said("the new tests cannot be read as code, so they describe nothing", output),
                               output=output, timed_out=done.timed_out, contained={"network": False})
    none = settings.no_tests_exit_code
    return _tests_judged(ctx, lambda code: (
        (False, "the new tests pass before anything was built, so they do not describe the change") if code == 0
        else (False, "the test command found no tests to run; the new tests were not collected") if code == none
        else (True, "")))


@register("tests_pass")
def tests_pass(ctx) -> CheckResult:
    """Every test passes: the new ones and the ones that were already there."""
    return _tests_judged(ctx, lambda code: (code == 0, "" if code == 0 else "the tests fail"))
