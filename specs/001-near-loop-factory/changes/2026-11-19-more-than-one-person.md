# Change record: names that do not clash, and a codebase's own ideals (2026-11-19)

Made outside spec kit with the operator's agreement ("go ahead"), for spec kit to review later.

**Raised by the operator**: "it would be challenging to have multiple people working on the
repo ... you would have to identify the runs some other way so they don't clash." Run numbers
are counted in each operator's own database, so two people would both produce run 18, with
the same branch and the same record file.

**Changed**

- **FR-081.** A run's branch is `factory/<YYYYMMDD-HHMMSS>-<slug>`, from when it was
  requested (UTC), and its record in `docs/runs/` carries the branch's name. The run's number
  is only the operator's handle for commands. The same request twice in one second on one
  machine gets the number appended. Spec kit's timestamp numbering for features is the same
  idea. Commit subjects still say `(run N)`, a local number; that is a label, not a name.
- **FR-082.** A codebase may commit `IDEALS.md`; where it does, runs on it are held to that,
  read from the starting commit, in place of the operator's personal file, and no step may
  change it.

**Not changed**: the factory is still one operator per machine. Plans awaiting approval,
events and status live in each operator's database, and whoever requested a run approves it.
The shape of a team version (the request an issue, the plan and record a pull request) is
noted in `docs/next.md` and not designed.
