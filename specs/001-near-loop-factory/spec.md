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

- **FR-054**: Where the target codebase has its own constitution, every agent step that is given the operator's ideals MUST also be given that constitution, and MUST be told the order of precedence: the target codebase's constitution first, then the operator's ideals, then spec kit's own instructions. An unfilled constitution template counts as none.

**A cycle that follows spec kit's stages** (where the target uses spec kit)

- **FR-055**: The steps a run goes through MUST be chosen by the target codebase: one that uses spec kit follows spec kit's stages, and one that does not runs the plain cycle unchanged.
- **FR-056**: Each spec kit stage that is part of a run MUST be carried out by a persona following that stage's own instructions: specify and clarify by an analyst, plan and tasks by the planner, analyze and checklist by the reviewer, implement by the test writer and the code writer, converge by the reviewer.
- **FR-057**: A run MUST be able to wait for the operator more than once. On a spec kit target it MUST wait once, for approval of the specification, plan and tasks together, with the analyze step's findings shown as notes; sending the work back MUST return the run to the plan. *(Amended 2026-11-20: one approval, not two. See `changes/2026-11-20-one-approval-then-a-sprint.md`.)*
- **FR-058**: After the build, the factory MUST assess every difference between what was built and the approved documents as one of: unbuilt work, an implementation detail, or a change to the requirement.
- **FR-059**: Unbuilt work MUST return the run to the build once; found again, it MUST be recorded as a deviation and the run MUST end accepted. An implementation detail, a change to the requirement and a broken ideal MUST each be recorded and MUST NOT stop the run or return it to planning. *(Amended 2026-11-20: after approval nothing returns to planning.)*
- **FR-060**: When a run returns to planning, what it had built MUST be set aside where the operator can find it, and the build MUST start again from the newly approved documents, so that tests are again written and seen to fail before the code.

**Questions**

- **FR-061**: An agent step MUST be able to ask a question instead of finishing, when it cannot proceed without an answer that the documents do not give.
- **FR-062**: A question MUST go first to a lead persona, which answers from the request, the approved documents, the codebase's constitution and the operator's ideals. When the lead answers, the step that asked MUST run again with the answer.
- **FR-063**: When the lead cannot answer, the run MUST wait for the operator, who MUST be notified of the question. When the operator answers, the step that asked MUST run again with that answer. A run MUST NOT be approved past a question that is still waiting.
- **FR-064**: Every question, who asked it, the answer, and who answered MUST be recorded and shown with the run.
- **FR-100**: An agent step MUST be able to ask, instead of finishing, for a fact only a running system can give. Such a request MUST NOT go to the lead, who answers from documents: the run waits, whoever drives it is notified with what is to be measured, and the step that asked runs again with the answer. It is recorded and bounded as a question is. No agent is given a way to run anything. *(Added 2026-11-22: on bttr_erp's runs 53 to 57 a planner wrote "from reading, not measured", a plan check judged a cast from memory, and the orchestrator measured on PostgreSQL after the fact and sent the plan back, five times in five runs. The operator: "If the test writer needs access to something that it can't get to, why not stop right then and ask you the orchestrator to run a command on its behalf and give it the results?")*

**Keeping tests proportionate, and tidying**

- **FR-065**: The tests a run adds MUST be proportionate to the change. The test-writer persona MUST be directed to test each behaviour once, at the level where it lives, and the factory MUST measure the tests a run adds against a budget the target codebase sets and report a set over it, saying how large it was and what the budget is, as a smell (FR-107).
- **FR-066**: The operator MUST be able to request a change that must not alter behaviour — tidying the tests, or tidying the code — without the factory demanding new failing tests. In such a run the existing tests MUST pass before and after; tidying the tests MUST NOT change the code, and tidying the code MUST NOT change the tests. The planner and the reviewer MUST be told which kind of run it is and what it holds still, so that a plan never asks for what the run may not change. *(Added 2026-11-19 after run 15, whose planner planned new tests in a tidy of the code.)*

**The plan travels with the code**

- **FR-079**: When the operator approves a plan that no spec kit stage wrote, the factory MUST commit it to the run's branch, in the run's record `docs/runs/<run>-<name>.md`, before the run carries on: the request as amended by any comments it was sent back with, the plan, how it follows the ideals, and its conflicts. Where spec kit wrote the documents, they are already committed. *(Added 2026-11-19 after publishing the viewer, whose plans had stayed in the factory's local database.)*
- **FR-080**: When a run ends, whatever its outcome, and its checkout still exists, the factory MUST complete the run's record and commit it to the run's branch: what FR-079 records, then each step and how it went, the outcome and its reason, the review's verdict and reasons, and the commits the run made. That commit MUST hold the record and nothing else. *(Added 2026-11-19: "once a run is completed it should be exported and put into the runs directory".)*

**More than one person on a codebase**

- **FR-081**: What a run leaves in the codebase MUST NOT be named by a counter kept on one machine. A run's branch and its record are named from the time the run was requested and the first words of the request, so runs made on different machines do not collide. The run's number remains each operator's own handle for commands. *(Added 2026-11-19: "you would have to identify the runs some other way so they don't clash".)*
- **FR-087**: A spec kit feature folder MUST NOT be numbered by counting the folders one checkout can see. It carries the name of the run's branch (FR-081), so two people specifying at the same time make two folders. *(Added 2026-11-20: "change the run file name template to a timestamp instead of a counter so that if multiple people work on the repo there wont be any clashes". Branches and run records already were; the feature folder, `specs/001-…`, was the counter left.)*
- **FR-088**: Each agent step MUST be given a model of the grade its entry names, and never the agent program's own default. There are two grades. The steps that judge a change, the architect's review and the final review, get the strongest; every other step gets the standard one. Which model each grade is MUST be stated in the one place that knows the agent program (FR-041). *(Added 2026-11-20: every step had been running on the costliest model, by default and unnoticed. The operator: "Fable for the orchestrator which is you and for the architect which reviews at the end but everything else should probably be opus", then "the final review should be Fable as well".)* *(Amended 2026-11-23 by FR-109: four grades; the judges run on the standard grade, the summarising steps on the light one, and no step starts on the strongest.)*
- **FR-089**: New tests that cannot be read as code MUST NOT count as tests that fail first. Before the new tests are run to see them fail, the factory MUST run the codebase's own command for "can these be read", contained, and where it fails the step MUST fail with what the command said, which returns the work to the test writer. A codebase MAY change that command or switch it off in its committed settings. *(Added 2026-11-20: run 22's test writer wrote one line with a syntax error; the file could not be loaded, which counted as failing, and the builder, who may not touch tests, used all three attempts on tests that could never run.)*
- **FR-090**: When a spec kit run ends, its record MUST end with a sprint review: the unbuilt work, implementation details, proposed requirement changes and broken ideals the final review found, and the architect's warnings and suggestions, so the operator can decide at merge which become the next request. *(Added 2026-11-20: "What if after the speckit plan the run (sprint) goes largely auto where deviations to the plan are noted and addressed at the end.")*
- **FR-091**: A spec kit run MUST end with a retro, after the final review: an advisory step, which never stops the run, written by a facilitator from what the factory measured, every agent's own notes on what made its step harder, the operator's comments in his own words, and the final review's and the architect's findings. It says what worked, what did not, the opportunities and the threats, for the factory and not for the product, and is committed as `docs/retros/<run>.md`. *(Added 2026-11-21: "Should be a retro at the end for the team of agents to publish. Basically what worked, what didn't and opportunities and threats ... all of that can be used to improve the factory.")*
- **FR-092**: Every agent step MAY say, in its reply, what made its step harder. A run's record MUST hold its time and cost, measured by the factory's code and never by an agent: each step's minutes, cost and outcome, the totals, and the time spent waiting for the operator. *(Added 2026-11-21: "I like that I can get time breakdowns as well.")*
- **FR-093**: A codebase MAY choose, in its committed settings, a sprint cycle in place of spec kit's, even where spec kit is set up: one plan by the planner from the codebase's standing documents, one approval, then the build to the end, a final review that sends unbuilt work back once and records everything else, the sprint review and the retro. *(Added 2026-11-21. The operator: "we are bulding an erp, thats not small and spec kit isnt working for it, what would it work for lol". On bttr_erp the specification already exists, in `requirements/`, and spec kit re-derived one from a paragraph every run.)*
- **FR-094**: A step run again after the agent program failed MUST be told the cause the program gave. The architect and the final review MUST be given the test run before the build as well as after it. Resuming a run MUST write its record again, so no step reads a record frozen at the stop. *(Added 2026-11-21, from the first retro's opportunities.)*
- **FR-095**: A sprint's plan MUST be checked before the operator is asked to approve it, by a reviewer that changes nothing and is not a gate; what the operator approves MUST show the planner's plan and the check's findings together. Every run's record MUST hold what the new tests said before the build and what the tests said after it, written by the factory's code. The planner MUST name each place its design differs from what it carries over, and plan a test for every refusal the build will make. *(Added 2026-11-21. The operator: "yeah a plan check should happen for future sprints". Run 28's retro: the red and green output had been missing from four records in a row.)*
- **FR-096**: A test run's output, where it is too long to keep whole, MUST be cut by keeping its beginning and its end and saying how much was left out. The planner MUST write new queries in the form the code will use and MUST NOT predict which tests fail first; when a plan-check finding allows more than one fix, the check MUST name the one to take. *(Added 2026-11-21, from run 30's retro.)*
- **FR-097**: A builder that finds a test no build can pass MUST be able to say so in its reply, and the factory MUST then ask the test writer, once in a run, to mend that test, changing tests only, and run the tests again without first requiring them to fail, since the build exists. The test writer MAY find the builder wrong and change nothing. A second such report in the same run MUST NOT be chased: the tests are run and their failure takes its usual course. The builder still may not change a test. *(Added 2026-11-22: on bttr_erp's runs 43 and 56 the build was right and one new test was wrong, a seed that left out a user and a file number the plan miscounted; the builder said so on its second attempt and still spent its third, and each run ended needs-me for a one-line fix made by hand.)*
- **FR-098**: The plan check MUST be asked to work out each expected value of a planned test from that test's own setup, to look for a string that will be read as a regular expression, to name every kind of input a rule covers where the plan shows one, and to follow the remedy a refusal offers. The test writer MUST be told it cannot run the tests and that the factory's next step does. *(Added 2026-11-22, from the retros of bttr_erp's runs 53 to 56: a file number vouched for by comparison with another row, `(3)` handed to pytest's `match=`, a cast rule measured for VARCHAR and wrong for CHAR, a refusal whose remedy led to the loss it prevented, and four retros in which the test writer said it had no shell.)*
- **FR-099**: The diff given to a step MUST leave out the run's own record, which repeats the request and the plan that step is already given. The retro MUST be given the codebase's constitution and the ideals. The planner and the plan check MUST be told where each later step may write, and the planner MUST give no step a file it may not write. The architect MUST move a backlog entry that has been answered out of the backlog. *(Added 2026-11-22, from the retros of bttr_erp's runs 52 to 56: the architect and the final review were given the plan twice; a retro could not see that a parity ideal had been followed against the constitution; plans gave the documenter a requirements row and a changelog that did not exist; and a backlog of some two hundred long entries could no longer be searched.)*
- **FR-101**: A codebase MAY set, in its committed settings, the longest line a step may add to its code or tests. Where it does, the factory's code MUST measure the lines each writing step added, counting indentation, and report each line that is over as a smell (FR-107), naming it; documentation is not measured. *(Added 2026-11-22: on bttr_erp's run 60 the final review sent a finished build back through build, test, architect, documenter and review for five docstring lines over a width the request had asked for and nothing measured.)*
- **FR-102**: The plan check and the final review MUST be given every question asked in the run that has its answer, with who asked and who answered, and MUST be told that where the request and an answer disagree the answer stands. *(Added 2026-11-22: on bttr_erp's run 60 the planner asked for a measurement that corrected a fact in the request; the plan check, shown only the request, reported the corrected plan as contradicting it, and a revision was spent putting the facts into the plan's own text.)*
- **FR-103**: Every commit the factory makes on a run's branch MUST say in its subject what it holds, in at most 72 characters: the approved plan by its title, the tests, the build, the architect's backlog notes, the documentation and the retro each by the summary the step that wrote them gave, and the run's record by its outcome and the plan's title. Its body MUST name the run and its request, and carry the run and the step as trailers (`Factory-Run:`, `Factory-Step:`); the run record's body MUST give the outcome's reason, the review's reasons and the time and cost. *(Added 2026-11-22. The operator: "the commit messages suck, :) should be a summary of the run", "meaning the commits it produces as part of a run". Until then every subject was `factory: <step> (run <n>)`.)*
- **FR-104**: Where the plan check finds something, the planner MUST be given the findings and amend its plan once, taking each finding that is right and declining, with its reason, each that is not, before the operator is asked; the operator MUST be shown the amended plan, the findings, and what was taken and declined, and still decides. A plan whose code is longer than the codebase's line length MUST be written again before it is checked. The plan check MUST ask of each planned test what makes it fail before the build, of each new list or mapping what a table missing from it does, and whether every module docstring the plan's change touches stays true. A run's record MUST keep the documenter's account and say which check sent a step back. *(Added 2026-11-22, from the retros of bttr_erp's runs 58 to 63: on nearly every run the plan check passed with findings and the orchestrator sent the plan back by hand to say "take the findings as written"; a planned test that could not fail first, a new list with no fallback, a plan's code over the line length and a docstring made untrue each reached the build; the documenter's account was overwritten; a build sent back said only "check".)*
- **FR-105**: The attempts a step's limit counts MUST be its own failures: a run of a step that asked a question the operator answered, or a run before the operator's latest send-back, MUST NOT count toward its limit; a question the lead answered still counts, so a step that only asks still ends. *(Added 2026-11-22: on bttr_erp's run 68 the planner asked for a measurement once and was sent back once by the operator, and the plan's own line check then found one long line; the planner had used its three attempts and the run ended needs-me for a one-line wrap.)*
- **FR-106**: The plan check MUST look for a planned case that would still pass with the rule it names broken, its outcome coming from something else, and, where a plan rewords a phrase, for that phrase across the whole package. The test writer MUST NOT drop a case the plan lists: one that cannot show its rule is written so that it does where its intent is plain, and either way the summary says so. *(Added 2026-11-23: on bttr_erp's run 69 a planned case put a parent's key where a child's belonged, the plan check passed it, and the test writer dropped it, leaving the only case of its kind untested; and a phrase reworded in one package stayed in another.)*
- **FR-107**: A step entry MAY name smells, checks run after its own checks pass whose findings MUST be kept with the step and listed under "Smells" in the run's record, and MUST NOT fail the step, send work back or end the run. The line length (FR-101, and a plan's code under FR-104) and the test budget (FR-065) are smells. The final review MUST be told that a smell is not a reason to reject. *(Added 2026-11-23. The operator, 2026-11-23: "Maybe docstring limits should be smells that don't stop the build from now on. I'm beginning to think the same about the test lines count budget." And: "By build I mean run". On bttr_erp the line check had sent work back seven times and ended run 68 needs-me for one line; the budget had never fired; and the two tidy steps were not measured at all, so run 78's 147-character line was found by the final review.)*
- **FR-108**: A step's change MUST be everything it changed over its attempts in a row: work an attempt left before it asked a question, or before a check sent it back, MUST count as the step's own when the next attempt keeps it, and an answered question MUST NOT be shown to the next attempt as a failure. A step the run comes to from another one, or after the head has moved, counts only its own change. An agent that finds the database or a tool behaving against the plan (the planner amending, the builder, the test writer mending) MUST be directed to ask for a measurement rather than leave the finding in a comment or to the orchestrator, and the plan check MUST ask whether each measured answer measured the statement the plan sends. *(Added 2026-11-23: on bttr_erp's run 79 the test writer wrote its tests, asked for a measurement and, answered, kept them; each attempt counted only its own change, so `tests_added` failed it three times and the run ended needs-me. The same run's builder left a database finding in a test comment, and its plan had measured a cast it did not send. The operator: "the more that we can interrupt the process and recover from it and the cheaper we can make it the more agile we can be".)*
- **FR-109**: There MUST be four grades, weakest first: light, middle, standard and strongest. The documenter, the retro and the lead MUST start on light; every other agent step on standard; no step on strongest, which is the operator's to choose. Each earlier attempt of a step whose work was found wanting (a failed check, a reply of the wrong shape, a guard, or a later step sending the work back) MUST make the next attempt run one grade higher, up to standard and never past it unless the step starts higher; an attempt that ended in an error of the agent program, a timeout or a question MUST NOT, since a stronger model would not help. The operator: "I suppose the cause of the failure should be evaluated before escalating the model". The run record's time and cost MUST say which model each attempt ran on. *(Added 2026-11-23. The operator, shown a post that sends search to Haiku, building to Sonnet and review to Opus: "Sounds like we should setup something like this in the factory"; then "On failure tries bump up the model", and "we could measure starting next sprint 83. If we see failure we can bail". Runs 80 and 81 had every step pass first time, with the architect and the final review on the strongest model: $4.38 of $14.16.)*
- **FR-082**: A codebase MAY state its own ideals in a committed file, `IDEALS.md`. Where it does, every run on it is held to those, read from the commit the run starts at, in place of the operator's personal ideals; and no step may change that file except as the operator's own commit.

**Resuming**

- **FR-067**: The operator MUST be able to resume a run that ended as needs-me, from the step it stopped at. Everything the run committed before that step MUST be kept and not redone; anything the stopped step left uncommitted MUST be discarded; and the earlier ending MUST stay in the run's history. Resuming MUST be refused for a run that ended any other way, whose checkout no longer exists, or while another run is open.

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
