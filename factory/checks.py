"""Control: verification. The named checks applied to a step's result.

A check is a plain function, registered by name, that looks at what a step did and says
whether it passed and why not. Checks are how code, not an agent, decides whether work is
acceptable. A new check is a function with `@register("name")` above it; the registry
stamps the name on what it returns. Which checks a step gets is a rule: workflow.checks_for.
"""
import json
import re
import textwrap
from dataclasses import dataclass, field, replace

from factory import config, own_files, proc, run_record, sandbox, speckit, workspace
from factory.config import under
from factory.workflow import ACCEPT, CheckResult, verdicts

REGISTRY: dict = {}

# Applied by the driver to every step, whatever its entry says. A step cannot leave these out.
ALWAYS = ("factory_untouched", "changes_allowed", "deletions_inside")


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
    store: object = None        # the factory's records, for a smell that compares with an earlier step (FR-110)
    refused: list = field(default_factory=list)     # deletions the agent asked for that were not made (FR-135)


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


@register("deletions_inside")
def deletions_inside(ctx) -> CheckResult:
    """Every file the agent asked the factory to delete is inside the run's checkout, and neither git's nor the
    factory's own (FR-135). A deletion inside is a change like any other, and changes_allowed judges it."""
    note = ("the factory deletes only files inside the run's checkout, never git's or its own; it was asked to"
            " delete: " + ", ".join(ctx.refused)) if ctx.refused else ""
    return CheckResult(not ctx.refused, note)


def refused_deletions(names, checkout, factory_paths) -> list[str]:
    """Which of the paths an agent asked to delete the factory refuses: one outside the checkout, in git's own
    folder, among the factory's own files, or not a path at all (FR-135)."""
    root = checkout.resolve()
    refused = []
    for name in names:
        file = (root / name).resolve() if isinstance(name, str) and name.strip() else None
        if file is None or not file.is_relative_to(root) or ".git" in file.relative_to(root).parts \
                or any(file.is_relative_to(own.resolve()) for own in factory_paths):
            refused.append(str(name))
    return refused


@register("changes_allowed")
def changes_allowed(ctx) -> CheckResult:
    """Every file the step changed is within what its entry lets it change (FR-032)."""
    offending = sorted(name for name in ctx.changed
                       if not _allowed(ctx.step.may_change, name, ctx.target_config, ctx.checkout))
    note = (f"this step may change {ctx.step.may_change.replace('_', ' ')} only; it changed: "
            + ", ".join(offending)) if offending else ""
    return CheckResult(not offending, note)


# Files no step may change, whatever its scope: what decides how a run is judged (FR-082, FR-111).
PROTECTED = (".factory.toml", ".gitignore", config.IDEALS_FILE, speckit.CONSTITUTION_FILE)


def _allowed(scope, name, settings, checkout) -> bool:
    if scope == "checkout":     # a spike's probe: the whole checkout but what decides how a run is judged (FR-113)
        return name not in PROTECTED
    if scope == "spec":     # spec kit's documents, and only where the target uses spec kit
        return speckit.available(checkout.path) and speckit.owns(name)
    if scope == "tests":
        return under(name, settings.test_paths)
    if scope == "not_tests":
        return not under(name, settings.test_paths) and name not in PROTECTED
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
    said = [str(item) for key in ("requirement_changes", "unbuilt", "reasons", "ideals_broken", "findings")
            for item in envelope.get(key) or []]
    return CheckResult(False, "; ".join(said) or f"the verdict was {envelope.get('verdict')}, with no reason given")


# ---- a planning dialogue (FR-122) ----

@register("dialogue_moves")
def dialogue_moves(ctx) -> CheckResult:
    """The planner proposes aligned, with a plan and an estimate and nothing more to ask; or it asks the asker
    something, or for a measurement. A planner that did neither would leave a round with nothing to go on."""
    said = ctx.envelope or {}
    asks = bool(said.get("questions") or said.get("measure"))
    if said.get("aligned") != "yes":
        return CheckResult(asks, "" if asks else "not aligned, and asking nothing: ask the asker what only they can"
                                                 " say, ask for a measurement, or propose aligned with the plan")
    missing = [key for key in ("plan", "estimate") if not str(said.get(key) or "").strip()]
    if missing:
        return CheckResult(False, f"aligned, with no {' and no '.join(missing)}: give it, or ask what you need")
    return CheckResult(not asks, "aligned, and still asking: it is aligned when there is nothing left to ask" if asks
                       else "")


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
    return CheckResult(False, f"the tests added {added} lines; this codebase's budget for one run is {budget},"
                              " so they may not be proportionate")


@register("lines_within_length")
def lines_within_length(ctx) -> CheckResult:
    """No line the step added to code or tests is longer than the codebase allows (FR-101). Documentation
    is not measured: prose and tables run long."""
    limit = ctx.target_config.line_length
    if not limit:
        return CheckResult(True, "this codebase sets no line length")
    measured = [name for name in ctx.changed if not under(name, ctx.target_config.docs_paths)]
    long = ctx.checkout.long_lines_added(measured, limit)
    if not long:
        return CheckResult(True, f"no added line is over {limit}")
    return CheckResult(False, f"these added lines are longer than this codebase's {limit}, counting indentation: "
                              f"{', '.join(long)}")


FENCE = re.compile(r"^```.*?$(.*?)^```", re.M | re.S)


@register("plan_lines_within_length")
def plan_lines_within_length(ctx) -> CheckResult:
    """No line of code a plan gives is longer than the codebase allows (FR-104): the builder copies a plan's code,
    and a line over the limit would send the build back. Prose is not measured."""
    limit = ctx.target_config.line_length
    text = (ctx.envelope or {}).get("plan") if isinstance(ctx.envelope, dict) else None
    if not limit or not isinstance(text, str):
        return CheckResult(True, "no line length to hold the plan's code to")
    long = [line for block in FENCE.findall(text) for line in block.splitlines() if len(line) > limit]
    if not long:
        return CheckResult(True, f"no line of the plan's code is over {limit}")
    shown = "; ".join(f"{len(line)}: {line.strip()[:60]}" for line in long[:5])
    return CheckResult(False, f"{len(long)} lines of the plan's code are longer than this codebase's {limit}, "
                              f"counting indentation (length: start): {shown}")


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
    return _set_up_then(ctx, config.test_argv(ctx.target_config))


def _set_up_then(ctx, argv) -> tuple[int | None, str, dict]:
    """The codebase's setup command, if it names one, then `argv`, both contained as its tests are."""
    settings, how = ctx.target_config, {"network": ctx.target_config.test_network}
    if settings.setup_command:
        how["setup"] = {"network": True}
        done, output = _contained(ctx, config.setup_argv(settings), True, home_writable=True)
        if done.timed_out or done.exit_code != 0:
            raise SetupFailed(output, done.timed_out, how)
    done, output = _contained(ctx, argv, settings.test_network)
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


def _coverage(ctx) -> dict | None:
    """What the test command's coverage report says (FR-110), or None where the codebase measures none or the
    report is not there. Coverage.py's JSON: the total, and each file's, in percent to one decimal."""
    report = ctx.target_config.coverage_report
    path = ctx.checkout.path / report if report else None
    if not path or not path.is_file():
        return None
    data = json.loads(path.read_text())
    files = {name: round(f["summary"]["percent_covered"], 1) for name, f in data.get("files", {}).items()}
    return {"coverage": round(data["totals"]["percent_covered"], 1), "files": files}


def _tests_judged(ctx, judge) -> CheckResult:
    """Run the tests, then let `judge(exit code)` say (passed, note). Output and containment are kept, and so is
    the coverage the run measured, if the codebase measures it (FR-110)."""
    report = ctx.target_config.coverage_report
    if report:      # a report left by an earlier run must not pass for this one's
        (ctx.checkout.path / report).unlink(missing_ok=True)
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
    return CheckResult(passed, note if passed else _said(note, output), output=output, contained=contained,
                       measured=_coverage(ctx))


def measured_before(store, run_id) -> dict | None:
    """The first coverage the run measured: the tests run before anything changed (FR-110)."""
    for step in store.query("steps", {"run_id": run_id}):
        found = next((c["measured"] for c in step.checks or [] if c.get("measured")), None)
        if found:
            return found
    return None


@register("coverage_holds")
def coverage_holds(ctx) -> CheckResult:
    """Coverage after the run is not below the codebase's floor, and the run did not lower it by more than the
    codebase allows (FR-110). A smell: reported, never a reason to send work back."""
    settings = ctx.target_config
    after = _coverage(ctx)
    if not after:
        return CheckResult(True, "coverage is not measured on this codebase")
    before = measured_before(ctx.store, ctx.run.id) if ctx.store else None
    said = f"coverage {after['coverage']}%"
    wrong = []
    if before:
        change = round(after["coverage"] - before["coverage"], 1)
        said = f"coverage {before['coverage']}% before, {after['coverage']}% after ({change:+.1f})"
        if settings.coverage_drop and -change > settings.coverage_drop:
            lower = sorted(((round(after['files'].get(f, 0) - p, 1), f) for f, p in before["files"].items()
                            if after["files"].get(f, 0) < p))[:5]
            wrong.append(f"it fell by more than {settings.coverage_drop:g} points; most: "
                         + ", ".join(f"{f} ({d:+.1f})" for d, f in lower))
    if settings.coverage_floor and after["coverage"] < settings.coverage_floor:
        wrong.append(f"it is below this codebase's floor of {settings.coverage_floor:g}%")
    return CheckResult(not wrong, "; ".join([said, *wrong]))


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


# ---- a spike: its probe, run by the factory, and its findings (FR-114, FR-115) ----

def probe_runs(store, run_id) -> list[dict]:
    """Every run of a spike's probe in this run, as its check recorded it, the latest last."""
    return [c for s in store.query("steps", {"run_id": run_id}) for c in s.checks or [] if c["name"] == "probe_ran"]


def _probe_file(ctx) -> str:
    """The file the probe step's latest reply names as its probe."""
    named = [s.produced["probe_file"] for s in ctx.store.query("steps", {"run_id": ctx.run.id})
             if isinstance(s.produced, dict) and isinstance(s.produced.get("probe_file"), str)]
    return named[-1].strip() if named else ""


@register("probe_ran")
def probe_ran(ctx) -> CheckResult:
    """The factory runs a spike's probe itself, contained as the tests are (FR-114): the codebase's `probe_command`,
    with {path} the file the probe step named. Whatever it exits with is what it measured, a refusal included. It
    cannot run when that file is not in the checkout, the setup fails, it does not finish in time, or it exits with
    a code that means nothing ran (`probe_cannot_run_exit_codes`, else `no_tests_exit_code`); then it fails, and
    goes back to be mended."""
    settings, path = ctx.target_config, _probe_file(ctx)
    file = (ctx.checkout.path / path).resolve()
    if not path or not file.is_file() or not file.is_relative_to(ctx.checkout.path.resolve()):
        return CheckResult(False, f"the probe step named {path or 'no file'} as its probe, and there is no such file"
                                  " in the run's checkout, so it cannot be run")
    try:
        code, output, contained = _set_up_then(ctx, config.probe_argv(settings, path))
    except SetupFailed as failed:
        return CheckResult(False, _said("the setup command failed, so the probe was not run", failed.output),
                           output=failed.output, contained=failed.contained)
    if code is None:
        return CheckResult(False, f"the probe {path} did not finish within {ctx.timeout:g} seconds", output=output,
                           contained=contained)
    if code in config.cannot_run_codes(settings):
        return CheckResult(False, _said(f"the probe {path} exited {code}, which on this codebase means nothing ran",
                                        output), output=output, contained=contained)
    return CheckResult(True, f"the probe {path} ran, contained, and exited {code}", output=output, contained=contained)


QUOTE = re.compile(r"^```[ \t]*(\S*)[^\n]*\n(.*?)^```", re.M | re.S)     # a fenced block: its language, its lines


@register("findings_quoted")
def findings_quoted(ctx) -> CheckResult:
    """A spike's findings note is where it belongs and quotes only what is there (FR-115): every block of code in it
    is, line for line, in a file on the branch the findings step did not write, and every block fenced as `text` is
    in what the probe printed. A person reads the note as what happened; a quote that is not would mislead him."""
    note = run_record.findings_note(ctx.run)
    if not (ctx.checkout.path / note).is_file():
        return CheckResult(False, f"there is no findings note at {note}; the note is written there and nowhere else")
    printed = [c["output"].splitlines() for c in probe_runs(ctx.store, ctx.run.id)]
    code = [(ctx.checkout.path / name).read_text(errors="replace").splitlines() for name in ctx.checkout.on_branch()
            if name != note and name not in ctx.changed and (ctx.checkout.path / name).is_file()]
    quotes = [(fence, _quoted(block)) for fence, block in QUOTE.findall((ctx.checkout.path / note).read_text())]
    wrong = [_first_missing(lines, printed if fence == "text" else code) for fence, lines in quotes
             if lines and not any(_holds(text, lines) for text in (printed if fence == "text" else code))]
    if wrong:
        return CheckResult(False, "the note quotes what is not, as quoted, in a file on the branch (code) or in what"
                                  " the probe printed (a `text` block); quote whole lines, unchanged, and close a"
                                  " block rather than leave lines out of it. Not found: "
                                  + "; ".join(repr(line) for line in wrong))
    return CheckResult(True, f"each of the note's {len(quotes)} quoted blocks is on the branch or in what the probe"
                             " printed")


def _quoted(block) -> list[str]:
    """A quoted block's lines, without trailing spaces or the blank lines around them."""
    lines = [line.rstrip() for line in block.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def _holds(text, quoted) -> bool:
    """Are the `quoted` lines in `text`, one after another, as written, up to an indentation they share?"""
    want = textwrap.dedent("\n".join(quoted)).splitlines()
    for start, line in enumerate(text):
        if line.strip() == want[0].strip():
            window = textwrap.dedent("\n".join(kept.rstrip() for kept in text[start:start + len(want)])).splitlines()
            if window == want:
                return True
    return False


def _first_missing(quoted, texts) -> str:
    """The first quoted line found in none of `texts`; or, where each is somewhere, the block's first line."""
    seen = {line.strip() for text in texts for line in text}
    return next((line.strip() for line in quoted if line.strip() not in seen), quoted[0].strip())
