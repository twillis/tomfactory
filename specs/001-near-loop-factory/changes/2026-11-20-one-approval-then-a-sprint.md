# Change record: one approval, then a sprint (2026-11-20)

Proposed with the operator's agreement ("I like all your suggestions"), for spec kit to review later.
Built 2026-11-20, after run 25 ended, tests first: FR-057 and FR-059 amended, FR-090 added.

**Why.** Measured over the first seven runs on `bttr_erp` (runs 18 to 24): of 146 minutes of agent
time and $69.64, planning took 68% of the time and 61% of the cost; the build and its tests took
21% and 14%. The costly loops were before approval: the operator and claude-dev sent specifications
and plans back (four plan passes on run 23, two each on runs 18 and 22), and each pass reran plan,
tasks and analyze. After approval the one costly loop was run 23's final review, which sent the work
back to the build once and then rejected the run over two untested behaviours the rework had added;
a tidy run later showed both held, for $1.14. The operator: "It's like automated waterfall and that
would lead me to believe that automated agile would be better ... What if after the speckit plan the
run (sprint) goes largely auto where deviations to the plan are noted and addressed at the end."

**The three rulings**, as claude-dev proposed them and the operator accepted:

1. **One approval, not two.** Specify, clarify, plan and tasks run in one go, and the operator
   approves once, at the plan. The analyze step's findings are attached to what he reads, as notes,
   and are not a gate. The specification's own approval goes.
2. **After approval, no going back to planning.** A failing test still returns to the builder within
   the attempt limit; nothing else returns. The final review (`converge`) no longer has `replan` or
   `reject`, and no longer sends work back for a requirement it thinks changed. It sorts what it finds
   into the run's record: unbuilt work, what was built differently from the plan and why, requirement
   changes it would propose, and ideals or constitution rules it thinks are broken. A broken ideal does
   not stop the run; it is reported, and the operator decides at merge.
   - Unbuilt work goes back to the build once (`Rework(at_most=2, then=End("accepted"))`), because
     it is the one finding the builder can act on without a new plan; found again, it is a deviation.
     Paperwork the builder cannot write is a detail, not unbuilt work: that was run 25's loop.
3. **A sprint review at the end.** The run ends `accepted` with a list for the operator: what was
   built, every deviation and why, and what the architect advised. The architect is unchanged
   (advice to a backlog, never a gate). The operator merges, and the deviations he wants become the
   next run's request.

**Applies to** the spec kit table. The plain and tidy tables already have one approval and no
replanning; whether the plain `review` should also stop rejecting is left for after this is tried.

**From** run 4b of `bttr_erp`.
