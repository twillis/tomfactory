# Feature Specification: Contain the Code Agents Write

**Feature Branch**: `002-contain-target-code` (spec directory; no git branch created)

**Created**: 2026-11-19

**Status**: Draft

**Input**: User description: "Contain the code that agents write, when the factory runs it. Today the agents are confined, but the factory then runs the target's tests, written by agents, as the operator, with the operator's files, network and credentials. Wanted: whenever the factory runs a target's code, it runs contained: its own checkout and nothing else of the operator's; no network unless the codebase says so; no local services; nothing outlives the step. If it cannot be contained, refuse; never fall back. A harmless stand-in test becomes a permanent check. Containing the agent program itself is a later phase." (Full text: the request of 2026-11-19, recorded in this feature's checklist notes.)

## Why

The factory confines its agents: they have no shell, and the agent program refuses their reads and edits outside the run's checkout. It then runs the target codebase's tests, which agents wrote, and the code those tests exercise, which agents also wrote. That code runs as the operator.

Measured on 2026-11-19 with a harmless stand-in for an agent-written test, run through the factory's own test path, that test could:

| It could | Measured |
|----------|----------|
| Read the operator's private keys folder | yes |
| Read the factory's own records | yes |
| Read the factory's own code | yes |
| Write outside its checkout, where it lasts | yes |
| Reach the internet | yes |
| Reach a local service equivalent to administrator access (the container daemon's socket) | yes |
| Leave a process running after the factory stopped the step | yes |

The containment the factory promises therefore stops at the agents and does not cover what they produce.

## Terms

- **Operator**: Tom Willis, who owns and runs the factory.
- **Target code**: anything from the target codebase that the factory executes: its tests, and the code they import and run.
- **Contained**: running so that only the run's own checkout, and the read-only tools the code needs, are visible, with the further limits in the requirements.
- **Stand-in test**: a harmless test that tries each of the things in the table above and reports which it could do, without doing harm.

## Clarifications

### Session 2026-11-19

- Q: When a codebase allows its tests the network, should they get the whole network, or only the specific hosts the codebase names? → A: The whole network, for a codebase that allows it; off for everyone else. Named hosts are deferred to phase 2.
- Q: Beyond the machine's own system tools and the Python the factory runs on, may a codebase name further folders of tools its tests need, to be visible read-only? → A: No. Only the system tools and the factory's Python are visible; a per-codebase list is added when a codebase needs it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Target code cannot reach the operator's things (Priority: P1)

When the factory runs a target's tests — before any change, to see them fail first, and to see them pass — that code can read and write its own checkout and read the tools it needs, and nothing else of the operator's. It cannot read the operator's private files, the factory's code or records, or the operator's credentials. It cannot reach the network or local services. Anything it writes outside its checkout is private to it and thrown away when the step ends. Nothing it starts outlives the step.

**Why this priority**: This is the gap. Everything else in this feature supports it.

**Independent Test**: Run the stand-in test through the factory's own test path. Every row of the table above reads "no", and no process it started is still running afterwards.

**Acceptance Scenarios**:

1. **Given** a target whose tests try to read the operator's private keys, the factory's records and the factory's code, **When** the factory runs those tests, **Then** each read fails.
2. **Given** a target whose tests try to write a file outside the checkout, **When** the step ends, **Then** no such file exists outside the checkout.
3. **Given** a target whose tests try to reach the internet and a local administrative service, **When** the factory runs them, **Then** both attempts fail.
4. **Given** a target whose tests start a process that detaches itself, **When** the step ends — normally, at its time limit, or because the operator stopped the run — **Then** that process is no longer running.
5. **Given** a target whose tests write and read files inside the checkout and in a temporary folder, **When** the factory runs them, **Then** they work as they would uncontained.

---

### User Story 2 - Refuse rather than run uncontained (Priority: P2)

If the factory cannot contain target code on this machine — the means to do it is missing or not permitted — it does not run the code at all. The step fails with a reason that says plainly what is missing and what to do about it, and the run ends as needs-me.

**Why this priority**: A containment that quietly switches itself off is worse than none, because the operator believes it is on.

**Independent Test**: Make containment unavailable, request a change, approve the plan, and see the run end as needs-me at the first step that would run target code, with a reason naming what is missing; and see that the target's tests were not run.

**Acceptance Scenarios**:

1. **Given** containment is unavailable, **When** the factory reaches a step that runs target code, **Then** it does not run the code, the step fails, and the run ends as needs-me with a plain reason.
2. **Given** containment is unavailable, **When** the operator asks the factory to check the machine, **Then** the check reports containment as missing and says what to do.
3. **Given** containment is unavailable, **When** a run is planning, **Then** planning still works, because planning runs no target code.

---

### User Story 3 - A codebase may need the network, and says so (Priority: P3)

Some codebases have tests that genuinely need the network. Such a codebase says so in its own committed settings. Only then are its tests given network access, and every run records whether they had it.

**Why this priority**: Without it, any codebase whose tests need the network could not use the factory at all; with it on by default, the main protection would be gone.

**Independent Test**: Run the stand-in test in a codebase that has not asked for the network (it cannot reach it), then in one whose committed settings ask for it (it can), and see each run's record say which.

**Acceptance Scenarios**:

1. **Given** a codebase that says nothing about the network, **When** its tests run, **Then** they cannot reach it.
2. **Given** a codebase whose committed settings say its tests need the network, **When** its tests run, **Then** they can reach it, and everything else in User Story 1 still holds.
3. **Given** a run's checkout where an agent edited the settings to ask for the network, **When** the tests run, **Then** they cannot reach it, because the setting is read from the commit the run started at.
4. **Given** any run, **When** the operator reads it back, **Then** each step that ran target code shows that it was contained and whether it had the network.

---

### User Story 4 - The protection stays in place (Priority: P4)

The stand-in test becomes part of the factory's own checks. If a later change to the factory reopens any of the holes in the table, the factory's own checks fail.

**Why this priority**: A protection nobody re-measures decays silently.

**Independent Test**: Deliberately weaken the containment in a copy of the factory and see the factory's own checks fail, naming the hole.

**Acceptance Scenarios**:

1. **Given** the factory as built, **When** its own checks run, **Then** the stand-in test runs contained and reports "no" for every row.
2. **Given** a change that lets target code read the operator's home, **When** the factory's own checks run, **Then** they fail and say which row turned to "yes".

---

### User Story 5 - Nothing else changes (Priority: P5)

Every kind of run the factory has today — changes, tidy runs, spec kit codebases, resume, questions — works as before. A target codebase's tests that pass today pass when contained.

**Why this priority**: Containment that breaks the factory would be switched off.

**Independent Test**: Run the factory's own checks, then a real request against the viewer, whose existing tests must pass contained.

**Acceptance Scenarios**:

1. **Given** the viewer codebase, **When** its existing tests run contained, **Then** all of them pass.
2. **Given** each kind of run, **When** it is exercised by the factory's own checks, **Then** it behaves as before.

### Edge Cases

- **The operator's environment carries secrets.** Tokens and keys are often in environment variables. Target code must not receive the operator's environment wholesale; it gets only what it needs to run.
- **Tests need a temporary folder.** They get one, private to the step, discarded afterwards.
- **Tests need tools installed under the operator's home.** The Python the factory runs on, and its libraries, are visible read-only. Other tools there, such as another language's runtime, are not: such a codebase's tests fail contained until a per-codebase list of tool folders is added (out of scope).
- **A codebase with the network allowed**: local services reached over the machine's own network become reachable too. That is part of what the operator accepts by allowing it, and the run's record says so.
- **The factory's own code-running steps** that run git, or the notification command, are not target code and are not contained by this feature.
- **A step stopped by the operator or a time limit** while target code is running: nothing it started survives.
- **Containment adds time to every test run.** It must stay small enough not to matter.

## Requirements *(mandatory)*

Requirement numbers continue the factory's single sequence from feature 001, so every test's requirement marker stays unambiguous.

### Functional Requirements

**Containment**

- **FR-068**: Every time the factory executes target code, that code MUST run contained.
- **FR-069**: Contained code MUST be able to read and write the run's checkout, and to read the tools it needs to run. The tools it may read are the machine's own system tools and the Python the factory runs on, with its libraries, and nothing else. It MUST NOT be able to read the operator's home directory otherwise, the factory's code, the factory's records, or the operator's credentials.
- **FR-070**: Contained code MUST NOT be able to make any write outside the checkout that lasts beyond the step. A private temporary folder MUST be available to it and discarded when the step ends.
- **FR-071**: Contained code MUST NOT be able to reach the network, unless its codebase allows it (FR-075), and MUST NOT be able to reach local services through the filesystem, such as the container daemon's socket, in either case.
- **FR-072**: Nothing contained code starts MUST outlive its step, whether the step ends normally, at its time limit, or because the run was stopped.
- **FR-073**: Contained code MUST NOT receive the operator's environment wholesale; only what it needs to run MUST be passed to it.

**Refusing**

- **FR-074**: If target code cannot be contained on this machine, the factory MUST NOT run it. The step MUST fail with a reason that names what is missing and what to do, and the factory's machine check MUST report containment as missing.

**The network, per codebase**

- **FR-075**: A target codebase MAY allow network access for its tests in its committed settings, read from the commit the run started at. The allowance is all or nothing: a codebase that allows it gets the whole network, including services on the local network. Without that setting its tests MUST NOT reach the network.
- **FR-076**: Each step record that ran target code MUST show that it ran contained and whether the network was allowed.

**Keeping it in place**

- **FR-077**: The factory's own checks MUST include the stand-in test, run contained through the same path the factory uses, and MUST fail, naming the capability, if it can do any of the things in the table in "Why".

**Nothing else changes**

- **FR-078**: All existing kinds of run MUST behave as before, and a target codebase's tests that pass uncontained MUST pass contained, given they need nothing this feature forbids.

### Key Entities

- **Containment**: how target code is run; on or unavailable, with or without the network. Recorded on each step that runs target code.
- **Network allowance**: a setting in a target codebase's committed settings, off unless present.
- **Stand-in test**: the harmless test that measures what contained code can do.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-013**: Run contained, the stand-in test can do none of the seven things in the "Why" table: 0 of 7, where today it is 7 of 7.
- **SC-014**: 100% of the viewer's existing tests pass when run contained.
- **SC-015**: When containment is unavailable, 0 target tests are run, and the operator can tell why from the run's reason alone.
- **SC-016**: Containment adds under one second to each test run.
- **SC-017**: A deliberate weakening of containment makes the factory's own checks fail every time it is tried.
- **SC-018**: After any step that ran target code — finished, timed out or stopped — 0 processes it started are still running.

## Assumptions

- **One operator, one Linux machine**, as for the factory. Other operating systems are out of scope.
- **"Contained" is not "isolated as a virtual machine".** Target code shares the machine's operating system kernel. That is judged enough for a codebase's own tests; it is not a defence against deliberately hostile code from strangers.
- **Resource limits are out of scope.** Contained code can still use a lot of processor time or memory until the step's time limit stops it.
- **Only target code is contained.** The agent program, git and the notification command run as today. Containing the agent program is the second phase and needs its own design, because it needs the network and the operator's login.
- **Only the network is allowed per codebase.** There is no per-codebase way to reveal more of the operator's files. If one is needed, it is a later change.
- **The run's record of containment is added to the step record.** No new screen is needed; the viewer can show it later.
- **The means of containment is a planning decision.** What was measured on 2026-11-19 is recorded in this feature's research once planning begins.

## Out of Scope (later)

- Containing the agent program itself (phase 2).
- Per-codebase allowances beyond the network, and allowing only named hosts (phase 2).
- A per-codebase list of extra read-only tool folders.
- Resource limits.
- Other operating systems.
