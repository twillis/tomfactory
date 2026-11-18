# Design: personas use their spec kit step (2026-11-18)

**Status**: slice 1 built and tested (the planner with specify and plan; FR-051 to FR-053). Slices 2 to 4 designed, not built. Written outside spec kit with the operator's agreement, for spec kit to review later.

## What the operator asked for

- "between personas in prompts i would like it if they were instructed to use the corresponding speckit command as part of their work/responsibilities."
- Later, listing it as technical debt: personas, "some anyway", should use the spec kit step that corresponds to their role.
- Asked how, given that spec kit's commands run shell scripts and agents have no shell, he chose: **"Factory code runs spec kit."** Agents stay without a shell.

## What a spec kit command is made of

Each command is two things:

1. **A script** that does the mechanical part: finds or creates the feature folder, copies a template, reports paths as JSON.
2. **Instructions** (the command's `SKILL.md`) that tell an agent what to write and how to check it.

So "the factory's code runs spec kit" means: the factory runs part 1, and gives the agent part 2 together with what part 1 reported. The agent then writes the documents with the file tools it already has. Nothing an agent does changes; what it is asked, and where it may write, do.

| Command | Script the factory runs | What the agent writes |
|---------|------------------------|-----------------------|
| specify | `resolve-template.sh spec-template --json`; makes `specs/<NNN-name>/`; writes `.specify/feature.json` | `spec.md`, `checklists/requirements.md` |
| plan | `setup-plan.sh --json` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| tasks | `setup-tasks.sh --json` | `tasks.md` |
| analyze | `check-prerequisites.sh --json --require-spec --require-tasks --include-tasks` | nothing: it reports |
| implement | `check-prerequisites.sh --json --require-tasks --include-tasks` | code and tests; marks tasks done in `tasks.md` |

## Which persona gets which command

The operator said "some anyway" and has not named them. Proposed, to be confirmed:

| Persona | Command | Why |
|---------|---------|-----|
| planner | specify, then plan, then tasks | These three are what a plan is, in spec kit's terms |
| reviewer | analyze | Its job is already to judge the result against what was asked; analyze checks spec, plan and tasks against each other and the constitution |
| test writer, code writer | implement, each for their half | Tasks in `tasks.md` are already ordered tests-first |
| architect, documenter | none | Spec kit has no counterpart |

## How it fits the factory as built

Four additions. None changes the driver's shape: it still names no step.

1. **A step entry can name a spec kit command**: a new optional field, `speckit`, for example `speckit="plan"`.
2. **A new effect module, `factory/speckit.py`**, the only code that knows spec kit's scripts. Given a command name and a checkout, it runs the script and returns the command's instructions and the script's report. Like `agent.py`, it decides nothing.
3. **Two new prompt inputs**, `speckit_instructions` and `speckit_context`, filled by the driver from that module when the step's entry names a command.
4. **A new `may_change` scope, `spec`**: files under `specs/` and `.specify/feature.json`.

The planner's `may_change` becomes `spec` when it is using spec kit, where today it is `nothing`. This is the one loosening, and it is narrow: the planner may write documents under `specs/` and nowhere else, checked from git like every other scope.

## It is opt-in per target

A target codebase uses this only if spec kit is set up in it, meaning `.specify/` is committed. Otherwise a run goes exactly as today.

- `factory init-target --spec-kit <dir>` runs `specify init` in the new codebase before the first commit.
- The target's own constitution (`.specify/memory/constitution.md`) is read by spec kit's instructions. How it relates to the operator's ideals file is an open question below.

## What the operator approves

With spec kit on, the thing waiting for approval is no longer a single plan text. It is the documents on the run's branch: `spec.md`, `plan.md` and `tasks.md`. `factory plan` prints a summary and their paths. Sending the plan back with a comment has the planner revise those files.

This means the plan step commits its documents before the wait, so the later steps start from them.

## Build order

One slice at a time, each usable on its own:

1. **Planner with specify and plan.** The approved plan becomes `spec.md` and `plan.md` in the target. Everything after approval runs as today.
2. **Planner adds tasks**, and the test writer and code writer are given `tasks.md`.
3. **Reviewer with analyze.**
4. **Test writer and code writer follow implement**, marking tasks done.

## Slice 1 as built

- `factory/speckit.py` runs `resolve-template.sh` and `setup-plan.sh`, numbers the feature folder, and returns the target's own `speckit-specify` and `speckit-plan` instructions. Where those instructions live is the agent program's business, so `agent.py` supplies that path.
- The `plan` entry has `speckit=("specify", "plan")`, `may_change="spec"`, and commits its documents before the wait.
- The scope `spec` allows nothing in a target without spec kit, so the planner there still changes no file (FR-052).
- A plan sent back reuses the same feature folder; a later run gets the next number.
- `factory init-target --spec-kit` runs `specify init`.
- Spec kit's own `.gitignore` excludes `.specify/feature.json`, so "has this run made its feature yet" is decided from the spec document, which git does see.
- The agent is given both the operator's ideals and, through spec kit's instructions, the target's constitution. They are not merged.

**Tried for real** (2026-11-18, a temporary home and a new spec kit target, planning only): a real planner, with no shell, produced in 77 seconds (estimated $0.81) `spec.md` (two user stories, FR-001 to FR-005, edge cases, success criteria), `plan.md` (technical context, constitution check, structure), `research.md`, `data-model.md`, `quickstart.md`, a contract and the requirements checklist, all under `specs/001-add-a-module-hello-py/`, committed as "factory: plan (run 1)" and waiting for approval. The three always-applied checks passed. The rest of the cycle was not run on that target.

**Size**: the factory's code is 1,901 non-blank lines against a limit of 2,000. Slices 2 to 4 will not fit without raising the limit or trimming elsewhere.

## Open questions

- **Ideals and the constitution.** A spec kit target has a constitution; the factory has the operator's ideals. They overlap. Are the ideals the constitution, is one copied into the other, or are both given to the agent?
- **Size.** A full spec kit plan step produces five documents and is far heavier than today's one-page plan. For a small request that may be more ceremony than the change. Should the operator be able to choose per request?
- **The wait moves.** If tasks are part of the plan, approval covers three documents. Is one approval enough, or should spec and plan be approved before tasks are written?
- **Which personas.** The table above is a proposal.
- This overlaps with two items already on the next-stage list: "using spec kit's own steps as the cycle" and R23, the expert panel before the plan, which spec kit's assess commands partly cover.
