# Data Model: Contain the Code Agents Write

No new table and no new column. Two small additions to existing shapes.

| Where | Addition | Meaning |
|-------|----------|---------|
| `.factory.toml` (target) | `test_network` (boolean, default `false`) | Whether this codebase's tests may reach the network (FR-075). Read from the run's starting commit. |
| `steps.produced` of a step whose check ran target code | `"contained": {"network": true\|false}` | That the step ran target code contained, and whether the network was allowed (FR-076). Absent on steps that ran no target code. |

A step that could not run its tests because containment was unavailable has `failure = "error"`, and its reason names what is missing (FR-074).
