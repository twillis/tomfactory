# A step's effort starts at medium and climbs on a retry (FR-158, amended)

**Asked.** The operator, 2026-11-26, after the effort per step landed: "default should be medium effort and then
escalate if theres a retry".

**Changed.** An agent step with no `effort` set starts at `medium` instead of the program's own default.
`workflow.effort_for` climbs one effort for each earlier attempt whose work was found wanting
(`records.attempts_climbed`, the same count that climbs grades), never past `effort_climbs_to` (a new setting,
default `high`) unless the step was set above it. The step's start event records the effort it ran at; `factory
table` shows each agent step's starting effort. A retry climbs model and effort together.

**Note.** A planning speaker's later rounds count as earlier attempts, so rounds after the first run at `high`.
