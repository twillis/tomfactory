# Change record: the approved plan is committed with the code (2026-11-19)

Made outside spec kit with the operator's agreement ("do the fix"), for spec kit to review later.

**Found** publishing the viewer: "there were no corresponding specs". On the plain cycle the
approved plan lived only in the factory's local database, so a codebase the factory built
carried no record of why. The viewer's past runs were exported by hand into its `docs/runs/`.

**Changed** (FR-079): `operations.approve` writes the approved plan to
`docs/plans/<run>-<name>.md` on the run's branch and commits it, as `factory: approved plan
(run N)`, before the run carries on. It holds the request, anything the plan was sent back
with, the plan, how it follows the ideals and its conflicts. It is skipped where the waiting
step follows a spec kit command, since spec kit's documents are committed by their own steps.
Tidy runs, which have no spec kit stages on any codebase, now leave their plan too.

**Tests**: `tests/test_cycle.py` (a change sent back once, then approved; a tidy) and
`tests/test_speckit.py` (nothing written on a spec kit run). Three commit counts rose by one.
