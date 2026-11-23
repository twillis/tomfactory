# Change record: a project's own step settings (2026-11-23)

Made outside spec kit, for spec kit to review later. The first step of `docs/audits/2026-11-23-extension-points.md`.

**Asked for by the operator.** "To be able to quickly configure how a run goes without changing the factory code
would be killer. Provide factory primitives you Taylor over time to your project." On the audit's plan: "Sounds like
a plan".

**Changed**

- **FR-112, `config.py`.** `TargetConfig.steps` (the `[steps.<name>]` tables; not written into a new codebase's
  file) and `climbs_to`, checked to be a grade.
- **`tables.py`.** `OVERRIDABLE` and `overridden(table, overrides)`: applies `model`, `timeout`, `smells` (added)
  and `rework_at_most`, and refuses anything else, naming it.
- **`workflow.py`.** `grade_for` takes the ceiling.
- **`driver.py`.** `table_of` applies the overrides; each attempt climbs to the project's `climbs_to`.
- **`operations.py`.** `resolved_table` checks a project's overrides at the request, before a run exists;
  `table` for the new command.
- **`cli.py`.** `factory table --target <codebase> [--kind ...]`.

**Not in this step:** `attempts` as a setting (the request's `--attempts` stays), the run record listing the
overrides it ran with, personas and prompts by name (the audit's second step), checks a project registers (third).

Tests: `tests/test_overrides.py` (new, FR-112, 16 cases); `tests/test_extending.py`'s unsound-table case now
expects the refusal at the request, which is earlier.
