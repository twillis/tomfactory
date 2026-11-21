# Change record: the factory runs from any directory (2026-11-21)

Made outside spec kit, for spec kit to review later.

**Asked for by the operator**, when the orchestrator ran the factory from inside its own folder
because the documented form failed: "on the factory wouldnt installing it as editable fix that? why
are you jumping through that hoop?"

**What was wrong.** The playbook, `orchestrator/factory.md` and the README's alias all say
`uv run --project <path> python -m factory <command>`, from any directory. `pyproject.toml` said
`package = false` and named no build system, so uv never installed `factory` into the environment
and the command answered "No module named factory" anywhere but the factory's own folder.

**Changed**

- `pyproject.toml`: `package = false` is gone; a build system (hatchling) names the `factory`
  package. `uv sync` now installs the factory into its own environment, editable, so the code that
  runs is still the code in the clone. `uv.lock` follows.
- `README.md`: "Using the factory" says both forms work.

**Not changed**: no `factory` console script; the README's alias still serves. Personas and prompts
are still read from the clone, beside the package.

Tests: `tests/test_cli.py::test_runs_from_any_directory` (FR-001), which failed before the change.
The whole suite: 387 passed.
