# Change record: tests that cannot be read are not failing tests (2026-11-20)

Made outside spec kit with the operator's agreement ("Fix both"), for spec kit to review later.

**Found on run 22**, the third run on `bttr_erp`. The test writer wrote
`{... for t in (reading := catalog.read(engine))}`, which Python refuses to compile. The whole
test file could not be loaded. `tests_fail_first` asks only whether the test command's exit
code is something other than "passed" and "no tests found", so a file that cannot be loaded
counted as tests failing first. The builder then made three attempts at tests that could never
run. It may not change a test file, so it had no way out, and the run ended as needs-me.

A copy of the run's files with that one line repaired ran 112 tests green and one red, and the
one red was a second mistake in the tests (an error code that PostgreSQL 18 changed). The build
itself was right.

**Why not the exit code.** pytest gives the same exit code for a syntax error in a test file as
for a test file that imports a module not built yet, and the second is the ordinary state of
new tests before the build. Only the first is a mistake.

**Changed, FR-089.** A new setting, `tests_readable_command`, by default
`python -m compileall -q tests`. `tests_fail_first` runs it first, contained and without the
network. If it fails, the step fails with what it said, and the step's existing route sends the
work back to the test writer. `""` switches it off; another language names its own command.

**Not changed**: a test that is readable but wrong about the world (the error code above) still
reaches the builder. Nothing but running it against the real thing can tell.

Tests: `tests/test_sandbox.py`, `test_new_tests_must_be_readable_before_they_count_as_failing`.
