# Quickstart: Proving the Containment Works

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## 1. The factory's own checks (no quota)

```bash
uv run pytest -q
uv run python scripts/traceability.py      # now reads every feature's spec
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
