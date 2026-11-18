# Feature Specification: Near-Loop Software Factory (Proof of Concept)

**Feature Branch**: `001-near-loop-factory` (spec directory; no git branch was created)

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "A small software factory I can run on my own machine, so I can work near the loop instead of in it. I hand it a short written request; it writes a plan and stops; I approve or send it back; after approval it runs a full test-first development cycle unattended and notifies me when finished. I can state ideals every run is held to. Every step is recorded as it happens. The first thing it builds is its own observability app, starting with a hello-world version. It is a proof of concept I must be able to understand, use and extend. It runs on my Claude subscription and must not assume one way of paying or one model." (Full text: `docs/brainstorm-2026-11-18.md`, Part 1.)

## Terms

- **Operator**: Tom Willis, the person who owns and runs the factory. There is one. What the finished factory lets him do that he cannot do now: approve a plan, walk away, and come back to finished, tested, reviewed work.
- **Persona**: a written description of who carries out an agent step — its expertise, what it cares about, and what it must not do. Each agent step has one.
- **Factory**: the system described here.
- **Target codebase**: the codebase a request asks the factory to change.
- **Request**: a short written description of a change the operator wants.
- **Run**: one attempt by the factory to carry out one request, from plan to outcome.
- **Step**: one stage of a run (for example plan, write tests, build, run tests, review, document).
- **Ideals**: the operator's standing principles that every run is held to.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hand over a request and approve its plan (Priority: P1)

The operator writes a short request for a change to a target codebase and hands it to the factory. The factory produces a written plan for the change and stops. The operator reads the plan and either approves it or sends it back with a comment. A plan that is sent back is revised with the comment taken into account and presented again. Nothing in the target codebase changes until a plan is approved.

**Why this priority**: The plan is the one point where the operator's judgment enters a run. Without it there is no "near the loop": the operator would either be absent entirely or back to steering every step.

**Independent Test**: Hand the factory a request, confirm a plan appears and the run is waiting, send the plan back with a comment, confirm the revised plan reflects the comment, and confirm the target codebase is unchanged throughout.

**Acceptance Scenarios**:

1. **Given** a target codebase and a written request, **When** the operator hands the request to the factory, **Then** the factory produces a readable plan and the run waits for the operator without changing the target codebase.
2. **Given** a run waiting on its plan, **When** the operator approves the plan, **Then** the run proceeds to the development cycle without further input.
3. **Given** a run waiting on its plan, **When** the operator sends the plan back with a comment, **Then** the factory produces a revised plan that addresses the comment and waits again.
4. **Given** a run waiting on its plan, **When** the operator abandons the request, **Then** the run ends as rejected with the reason recorded and the target codebase unchanged.

---

### User Story 2 - Unattended test-first cycle with a clear outcome (Priority: P2)

Once the plan is approved, the factory carries out the change without the operator. It first writes tests that describe the change and confirms those tests fail. It then builds the change until those tests and the target codebase's existing tests pass. It documents what it changed, and it reviews the whole result — code, tests and documentation — against the request, the approved plan and the operator's ideals. Each of these steps is carried out by its own persona: the tests are written by a test writer who specialises in testing and in thinking through edge cases, and the change is built by a separate code writer; the reviewer and the documenter are likewise distinct. Tests are run by ordinary deterministic checking, not by asking an agent whether they passed. If the tests fail, the failure is sent back to the build step, up to a fixed number of attempts. The run ends in exactly one of three outcomes — accepted, rejected, or needs-me — with a stated reason, and the operator is notified.

**Why this priority**: This is the work the operator no longer has to sit through. It depends on Story 1 for an approved plan.

**Independent Test**: Approve a plan for a small change, leave the machine alone, and confirm that a notification arrives, that the run shows one of the three outcomes with a reason, and that an accepted result contains new tests that failed before the change and pass after it.

**Acceptance Scenarios**:

1. **Given** an approved plan, **When** the cycle runs, **Then** tests describing the change are written and shown to fail before any of the change is built.
2. **Given** tests that fail after a build attempt, **When** attempts remain, **Then** the failure details are passed back to the build step and it tries again.
3. **Given** tests that still fail after the fixed number of attempts, **When** the limit is reached, **Then** the run stops as needs-me and reports which tests failed and how many attempts were made.
4. **Given** all tests passing, **When** the review finds the result matches the request, the plan and the ideals, **Then** the run ends as accepted and includes a written account of what changed.
5. **Given** all tests passing, **When** the review finds the result does not match the request, the plan or an ideal, **Then** the run ends as rejected and names what did not match.
6. **Given** a run that has ended in any outcome, **When** it ends, **Then** the operator is notified with the outcome and its reason, without having been asked for anything since approving the plan.
7. **Given** a finished run, **When** the operator inspects the target codebase, **Then** the run's changes are kept separate from the operator's own working version until the operator chooses to take them.
8. **Given** an approved plan, **When** the tests are written, **Then** they are written by the test-writer persona, they cover at least one edge or failure case beyond the main path, and the run's record lists the edge cases that were considered.
9. **Given** a finished run, **When** the operator reads it back, **Then** every agent step shows which persona carried it out, and the tests and the change were produced by different personas.

---

### User Story 3 - See what a run is doing and read back what it did (Priority: P3)

Every step of every run is recorded as it happens. While a run is in progress the operator can see which step it is on and how long it has been there. After a run has ended the operator can read back each step: what the step was asked, what it produced, how long it took, and whether its check passed.

**Why this priority**: An unattended system the operator cannot inspect cannot be trusted or improved. Recording is also the raw material for the observability app in Story 5.

**Independent Test**: Start a run, check its current step while it is in progress, then after it ends read back every step and confirm each has its instruction, its output, its duration and its check result.

**Acceptance Scenarios**:

1. **Given** a run in progress, **When** the operator asks for its status, **Then** they see the current step, when it started, and the outcome of every earlier step.
2. **Given** a finished run, **When** the operator reads it back, **Then** each step shows what it was asked, what it produced, how long it took, and whether its check passed.
3. **Given** a step that was repeated after a failure, **When** the operator reads the run back, **Then** every attempt appears separately, in order, with the failure that caused the repeat.
4. **Given** a run that was interrupted before finishing, **When** the operator reads it back, **Then** everything recorded up to the interruption is still present.

---

### User Story 4 - State ideals once and have every run held to them (Priority: P4)

The operator writes down ideals in their own words, once, in one place. Every run is held to them: the plan must follow them, and the review checks the result against them and names any ideal it found broken. An example ideal is "well-defined layers with explicit interfaces between them, so the system can absorb change over time". The operator can edit the ideals at any time, and doing so requires no change to the factory itself.

**Why this priority**: Ideals are how the operator and the factory stay aligned across many runs without the operator repeating themselves in every request. A run can complete without them, so they follow the core cycle.

**Independent Test**: State an ideal, submit a request whose easiest solution would break it, and confirm that the plan addresses the ideal and that a result which breaks it is rejected with that ideal named. Then edit the ideals and confirm the next run uses the new text.

**Acceptance Scenarios**:

1. **Given** stated ideals, **When** a plan is produced, **Then** the plan says how it follows the ideals that apply to the change.
2. **Given** stated ideals and a finished build, **When** the review runs, **Then** it checks the result against each ideal and names any it found broken.
3. **Given** the operator has edited the ideals, **When** the next run starts, **Then** it uses the edited ideals with no other change made to the factory.
4. **Given** no ideals have been stated, **When** a run proceeds, **Then** it completes normally and its record notes that no ideals were in effect.

---

### User Story 5 - The factory builds its own observability app (Priority: P5)

The first target codebase is the factory's own observability app: a way to look at recorded runs. The bare minimum that proves the cycle works is a hello-world version of that app, produced end to end by the factory from a written request. The app then grows into a real tool through further requests, each going through the same cycle.

**Why this priority**: This is the demonstration that the whole cycle works on a real, if tiny, product, and it gives the operator a tool they actually want. It needs Stories 1 to 3 to exist first.

**Independent Test**: Hand the factory a request for a hello-world observability app in an empty target codebase, approve the plan, and confirm the run ends accepted with a working hello-world app the operator can start and see. Then hand it a second request that makes the app show something from a recorded run, and confirm that also completes through the same cycle.

**Acceptance Scenarios**:

1. **Given** an empty target codebase and a request for a hello-world observability app, **When** the operator approves the plan and the run completes, **Then** the result is a working app the operator can start and see, with tests that pass.
2. **Given** the hello-world app exists, **When** the operator submits a further request to extend it, **Then** the change goes through the same plan, approval and cycle, and the existing tests still pass.
3. **Given** the factory is building its own observability app, **When** any run executes, **Then** the factory's own workings, its recorded runs and the operator's ideals are not altered by that run.

---

### User Story 6 - Understand, use and extend the factory (Priority: P6)

The factory is a proof of concept whose purpose is for the operator to see it work, understand how it works, and learn how to use and extend it. It is small enough to read in one sitting. It comes with a written explanation of how a run flows from request to outcome, how to use it, and how to add a new step or a new workflow, which is an obvious, documented change.

**Why this priority**: The operator's stated goal is understanding, not only output. This story constrains how the others are built and is verified last.

**Independent Test**: The operator, coming to the finished factory fresh, reads its documentation and its own source in one sitting, then adds a trivial new step to the cycle by following the documentation, and sees that step appear in the next run's record.

**Acceptance Scenarios**:

1. **Given** the factory's documentation, **When** the operator follows it, **Then** he can hand over a request, approve a plan and read back the run without other help.
2. **Given** the documentation on extending the factory, **When** the operator adds a new step, **Then** the step runs in the next run and appears in that run's record, with no change to the existing steps.
3. **Given** the documentation, **When** the operator looks for how a run decides what happens next, **Then** he finds it stated in one place.

---

### Edge Cases

- **Tests pass before anything is built**: if the newly written tests do not fail first, they do not describe the change. The run treats this as a failed attempt at the test-writing step and tries again within the attempt limit, then stops as needs-me.
- **Target codebase has no existing tests**: the run proceeds with only the newly written tests and records that there were no prior tests.
- **A step never finishes**: every step has a time limit. A step that exceeds it is stopped completely, leaving nothing running, and the run ends as needs-me with the step and the limit named.
- **The factory is interrupted mid-run** (machine restart, operator stops it): on next use the run is shown as stopped at the step it reached, as needs-me, with its record intact. It is never shown as still running and never silently lost.
- **A second request arrives while a run is in progress**: the factory handles one run at a time. It declines the second request with a clear message and does not disturb the run in progress.
- **An agent step changes something it should not** (a file in the checkout outside what that step may change, or the factory's own code, personas, prompts or ideals): the change is detected, undone, and the run ends as needs-me naming what was touched.
- **Code written by an agent misbehaves when the tests run it**: the test command executes agent-written code with the operator's permissions. This stage does not contain that; see Assumptions.
- **The request conflicts with an ideal**: the plan must say so plainly, so the operator decides at the approval point.
- **The plan is sent back repeatedly**: there is no limit on revisions; each revision and comment is recorded.
- **The operator is away when the notification fires**: the outcome and reason remain visible whenever the operator next looks.
- **The subscription's usage limit is reached mid-run**: the run stops as needs-me with that reason; partial work is kept and recorded.
- **The operator's working version of the target codebase has changed since the run began**: the run's result stays separate, so nothing of the operator's is overwritten.

## Requirements *(mandatory)*

### Functional Requirements

**Requests and plans**

- **FR-001**: The operator MUST be able to hand the factory a short written request naming the target codebase it applies to.
- **FR-002**: For every request the factory MUST produce a written plan and then wait for the operator before changing anything in the target codebase.
- **FR-003**: The operator MUST be able to approve a waiting plan, send it back with a comment, or abandon the request.
- **FR-004**: A plan sent back MUST be revised taking the operator's comment into account and presented again; the earlier plan and the comment MUST remain in the run's record.
- **FR-005**: After approval, a run MUST NOT require any input from the operator until it has ended.

**The development cycle**

- **FR-006**: After approval the factory MUST write tests that describe the requested change before building any of the change.
- **FR-007**: The factory MUST confirm that the newly written tests fail before the change is built, and MUST treat tests that already pass as a failed test-writing attempt.
- **FR-008**: The factory MUST build the change and then run both the newly written tests and the target codebase's existing tests.
- **FR-009**: Whether tests passed MUST be determined by running them and reading the result directly, not by asking an agent.
- **FR-010**: When tests fail, the failure details MUST be passed back to the build step for another attempt, up to a fixed number of attempts that the operator can set when making the request and can see on the run.
- **FR-011**: When the attempt limit is reached the run MUST stop and report what failed and how many attempts were made.
- **FR-012**: When tests pass and the change is documented, the factory MUST review the whole result against the request, the approved plan and the operator's ideals.
- **FR-013**: The factory MUST produce a written account of what the run changed, before the review, so the review covers it.
- **FR-014**: Every step MUST have a time limit, and a step that exceeds it MUST be stopped completely, leaving nothing of it running.

**Outcomes and notification**

- **FR-015**: Every run MUST end in exactly one of three outcomes: accepted, rejected, or needs-me.
- **FR-016**: Every outcome MUST carry a stated reason the operator can read.
- **FR-017**: The factory MUST notify the operator when a run ends, with the outcome and its reason.
- **FR-018**: The outcome and reason MUST remain available after the notification, for as long as the run's record exists.
- **FR-019**: A run's changes MUST be kept separate from the operator's own working version of the target codebase until the operator chooses to take them.

**Ideals**

- **FR-020**: The operator MUST be able to state ideals in their own words, in one place, once.
- **FR-021**: Every plan MUST say how it follows the ideals that apply to the change, and MUST state plainly when the request conflicts with an ideal.
- **FR-022**: Every review MUST check the result against the ideals and name any ideal it found broken.
- **FR-023**: Editing the ideals MUST take effect on the next run and MUST NOT require any change to the factory.
- **FR-024**: Each run's record MUST show which ideals were in effect for that run.

**Recording**

- **FR-025**: The factory MUST record every step of every run as it happens, not only when the run ends.
- **FR-026**: For each step the record MUST show which step it was, what it was asked, what it produced, how long it took, and whether its check passed.
- **FR-027**: The operator MUST be able to see, for a run in progress, which step it is on and when that step started.
- **FR-028**: The operator MUST be able to read back any finished run in full, including every repeated attempt in order.
- **FR-029**: An interrupted run MUST keep everything recorded up to the interruption and MUST be shown as stopped, never as still running.

**Safety of the factory itself**

- **FR-030**: A run MUST NOT alter the factory's own code, personas, prompts or the operator's ideals. The factory MUST check this after every step and restore them if they changed.
- **FR-031**: An agent step MUST be confined to the run's own checkout of the target codebase: it MUST NOT be given a shell, and it MUST NOT be able to create or edit files outside that checkout.
- **FR-032**: If an agent step changes a file it is not allowed to change — inside the checkout, or among the factory's code, personas, prompts and ideals — the factory MUST detect it, undo it, and stop the run as needs-me naming what was touched.
- **FR-033**: The factory MUST handle one run at a time and MUST decline a new request while a run is in progress, without disturbing that run.

**First product**

- **FR-034**: The factory MUST be able to produce, from a written request and an empty target codebase, a working hello-world version of an observability app for its recorded runs.
- **FR-035**: Further requests against that app MUST go through the same plan, approval and cycle as any other request.

**Understanding and extending**

- **FR-036**: The factory MUST come with a written explanation of how a run flows from request to outcome and how to use it.
- **FR-037**: Adding a new step or a new workflow MUST be a documented change that does not require altering existing steps.
- **FR-038**: The rules that decide what a run does next MUST be readable in one place.
- **FR-039**: The factory's own source MUST stay small enough to read in one sitting (see SC-007).

**Room for the next stage**

- **FR-040**: The factory MUST work using the operator's existing Claude subscription, with no separate pay-per-use account required.
- **FR-041**: Only the single point where an agent is started MAY depend on which agent program is used, how it is paid for, or which model it uses. Every other part of the factory MUST NOT depend on any of these.

**Personas**

- **FR-042**: Every agent step MUST be carried out by a named persona whose written description states its expertise, what it prioritises, and what it must not do.
- **FR-043**: The persona that writes tests MUST be different from the persona that builds the change. The test-writer persona's description MUST direct it to cover edge cases and failure cases, not only the main path, and MUST forbid it from writing the implementation.
- **FR-044**: The persona that reviews MUST be different from the persona that builds, and MUST NOT see the builder's working conversation, only the result.
- **FR-045**: The test-writing step MUST state the edge cases it considered, and the factory MUST refuse a set of tests that states none.
- **FR-046**: Personas MUST be text the operator can edit. Changing a persona, or adding one for a new step, MUST NOT require changing the factory's code.
- **FR-047**: Each step record MUST show which persona carried the step out.

**The architect, and advisory steps**

- **FR-048**: After the tests pass, an architect persona MUST review the change for how well it will bear maintenance and change — repeated code, unclear boundaries between layers, the wrong tool for the job — and state its suggestions and warnings.
- **FR-049**: The architect's suggestions and warnings MUST be recorded as a backlog in the target codebase's documentation and on the run's record. They MUST NOT, by themselves, fail the run.
- **FR-050**: A step MAY be marked advisory. When an advisory step fails — its reply is malformed, it times out, the agent program fails — the run MUST carry on and the failure MUST be recorded. An advisory step that changes what it may not is still undone and still stops the run.

**Spec kit, where the target uses it**

- **FR-051**: When the target codebase has spec kit set up, the planner MUST produce the plan as spec kit's specification and plan documents in the target, following the target's own spec kit instructions. The factory's code, not the agent, MUST run spec kit's scripts; no agent is given a shell for it.
- **FR-052**: A target codebase without spec kit MUST run exactly as it did before: the planner changes nothing, and the plan is the text it returns.
- **FR-053**: When spec kit is in use the planner MAY write only under the target's specification folder. Sending a plan back MUST revise the same documents, not start new ones.

### Key Entities

- **Persona**: who carries out an agent step. Has a name and a written description. One persona may serve more than one step.

- **Request**: the operator's written description of a wanted change, and the target codebase it applies to.
- **Run**: one attempt to carry out a request. Has a current state (waiting on plan, in progress, ended), an outcome once ended, a reason, and the ideals in effect.
- **Plan**: the written proposal for carrying out a request. A run may have several versions, each with the operator's comment that prompted the next.
- **Step record**: one execution of one step: which persona carried it out, what it was asked, what it produced, when it started, how long it took, which checks ran and whether they passed, and which attempt it was.
- **Check**: a deterministic verification applied to a step's result (for example "the new tests fail", "all tests pass").
- **Outcome**: accepted, rejected, or needs-me, with a reason.
- **Ideals**: the operator's standing principles, as written by the operator.
- **Target codebase**: the codebase a run changes. The first one is the observability app.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Starting from an empty target codebase, the operator obtains a working hello-world observability app by writing one request and approving one plan, with no other input.
- **SC-002**: Between approving a plan and receiving the notification, the operator is asked for nothing in 100% of runs.
- **SC-003**: 100% of runs end in exactly one of accepted, rejected or needs-me, each with a reason the operator can read without opening anything else.
- **SC-004**: For any accepted run, the operator can show that the run's new tests failed before the change and pass after it, using only the run's record.
- **SC-005**: The operator can find out what a run in progress is doing in under 10 seconds.
- **SC-006**: For any finished run, 100% of its steps can be read back with their instruction, output, duration and check result.
- **SC-007**: The operator can read the factory's entire own source in one sitting of under 60 minutes.
- **SC-008**: Following only the documentation, the operator can add a new step and see it in the next run's record in under 30 minutes, without changing any existing step.
- **SC-009**: A result that breaks a stated ideal is never reported as accepted; the review names the broken ideal.
- **SC-010**: After any run, including interrupted and failed ones, the factory's own workings, its recorded runs and the operator's ideals are unchanged, and nothing started by the run is still running.
- **SC-011**: At least three consecutive requests against the observability app complete through the same cycle, showing the cycle is repeatable and not a one-off.
- **SC-012**: In 100% of accepted runs, the tests and the change were produced by different personas, the record names the persona for every agent step, and the tests cover at least one stated edge or failure case.

## Assumptions

- **One operator, one machine.** There are no accounts, sharing or remote access.
- **Meaning of the three outcomes.** *Accepted*: tests pass and the review found the result matches the request, the plan and the ideals. *Rejected*: the review found a mismatch, or the operator abandoned the request at the plan. *Needs-me*: the factory could not finish on its own (attempt limit reached, time limit exceeded, a step changed something it should not, interruption, or usage limit reached). This split was inferred from the description; the operator confirmed it, and the other assumptions here, on 2026-11-18.
- **A rejecting review ends the run.** A review that finds a mismatch ends the run as rejected; it does not send the work back for another build attempt. Only failing tests cause rework. This keeps the proof of concept to a single rework loop.
- **No resuming.** A run that ends as needs-me or rejected is not resumed. The operator submits a new request, optionally referring to the earlier run. Resuming is left for a later stage.
- **Attempt limit.** An attempt is one execution of a step, whatever caused it. No step runs more than the limit in one run. The limit defaults to three, can be set when making a request, and is shown on the run. Sending a plan back with a comment is the operator's decision and does not count.
- **What is and is not contained.** Agent steps have no shell and are confined to the run's checkout. The test command, however, executes code and tests that an agent wrote, with the operator's permissions; nothing in this stage limits what that code does. Whether an agent can be stopped from *reading* files outside its checkout depends on the agent program and is established by the first task; the result is stated in the README. Sandboxing is next stage.
- **Notification reaches the operator at this machine.** Reaching a phone or another device is not required.
- **"Kept separate" means not merged.** The operator takes a run's changes into their own working version by hand. The factory does not do this for them.
- **Documentation step.** "Documents what it changed" means a written account stored with the run and with the change; it does not mean maintaining user-facing manuals for the target codebase.
- **The ideals are free text.** The factory does not interpret them mechanically; the plan and review steps read them as written.
- **The existing subscription has enough usage** for small runs. The factory does not manage or predict usage.
- **The technical choices** discussed during brainstorming (language, how agents are started, how runs are stored, how notification is delivered) are deliberately left to the planning phase and recorded in `docs/brainstorm-2026-11-18.md`, Part 2.

## Out of Scope (next stage, if this proof of concept succeeds)

- Working with a pay-per-use key as well as the subscription
- Choosing which model each step uses
- Running several requests at once
- Isolation or sandboxing beyond keeping a run's changes separate
- Scheduled or triggered runs
- Models from other vendors
- Using spec kit's own steps (specify, plan, tasks, converge) as the cycle. The operator added on 2026-11-18 that each persona and prompt should instruct its agent to use the corresponding spec kit command as part of its responsibilities; today none does. See research.md, R20.
- Resuming a stopped run
- **An expert panel before the plan, and a factory shaped per project.** Raised by the operator on 2026-11-18. See research.md, R23.
- **The architect taking part in planning.** The operator said on 2026-11-18 that the architect "may also be useful in planning". As built it reviews after the tests pass; having it advise the planner is left for later. See research.md, R21.
- **Reworking the repo layer** (`factory/store.py`). Raised by the operator on 2026-11-18 after reading the source: his only concern with the code as built, deliberately left for later. See research.md, R19.
- Sending rejected work back for rework automatically
