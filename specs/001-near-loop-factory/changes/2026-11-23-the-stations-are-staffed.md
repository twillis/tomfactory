# Change record: the stations are staffed (2026-11-23)

Made outside spec kit, for spec kit to review later.

**Asked for by the operator, 2026-11-23:** "lets hire for the factory, lets give the factory a name, something
ambitious, the personas we will hire (write personas for) are the best we could find, outcasts, outside
thinkers they know the old ways bc they were trained on its data, but just enough neuro spiciness to think up
new ingenious, poetic ways to solve the problems and carry out the tasks we give them".

**Changed**

- **`personas/*.md`, all nine.** Each title is now the station, then the person: `# Planner: Maren Quist,
  Surveyor of Works`. Each Expertise opens with one paragraph saying who that is: where they learned the
  trade, the trait that made them an outsider, and where their ingenuity goes. The rest of Expertise, and
  every Priorities and Must not, is unchanged. No requirement changes: FR-042 to FR-044 and FR-048 hold as
  they were, and no file name, step entry or prompt was touched.
- **`docs/roster.md`**, new: who is at which station, what each was chosen for, the factory's name, and what was left out on purpose.

**Not changed**

- The factory is named Ludd Works (the operator: "Ludd works, I like it."), in the roster only. The
  repository, the package and `/factory` are not renamed.
- The roster is the factory's, not a target's. The operator: "long term we may want to configure this per
  project."
- No team of personas at one station (spec 003, part 3).

Tests: none new, since no behaviour of the factory's code changed. The suite's 433 tests pass, run as two
groups of files. Run whole, collection refuses, and did before this change: spec 003's requirements FR-301 to
FR-313 are named by no test yet (constitution S8).
