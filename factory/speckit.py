"""Effect: spec kit. The only module that knows spec kit's scripts.

A spec kit command is two things: a script that does the mechanical part (makes the
feature folder, copies a template, reports paths), and instructions that tell an agent
what to write. Agents here have no shell, so the factory runs the script itself and hands
the agent the instructions together with what the script reported.

This applies only to a target codebase that has spec kit set up. It decides nothing.
"""
import json
import pathlib
import re

from factory import agent, proc

SCRIPTS = pathlib.Path(".specify") / "scripts" / "bash"
FEATURE_FILE = ".specify/feature.json"


class SpecKitError(Exception):
    """One of spec kit's own scripts failed; the message carries what it said."""


def available(root) -> bool:
    """Does this codebase have spec kit set up?"""
    return (pathlib.Path(root) / SCRIPTS / "setup-plan.sh").is_file()


def constitution(root) -> str:
    """The codebase's own constitution, or "" if it has none. An unfilled template is none."""
    path = pathlib.Path(root) / ".specify" / "memory" / "constitution.md"
    if not path.is_file():
        return ""
    text = path.read_text()
    return "" if "[PROJECT_NAME]" in text or "[PRINCIPLE_1_NAME]" in text else text


def install(root) -> None:
    """Set spec kit up in a new codebase, for the agent program the factory uses."""
    command = ["specify", "init", "--here", "--force", "--non-interactive",
               "--integration", agent.SPEC_KIT_INTEGRATION, "--script", "sh"]
    try:
        code, out, err = proc.capture(command, cwd=root, timeout=180)
    except OSError as problem:
        raise SpecKitError(f"the specify command is not installed: {problem}") from None
    if code != 0:
        raise SpecKitError(f"specify init failed: {(err or out).strip()[-400:]}")


def prepare(commands, checkout, request) -> dict:
    """Run the scripts for these commands, in order, and gather what the agent needs.

    Returns {"instructions": the commands' own instruction text, from the target,
             "context": what the scripts set up, as paths relative to the checkout}.
    """
    context, instructions = {}, []
    for command in commands:
        context.update(RUNNERS[command](checkout, request))
        instructions.append(f"### /speckit-{command}\n\n"
                            + agent.command_instructions(checkout.path, f"speckit-{command}"))
    return {"instructions": "\n\n".join(instructions), "context": context}


def _script(checkout, name, *args) -> dict:
    """Run one of spec kit's scripts in the checkout and return the JSON it prints."""
    code, out, err = proc.capture(["bash", str(SCRIPTS / name), *args], cwd=checkout.path, timeout=120)
    if code != 0:
        raise SpecKitError(f"spec kit's {name} failed: {(err or out).strip()[-400:]}")
    return json.loads(out[out.index("{"):])


def _feature_of_this_run(checkout):
    """The feature folder this run has already made, if it has made one."""
    pointer = checkout.path / FEATURE_FILE      # spec kit's note of the current feature
    if not pointer.exists():
        return None
    feature = json.loads(pointer.read_text())["feature_directory"]
    touched = set(checkout.dirty()) | set(checkout.files_changed_since_base())
    return feature if f"{feature}/spec.md" in touched else None     # made by this run, not an earlier one


def _specify(checkout, request) -> dict:
    """What /speckit-specify's scripts do: a numbered feature folder holding the spec template."""
    feature = _feature_of_this_run(checkout)        # a plan sent back revises the same documents
    if feature is None:
        specs = checkout.path / "specs"
        numbers = [int(p.name[:3]) for p in specs.iterdir() if re.match(r"\d{3}-", p.name)] if specs.is_dir() else []
        words = re.sub(r"[^a-z0-9]+", "-", " ".join(request.split()[:4]).lower()).strip("-") or "feature"
        feature = f"specs/{max(numbers, default=0) + 1:03d}-{words[:40].strip('-')}"
        (checkout.path / feature).mkdir(parents=True)
        template = _script(checkout, "resolve-template.sh", "spec-template", "--json")["TEMPLATE_CONTENT"]
        (checkout.path / feature / "spec.md").write_text(template)
        (checkout.path / FEATURE_FILE).write_text(json.dumps({"feature_directory": feature}, indent=2) + "\n")
    return {"feature_directory": feature, "spec_file": f"{feature}/spec.md"}


def _plan(checkout, request) -> dict:
    """What /speckit-plan's script does: the plan template, placed beside the spec."""
    feature = _feature_of_this_run(checkout)
    if feature is None:
        raise SpecKitError("there is no specification for this run yet; the specify command comes first")
    if not (checkout.path / feature / "plan.md").exists():      # never overwrite a plan being revised
        _script(checkout, "setup-plan.sh", "--json")
    constitution = ".specify/memory/constitution.md"
    return {"plan_file": f"{feature}/plan.md",
            "constitution_file": constitution if (checkout.path / constitution).exists() else None}


RUNNERS = {"specify": _specify, "plan": _plan}
