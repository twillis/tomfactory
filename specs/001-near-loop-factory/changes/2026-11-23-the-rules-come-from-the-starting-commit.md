# Change record: the constitution and spec kit's presence come from the starting commit (2026-11-23)

Made outside spec kit, for spec kit to review later.

**Found by the audit of extension points** (`docs/audits/2026-11-23-extension-points.md`, F1 and F2), checked by the
orchestrator against the code, and fixed on the operator's word ("Sounds like a plan").

**Changed**

- **FR-111, `speckit.py`.** `CONSTITUTION_FILE`; `constitution_at(target, commit)` and `available_at(target, commit)`
  read the committed files.
- **`driver.py`.** The `constitution` input and `table_of` read from the run's starting commit.
- **`checks.py`.** `PROTECTED` names the files no step may change, the constitution added to `.factory.toml`,
  `.gitignore` and the ideals.

Tests: three in `tests/test_speckit.py` (FR-111), all failing before the change.
