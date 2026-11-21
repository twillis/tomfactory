# Change record: lessons from run 30's retro (2026-11-21)

Made outside spec kit with the operator's agreement ("Merge and batch"), for spec kit to review later.

**Changed (FR-096)**

- **Test output keeps both ends.** `checks.kept_output` keeps a third of `OUTPUT_LIMIT` (now 20,000
  characters, was 6,000) from the beginning and the rest from the end, and says how many lines it
  left out. Cutting only the front had shown the architect and the final review "its last lines, all
  errors", and the builder the tail of a log whose first error was the one that mattered.
- **The planner does not predict the red run.** Three plans in a row got the list wrong; the factory
  now records what failed (FR-095).
- **The planner writes new queries in the form the code will use**, so a library trap (run 30's
  `NOT uid = ANY(path)`) shows before approval.
- **The plan check names one fix** when a finding allows more than one.

**Done outside the factory**: `bttr_erp`'s test command reports every failed and errored test by id
(`-rfE`), so the red run reads case by case; and requests name the records they point to by path,
since a record's file name comes from its request's first words, not its run-order label.

**Not taken**: a shell for the builder. Agents have no shell by design; the fuller output is the
cheaper answer. The "bare SQLSTATE" the builder saw was bttr_erp's own refusal message, recorded there.
