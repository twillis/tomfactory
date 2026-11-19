# 2026 Ventures Constitution

This file holds the rules a spec, plan or task list MUST satisfy. A rule belongs
here only if it can reject a plan. Everything else lives in `CLAUDE.md`,
`CURRENT_WORK.md` or `/knowledge`.

It says how things must be built. It does not say what any product must do; that
belongs in a spec.

## Part I — Core Principles (every venture)

### I. Serve, Don't Extract

Every system we build MUST serve the people who use it. A spec MUST NOT include
a mechanism whose purpose is to capture attention, lock a user in, or harvest
their data for a use they did not ask for.

Rationale: this is the mission. A feature that extracts is the thing the three
ventures exist to resist, whatever it earns.

### II. Start From the Problem and the Person

A spec MUST name who it is for and what that person can do on the finished thing
that they could not do before. The audience MUST be a real, named one. A spec
MUST NOT be justified by an invented "typical user".

A named technology is not a problem statement. A spec that opens with a tool and
no problem MUST go back to assessment.

Rationale: work reviewed only against itself never finishes, because nothing
says what it is for.

### III. No Microsoft Tools

A plan MUST NOT introduce a Microsoft tool, framework, SDK or service. This
includes Azure, Playwright, and Microsoft-published editor extensions.

Carve-out: GitHub hosting, the `gh` CLI and spec kit are already in use by the
operator's choice and are not violations.

### IV. Work Leaves an Artifact That Shows Its Method

Every objective MUST produce a deliverable in `/artifacts`, and that deliverable
MUST say how it was done, what sources were used and what was decided. Reusable
findings MUST be extracted to `/knowledge`.

## Part II — Software Design (any software)

These apply to every spec that produces software: bttr and its apps, Hive,
viz-rig and anything new. They do not apply to publishing, real estate or
learning work.

The operator directs and the robot writes. Review is where the two align, so
these rules exist to make what the operator reads worth reading.

### S1. Three Layers; Only the Differentiating Logic Is Left to Read

Software is divided into a data layer, a control layer and a presentation
layer. The data and presentation layers MUST be general: a new domain SHOULD
need no hand-written code in either.

What remains to read MUST be the logic that makes this system different from
another. A plan that requires per-domain plumbing in the data or presentation
layer MUST justify it as something the general layer could not derive.

The control layer has historically been under-specified, and it is where the
guts of a system live. It will probably turn out to be several layers that are
not yet discovered. A plan MAY propose a new layer inside it, and MUST name what
that layer is responsible for. A plan MUST NOT treat the control layer as a
single undivided place to put whatever does not fit elsewhere.

### S2. Discrete Under Fuzzy

A discrete operation gives a predictable output for a given input, and states
its side effects. A fuzzy operation is an agent acting on context, the user's
goal and the constraints of the discrete operations available to it.

A fuzzy layer MUST act only through declared discrete operations. It MUST NOT
reach persistence or any other layer directly. When a fuzzy outcome is
unreliable, the first remedy MUST be a stronger discrete layer.

### S3. Data Access Through a Repo, Matched by Archetype or Table

All persistence MUST go through a repo. A repo is matched to a table by the
table's archetype, or by its name where the table needs handling of its own.

Special handling MUST stay behind an interface that looks like CRUD to the
caller. A status-history table is the example: the caller updates a status, and
the repo keeps the history correct.

### S4. The Resource Coordinates

An operation is resource + operation + context + input. The resource is
resolved from a path, and the path implies the context and the parent-child
relations of the domain.

The resource coordinates business logic and persistence. Reading an operation
MUST show, at a minimum, the current resource, the current context and the
repo operations performed. Domain logic, where it exists, MUST be written
there, in line with them.

Domain logic MUST NOT live in a repo, in the presentation layer or in transport
code such as an HTTP handler.

### S5. Presentation Is Described, Not Bound to a Medium

An operation MUST return data, its types and its constraints, with hints where
they help. It MUST NOT return output tied to one medium, such as HTML.

A mediator, which MAY be fuzzy, turns that description into what the user needs:
a form, a conversation, a phone call. The user's need decides the medium.

### S6. Any Language the Operator and Robot Can Align On

No language is mandated. A plan MAY choose any language, provided the operator
can review the result.

### S7. Always Leave Room to Extend and Specialise

Whatever a layer derives, a caller MUST be able to extend or specialise it
without changing the layer. A plan that derives a behaviour MUST name where that
behaviour can be overridden.

An override MUST NOT be able to remove a safety property, such as tenant
isolation, by leaving it out.

Rationale: "a general rule for archs that I have managed historically always
leave the ability to extend and specialize on things."

### S8. Every Functional Requirement Has Tests That Fail First

Every functional requirement in a spec MUST be covered by at least one unit or
functional test, and SHOULD be covered by several where it has edge or failure
cases. Each test MUST name the requirement it covers.

A requirement's tests MUST be written before the code that satisfies it, and
MUST be seen to fail before that code is written: red, then green, then
refactor. A task list MUST place each requirement's tests ahead of its
implementation. A plan MUST say how each requirement is tested.

A test MUST NOT be weakened or deleted to make it pass. A requirement that
cannot be tested MUST be rewritten until it can be, or removed.

Rationale: "any FR should have at least one if not several unit/functional
tests that fail until implemented rgr style."

### S9. The Most Functionality for the Least Code; Impeccably Organised

Software MUST deliver what is required with the least code that does so, within
reason. A plan MUST prefer the smaller design that does the same job, and MUST
say what it reuses or removes. A plan MUST NOT add code that repeats what
existing code already does; it MUST give the repeated thing one home instead.

Code MUST be organised so that its structure can be read: each piece has one
obvious place, and a reader can tell where a thing lives before opening a file.
The standard is code worth admiring, not merely code that works.

This applies to tests as much as to the code they cover. Each behaviour is
tested once, at the level where it lives. Variations of one rule MUST be one
parametrised test, not a row of near-identical ones. Test volume MUST be
proportionate to the code.

"Within reason" is part of the rule. Brevity MUST NOT be bought with
obscurity, and a safety property MUST NOT be dropped to save lines.

Rationale: "Most functionality for least amount of code within reason.
Impeccably organized, art." And, of tests: "Parameterized tests seems like a
thing the test writer should be encouraged to use going forward."

## Part III — bttr Principles

These apply when a spec touches `src/bttr_clojure`, `src/chart_app`,
`src/band_app` or `src/bttr_examples`, or when a spec declares itself bttr work,
such as another implementation of a bttr layer. They MUST NOT be applied to any
other work in this repo. They are the bttr form of Part II: B3 is how bttr meets S3,
and B4 is how it meets S4.

### B1. The Schema Is the Source of Truth; Ask the Catalog, Not the Name

The database drives the application. A new table MUST work with no
configuration.

The framework MUST read facts from the catalog (primary key, foreign keys). It
MUST NOT infer them from how a consumer spelled a name. `<table>_uid` is a DDL
style, not a contract.

bttr MAY construct a name it generates itself, such as `summary_view__<table>`.
It MUST NOT construct a name the consumer owns. The test is who is allowed to
break the name.

### B2. Derive Before You Configure

When a feature needs structure, the plan MUST first ask which already-declared
relation implies it. Configuration MAY only override, relabel, reorder or hide
what was derived. Layers apply in order: convention, then domain, then tenant.

Rationale: "view config becomes paint and polish on a sturdy frame."

### B3. Archetypes Carry the Machinery; Domain Code Holds Only Domain

A table declares an archetype (`:entity`, `:ref-data`, `:period-fact`,
`:observation`). The archetype supplies audit columns, tenant scoping, absence
and CRUD. Domain code MUST NOT restate them.

Any proposed registry, vocabulary or self-schema MUST pass one test: does it
delete a description or add one? A proposal that adds one MUST be rejected.

How a row says it is gone is decided by its archetype, never by the author:
`deleted_at` for an entity, `active` and `retired` for ref-data, the end of a
validity range for a period fact. These MUST NOT be collapsed into one flag.

### B4. Traversal, Not Routes; the Path Is the Scope

There are no hard-coded routes. A URL path is a chain of containment, and that
chain is the query scope. A path that names a parent MUST apply that parent. A
request that cannot apply it MUST fail; it MUST NOT answer with wider data.

A path segment asserts that the parent contains the child. A catalog classifies
rows; it does not contain them.

The hierarchy is a tree chosen over the foreign-key graph. Where a table has more
than one possible parent, the choice MUST be declared. It MUST NOT be left to
alphabetical order or any other accident.

Open: the form of that declaration is not yet settled.

### B5. Multi-Tenant by Default

Every domain table is tenant-scoped, enforced at the row level. A plan MUST NOT
add a read or write path that can cross a tenant boundary. Global rows exist for
reference data only.

### B6. Open by Default, Closed Where Being Wrong Is Silent

Defaults point open: a new table works without setup. Where openness is wrong,
the subtraction MUST be structural and derived by every layer, never something
each consumer has to remember.

When bttr cannot answer a question, it MUST pick the direction whose mistake
announces itself. Every plan MUST answer one question for each default and
fallback: if this is wrong, is it loud or silent? Silent and open together need
a stated reason at the call site.

### B7. All-In on PostgreSQL

Where PostgreSQL has a native answer (schemas, EXCLUDE constraints, partial
indexes, generated columns, range types), the plan MUST use it. A plan MUST NOT
emulate in the application something the database already does. Vendor
portability is not a valid reason to avoid a feature.

### B8. Every Table Has an Owning Namespace

A table belongs to a module: auth, multitenancy, configuration, events, or a
consumer's domain. A plan MUST NOT classify tables with a system-or-domain
boolean, and MUST NOT add a new classifier beside the existing ones.

### B9. Mechanism in bttr, Domain in the App

To decide where code belongs, ask whether it would survive the app being split
into its own repository. Generators, seeding primitives and auth screens are
mechanism and belong in bttr. Table specs, demo rows and screens are domain and
belong in the app.

The examples are the lowest priority. A core migration MUST NOT change on their
account. A defect found through an example MUST be re-argued on the merit of a
real consumer before it is fixed.

### B10. No Compatibility Debt, and the Gate Matches the Claim

bttr has no third-party users. Until 2027-08, a plan MUST NOT add work whose only
purpose is backward compatibility.

Every gate in a plan MUST name the claim it proves. A gate that proves "nothing
changed" MUST NOT be applied to a change that intends to change behaviour.

When work runs long, cut mechanism: cold starts, redundant runs. The gates
themselves MUST NOT be cut.

## Scope

- This copy lives in `tomfactory`, a repository inside the 2026 Ventures
  workspace. It was copied from `bttr_rs` on 2026-11-18 at the operator's
  request, "for now"; only this bullet was changed. `/artifacts`, `/knowledge`,
  `CLAUDE.md`, `CURRENT_WORK.md` and the `src/...` paths name things in that
  workspace, at `../../` from here. "This repo" means this repository. The work
  here is software but is not bttr work, so Parts I and II apply and Part III
  does not.
- Part I applies to every spec, plan and task list written in this repo.
- Part II applies to every spec that produces software.
- Part III applies only to specs touching the four bttr paths listed above, or
  declaring themselves bttr work.
- Where rules conflict, the lower-numbered Part wins.
- `src/hive` and `music/viz-rig` are governed by Parts I and II. Publishing,
  real estate and learning work are governed by Part I alone.

## Workflow and Gates

- An idea that has not been judged worth building SHOULD go through
  `/speckit-assess-*` before `/speckit-specify`.
- For bttr work, the recorded decisions D8–D18 in `/knowledge/decisions` are
  binding. A plan that contradicts one MUST say so and propose amending it.
- For bttr work, `bb test` is the gate. A claim about behaviour MUST be shown on
  the running system (REPL, driven browser), not inferred from reading source.
- For every API endpoint the client calls there MUST be a contract test covering
  the full round trip.

## Governance

This constitution supersedes other guidance where they conflict, for work done
through spec kit. `CLAUDE.md` and `CURRENT_WORK.md` remain the operating
instructions for everything else.

Only the operator amends it. An amendment is made with `/speckit-constitution`
and MUST state what changed and why. Versions follow semantic versioning: MAJOR
for a principle removed or redefined, MINOR for a principle or section added,
PATCH for wording.

`/speckit-analyze` treats a conflict with any MUST above as critical. The spec,
plan or tasks change to comply; the rule is not reinterpreted to fit.

**Version**: 1.4.0 | **Ratified**: 2026-11-10 | **Last Amended**: 2026-11-18

Amendment 1.4.0 (2026-11-18, this copy only): added S9, "The Most Functionality
for the Least Code; Impeccably Organised", at the operator's direction ("That
should be in the constitution"), after the factory's test writer produced ten
lines of tests for every line of code. MINOR: a principle was added.

Amendment 1.3.0 (2026-11-18, this copy only): added S8, "Every Functional
Requirement Has Tests That Fail First", at the operator's direction, so that no
requirement is counted as built without a test that failed first. MINOR: a
principle was added. The `bttr_rs` copy remains at 1.2.1 and does not have S8.
