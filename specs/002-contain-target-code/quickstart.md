# Quickstart: Proving the Containment Works

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## 1. The factory's own checks (no quota)

```bash
uv run pytest -q
# the requirement gate now runs as part of test collection, over every feature's spec
```

**Expect**: everything passes, including `tests/test_sandbox.py`, whose stand-in test reports 0 of 8 capabilities contained (the seven measured, plus seeing an operator environment variable), nothing left running, and under one second of overhead. **Proves**: SC-013, SC-016, SC-017, SC-018.

## 2. The machine check

```bash
uv run python -m factory doctor
```

**Expect**: a `containment` line reading ok.

## 3. The viewer, contained (no quota)

Covered by a factory test that runs a codebase's suite through the contained path; and, by hand, the measurement in research R4 (434 passed, 24.9 s). **Proves**: SC-014.

## 4. One real run (quota)

A small request against the viewer. **Expect**: accepted; `factory show --step <id>` on its `test` step shows `contained` with `network: false`. **Proves**: SC-014 end to end, FR-076.

## 5. Refusing (no quota)

Covered by a factory test that makes containment unavailable. **Expect**: the run ends as needs-me at `baseline` with a reason naming bubblewrap, and the target's tests never ran. **Proves**: SC-015.

## Results — 2026-11-19

**Quickstart 1–3, 5**: the factory's suite, 290 tests including 20 for containment, passes. `doctor` reports containment ok. The traceability gate names all 78 requirements across both features.

**Quickstart 4, one real run** (run 15, a `--tidy code` request on the viewer): the viewer's suite ran contained four times, 434 passed each time, about 25 s each, the same as uncontained. Every test step's record shows `contained: {"network": false}`. **Containment is proven end to end.**

The run itself ended as needs-me, for a reason unrelated to containment: the planner, not told the run was a tidy that holds the tests still, planned three new tests. The code writer may not write tests in a tidy, so the reviewer rejected the result three times for the missing tests, while saying the code change itself was correct. Recorded in `docs/next.md` as a fix.
