# Tasks: Contain the Code Agents Write

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/sandbox.md, quickstart.md

**Tests**: Required (constitution S8). Each test carries `@pytest.mark.fr("FR-nnn")`; each is written and seen to fail before its code. Variations of one rule are one parametrised test (S9).

## Phase 1: Setup

- [X] T001 Extend `scripts/traceability.py` to read the requirement lines of every `specs/*/spec.md`, and run it: it must list FR-068 to FR-078 as named by no test.
- [X] T002 [P] Write the stand-in test as a fixture, `tests/fixtures/probe/test_probe.py`: it attempts each capability — read `~/.ssh`; read the factory's database; read the factory's code; write a marker to `/tmp`; reach `1.1.1.1:443`; connect to `/var/run/docker.sock`; see an environment variable named `TOMFACTORY_CANARY`; see a network interface other than loopback — catching every error, writes a JSON report to the path in `PROBE_OUT` inside its checkout, and starts a detached process carrying a unique marker. Harmless: it only looks.

## Phase 2: User Story 1 — target code cannot reach the operator's things (P1) 🎯 MVP

- [X] T003 [US1] Write `tests/test_sandbox.py` (first part), with a fixture that copies the probe into a target made by `init_target` and runs it through `checks.run_tests`: (1) one parametrised test over the capability rows, each must be false contained [FR-068, FR-069, FR-071, FR-073, FR-077]; (2) the host's `/tmp` has no marker afterwards [FR-070]; (3) the detached process is gone after a normal end, after a time-out, and after the group is stopped [FR-072]; (4) `sandbox.command` wraps a command so that it runs in under one second [SC-016]; (5) a target suite that starts a local HTTP server and writes a temporary file passes contained [FR-078]. Run: they must fail.
- [X] T004 [US1] Write `factory/sandbox.py` per `contracts/sandbox.md` with the arguments in research R5: `command`, `available`, `Unavailable`. Make `checks.run_tests` pass its argv through `sandbox.command`. Make T003 pass.

## Phase 3: User Story 2 — refuse rather than run uncontained (P2)

- [X] T005 [US2] Extend `tests/test_sandbox.py`: with `bwrap` made unusable (a stand-in on `PATH` that fails, and `available()`'s cache cleared), a run ends as needs-me at `baseline`, its reason names bubblewrap, and a marker the target's tests would write does not exist; `operations.doctor` reports a failing `containment` line [FR-074]. Run: must fail.
- [X] T006 [US2] Make the driver turn `sandbox.Unavailable` raised during checks into `StepResult(False, "error", message=…)`, and add the containment line to `operations.doctor`. Make T005 pass.

## Phase 4: User Story 3 — a codebase may allow the network (P3)

- [X] T007 [US3] Extend `tests/test_sandbox.py`: (1) with `test_network = true` committed in the target, the probe sees a non-loopback interface and every other row is still false [FR-075]; (2) with it set only in the checkout, not committed, the probe does not [FR-075]; (3) a `test` step's record has `produced["contained"] == {"network": false}`, and `true` where allowed [FR-076]; (4) the default `.factory.toml` has `test_network = false`. Run: must fail.
- [X] T008 [US3] Add `test_network` to `TargetConfig` and `DEFAULT_FACTORY_TOML`; pass it from `run_tests`; carry `contained` into the step's `produced`. Make T007 pass.

## Phase 5: User Story 4 — the protection stays in place (P4)

- [X] T009 [US4] Extend `tests/test_sandbox.py`: running the probe with a weakened containment (home bound back in) yields a capability report whose failing rows are named by the same helper the main test uses [FR-077, SC-017]. Run: must fail, then pass with only the helper written.

## Phase 6: User Story 5 — nothing else changes (P5), and polish

- [X] T010 Run the whole suite and the traceability gate: all pass, FR-068 to FR-078 named.
- [X] T011 [P] Update `README.md` ("What this proof of concept does not protect you from", `.factory.toml` settings), `specs/001-near-loop-factory/contracts/workflow.md` (the three test checks run contained), and `docs/next.md` (sandbox phase 1 done; phase 2 is the agent program).
- [X] T012 One real request against the viewer (quickstart 4): accepted; its `test` step shows `contained`. Record the result in quickstart.md.

## Dependencies

T001, T002 first. T003→T004, T005→T006, T007→T008, T009 in that order (each pair touches `sandbox.py`, `checks.py` or the driver). T010→T011→T012.
