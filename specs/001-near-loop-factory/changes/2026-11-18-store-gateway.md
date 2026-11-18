# Change record: the store becomes a gateway (2026-11-18)

Made outside spec kit with the operator's agreement, on condition it is documented here for
spec kit to review later. His reasons are quoted in research.md, R19.

## What changed

- `factory/store.py` is now one `Gateway` with five operations that take a table:
  `insert`, `get`, `query`, `update`, `delete`. It reads each table's columns from the
  database catalog, so a new table needs only its DDL (which stays in code, as he agreed).
- Rows are plain mappings (`Row`, a dict with access by name). The four data classes
  `Run`, `Plan`, `StepRecord`, `Event` are gone. He said typed records are not needed.
- Conditions are values (`eq`, `ne`, `gt`, `lt`, `is_null`, `not_null`, or a mapping);
  table and column names are checked against the catalog. No operation takes SQL text.
- The per-table repo classes are gone. The rules they hid moved to a new control-layer
  module, `factory/records.py`: branch naming, state changes writing history, a run ending
  once, plan and attempt numbering, a step finishing once, the follow query.
- JSON columns are declared `JSON TEXT` and yes/no columns `BOOLEAN` in the DDL; the
  gateway converts them. Column names and what is stored on disk are unchanged, so the
  observability app is unaffected. The schema carries a version stamp (2); an older home is
  refused with a readable message.
- The operator's `~/.tomfactory/factory.db` was migrated by hand; the original is kept
  beside it as `factory.db.v1.bak`.

## Tests

Written first and seen to fail: `tests/test_store.py` (the gateway, including "a new table
needs no code") and `tests/test_records.py` (the moved rules). 224 tests pass.

## Still to bring into line (not done: the usage limit was reached)

- `contracts/run-store.md` still describes five repos and typed records.
- `plan.md` (S3 and S5 evidence, layer table), `data-model.md` and `README.md` (file
  table) do not yet mention `records.py` or the gateway.
- Constitution S5 was read during the build as "typed records"; this change follows the
  bttr answer instead (types come from the catalog). That reading should be confirmed.
