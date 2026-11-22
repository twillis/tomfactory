# Change record: an agent may ask for a measurement (2026-11-22)

Made outside spec kit, for spec kit to review later.

**Found on bttr_erp's runs 53 to 57.** No agent can run anything, by design. So a planner wrote
"from reading, not measured" about a PostgreSQL cast, a plan check judged Django's cast "from memory",
a planner could not tell which PostgreSQL the tests run on or whether an extension was installed, and
each time the orchestrator measured it on a scratch database after the plan was written and sent the
plan back with the result. That is a whole plan and plan check spent to carry a fact that was one
query away. The retro of run 57 proposed giving the planner a database session. The operator proposed
the smaller thing, 2026-11-22: "If the test writer needs access to something that it can't get to,
why not stop right then and ask you the orchestrator to run a command on its behalf and give it the
results?" And, on the plan for it: "Yeah that sounds like a good plan after this run".

**Changed**

- **FR-100, `workflow.py`.** A reply that is only `{"measure": "..."}` is a question (`question_in`),
  and `asks_to_measure` says it is that kind. `Ask` carries `measure`. It is bounded as a question
  is: a step that has used its attempts and still asks ends the run needs-me.
- **`driver.py`.** A measurement is not put to the lead, who answers from documents and would spend
  a step concluding it cannot run a database. The run waits and the notification is "a measurement
  is asked for". The check on the step's record is named `measure`. `factory answer` is unchanged:
  the step that asked runs again with the answer among its earlier answers.
- **`prompts/fragments/asking.md`.** Every agent that may ask is told it can run nothing, that it
  may ask for a measurement in place of writing "not measured", to ask for everything in one
  request and as early as it can, and that each request uses one of its attempts.
- **`orchestrator/playbook.md`.** A measurement is the orchestrator's to answer, not the operator's:
  on a scratch system, with a command it writes itself from what is asked (the agent's words say
  what to find out and are never pasted and run), changing nothing outside the scratch system,
  answering only what it saw and on which version, and telling the operator afterwards. What is
  really a decision goes to him.
- `README.md` and `spec.md` say so.

**What holds it.** No agent gains a way to run anything; containment is as it was. The person or
orchestrator who answers chooses what is run.

**What it costs.** The step that asked runs again from the start, with the answer: about a minute for
the test writer, up to six for the planner, against a send-back after the plan check, which runs the
planner and the check again. Each request uses one of the step's attempts.

**Not taken.** A shell or a database session for an agent (run 57's retro): it would save the
round trip and is a change to containment, which this is not. Handing the plan check's findings to
the planner without the operator (run 57's retro, and three before it): still open.

Tests: `tests/test_questions.py::test_asking_for_a_measurement_is_a_question_that_the_lead_is_not_asked`,
`::test_a_measurement_comes_straight_to_whoever_drives_the_run_and_its_answer_goes_back`,
`::test_every_agent_is_told_it_may_ask_for_a_measurement_and_the_orchestrator_how_to_answer` (FR-100),
all of which failed before the change. The whole suite: see the count in `README.md`.
