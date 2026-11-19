# Implementation Plan: Contain the Code Agents Write

**Branch**: `002-contain-target-code` (spec directory) | **Date**: 2026-11-19 | **Spec**: [spec.md](spec.md)

## Summary

Run the target codebase's test command — the only place the factory executes a target's code — inside bubblewrap, so it sees its checkout, the system read-only and the factory's Python, and nothing else of the operator's: no home, no records, no credentials, no environment, no network unless the codebase allows it, no local services, and nothing outliving the step. If bubblewrap does not work, refuse to run the tests. The measured stand-in test becomes a permanent factory test.

## Technical Context

**Language/Version**: Python 3.13, standard library (as feature 001)
**Primary Dependencies**: `bwrap` (bubblewrap) from the system, already installed; no Python dependency
**Storage**: no schema change; one key in the target's `.factory.toml`, one key in a step's `produced`
**Testing**: pytest; real `bwrap` runs in the factory's own tests (about 10 ms each)
**Target Platform**: Linux (Ubuntu 26.04 here); bubblewrap ≥ 0.4
**Project Type**: command-line tool (as feature 001)
**Performance Goals**: under one second added per test run (SC-016); measured about 10 ms
**Constraints**: no system change (no `sudo`, no AppArmor edit); fail closed
**Scale/Scope**: one new module of roughly 40 lines; changes in 4 existing modules

## Constitution Check

*Gate before research, re-checked after design.* Constitution 1.4.0; Parts I and II apply.

| Rule | Result | Evidence |
|------|--------|----------|
| I. Serve, don't extract | Pass | Protects the operator; reports nowhere. |
| II. Start from the problem and the person | Pass | The spec opens with the measured problem and the named operator. |
| III. No Microsoft tools | Pass | bubblewrap is a Flatpak project. Docker was considered and not used. |
| IV. Artifact shows its method | Pass | research.md records the measurements and the alternatives. |
| S1. Three layers | Pass | `sandbox.py` is an effect module beside `proc.py`; decides nothing. |
| S2. Discrete under fuzzy | Pass | Strengthens the discrete layer under the agents: what their code can do is now bounded by the factory, not by trust. |
| S3. Data through a repo | Pass | No persistence added beyond a key in `produced`, written through the gateway as today. |
| S5. Presentation described | Pass | Containment appears as data on the step record. |
| S7. Room to extend | Pass | One override point, `test_network`, in the target's committed settings. Containment itself cannot be turned off by a target or by a step entry: there is no setting for it. |
| S8. Tests fail first | Pass | Every requirement FR-068 to FR-078 is named by a test written first; the traceability gate is extended to read every spec. |
| S9. Least code, impeccably organised | Pass | One module, one call site (`run_tests`), one exception. The probe test is one parametrised table of capabilities. |

**Result**: pass. Re-checked after design: no change.

## Design

### `factory/sandbox.py` (new, effect)

`command(argv, checkout, network=False) -> argv` and `available() -> (bool, reason)`, as in [contracts/sandbox.md](contracts/sandbox.md), with the arguments measured in research R5. `Unavailable` is its one exception.

### Changes

| Module | Change |
|--------|--------|
| `checks.py` | `run_tests` passes the test argv through `sandbox.command`, with `network` from the target's settings; the step's result carries `{"contained": {"network": …}}` |
| `config.py` | `TargetConfig.test_network = False`; the default `.factory.toml` gains the line |
| `driver.py` | a `sandbox.Unavailable` raised while checks run becomes `StepResult(False, "error", message=…)`, so the run ends as needs-me without looping |
| `operations.py` | `doctor` reports containment |
| `scripts/traceability.py` | reads the requirements of every `specs/*/spec.md` |

No change to `workflow.py`: which steps run tests is already data, and every one of them reaches `run_tests`.

### Tests (written first)

`tests/test_sandbox.py`, with the stand-in test as a fixture file (`tests/fixtures/probe/test_probe.py`):

| Test | Requirements |
|------|--------------|
| One parametrised test over the eight capabilities: run contained through `checks.run_tests`, each reads "no" | FR-068 to FR-071, FR-073, FR-077 |
| The same probe with `test_network = true`: it sees a network beyond loopback; every other row still "no" | FR-075 |
| A process the probe detaches is gone after the step, after a time-out, and after a stop | FR-072 |
| A file the probe writes to `/tmp` is not in the host's `/tmp` afterwards | FR-070 |
| With `bwrap` unusable: `baseline` ends the run as needs-me, the reason names it, the tests never ran; `doctor` reports it | FR-074 |
| A weakened sandbox (home bound back in) makes the capability check fail, naming the row | FR-077, SC-017 |
| The step record of a test step has `contained` with the network flag | FR-076 |
| Wrapping adds under one second | SC-016 |
| A codebase's suite that passes uncontained passes contained, including a local HTTP server | FR-078 |

The existing suite (270 tests) passing unchanged covers the rest of FR-078.

## Project Structure

```text
specs/002-contain-target-code/
├── spec.md  research.md  plan.md  data-model.md  quickstart.md
├── contracts/sandbox.md
└── checklists/requirements.md

factory/sandbox.py                       new
tests/test_sandbox.py                    new
tests/fixtures/probe/test_probe.py       new: the stand-in test
```

## Risks

| Risk | Handling |
|------|----------|
| A codebase's tests need a tool under the operator's home other than the factory's Python | They fail contained, with the tool's absence in the output. Out of scope by clarification 2; the README says so. |
| Tests that use git (the checkout's `.git` points into the target's own repository, which is hidden) | They fail contained. No codebase does today. Recorded as a known limit. |
| bubblewrap is removed or its AppArmor profile changes | The factory refuses to run tests and `doctor` says so; the factory's own suite fails. |
| No seccomp layer | Accepted for phase 1 (research R4); phase 2 revisits with `srt`. |

## Complexity Tracking

No violations.
