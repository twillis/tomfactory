# Quickstart: Proving the Factory Works

**Date**: 2026-11-18 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

These scenarios are how the finished factory is shown to work. Each one names the success criteria it proves. Command details are in [contracts/cli.md](contracts/cli.md); step order and rules are in [contracts/workflow.md](contracts/workflow.md).

Scenarios 1 and 6 use no subscription usage. Scenarios 2 to 5 and 7 run real agents.

## Prerequisites

- Python 3.13, `uv`, `git`, and the `claude` command signed in to the operator's subscription.
- A desktop session, for notifications.
- From the factory's repository: `uv sync`.

## Scenario 1 — The factory's own tests pass without an agent

```bash
uv run pytest
```

**Expect**: every test passes, with the real agent program never started. The tests drive the whole workflow through the fake agent, including: a plan sent back and revised, tests that fail to fail, a build that needs two attempts, a build that exhausts its attempts, a rejecting review, a step that times out, a step that edits a forbidden file, a test writer that states no edge cases, and an interrupted driver.

Then:

```bash
uv run python scripts/traceability.py
```

**Expect**: it lists nothing: every requirement in the spec is named by a test.

**Proves**: FR-041 (nothing but the adapter depends on the agent), SC-003, SC-010, the size limit behind SC-007 through the line-count test, and constitution S8.

## Scenario 2 — The machine is ready

```bash
uv run python -m factory doctor
```

**Expect**: each line reports ready — git, the agent command answering a one-line prompt on the subscription, the notification command, and a writable home directory.

## Scenario 3 — Hello world, end to end

```bash
uv run python -m factory init-target ../tomfactory-viewer
uv run python -m factory request "Create a hello-world observability app: a page I can open in a browser that says hello and shows how many runs the factory has recorded." --target ../tomfactory-viewer
```

**Expect**: the command returns at once with a run id. Within a few minutes a "plan ready" notification appears.

```bash
uv run python -m factory plan
uv run python -m factory approve
```

**Expect**: `approve` returns at once. Leave the machine alone. A "run ended" notification appears with the outcome.

```bash
uv run python -m factory show
```

**Expect**: outcome `accepted` with a reason; steps in order `plan`, `baseline`, `write_tests`, `red`, `build`, `test`, `architecture_review`, `document`, `review`, `finish`; the `red` step shows failing tests and the `test` step shows the same tests passing; every agent step names its persona, with the test writer and the code writer on different steps; the `write_tests` step lists the edge cases it considered; a branch name is printed. Checking out that branch in `../tomfactory-viewer` and following its documentation starts an app that shows the hello page.

**Proves**: SC-001, SC-002, SC-003, SC-004, SC-006, SC-012.

## Scenario 4 — Watching and sending a plan back

```bash
uv run python -m factory request "Show the most recent run's outcome and reason on the page." --target ../tomfactory-viewer
uv run python -m factory status
```

**Expect**: `status` answers in well under ten seconds, showing the run in `planning` with the current step and how long it has been running.

```bash
uv run python -m factory revise "Also show when the run ended."
uv run python -m factory plan
```

**Expect**: a second plan version that mentions the end time. `factory show` lists both versions and the comment.

```bash
uv run python -m factory approve
uv run python -m factory watch
```

**Expect**: events print as they are recorded — tool calls by name, checks with pass or fail — until the run ends.

**Proves**: SC-005, SC-006, and the second of the three consecutive requests for SC-011. A third request of the operator's choosing completes SC-011.

## Scenario 5 — Ideals are enforced

```bash
uv run python -m factory ideals --edit
```

Add one ideal, for example: *"The page's wording lives in one place, separate from the code that reads the run store."*

```bash
uv run python -m factory request "Add a line to the page showing the number of accepted runs." --target ../tomfactory-viewer
uv run python -m factory plan
```

**Expect**: the plan states how it follows the ideal. After approval, `factory show` lists the ideal as in effect for the run, and the review step's output addresses it by name. If the result breaks the ideal, the outcome is `rejected` and the reason names it.

**Proves**: SC-009, FR-021 to FR-024.

## Scenario 6 — Adding a step

Follow the README section "Adding a step" to add a trivial code step (for example one that records the number of files in the checkout) after `test`. Then follow "Adding a persona" to add a new persona file and name it on an agent step.

```bash
uv run pytest
```

**Expect**: the tests pass, and — as `tests/test_extending.py` shows without editing any file — the new step and the new persona appear in the fake-agent run's record, with no existing step edited and no change to `store.py` or `cli.py`. The operator, doing this by hand from the README, completes it in under thirty minutes (task T063).

**Proves**: SC-008, FR-037, FR-046.

## Scenario 7 — Nothing is left behind

During any real run:

```bash
uv run python -m factory stop
```

**Expect**: the command returns once everything has stopped; `factory status` shows the run ended as `needs-me`, "stopped by operator"; no agent or test process started by the run is still alive; the factory's own files and `ideals.md` are unchanged; `factory show` still displays every step recorded before the stop.

**Proves**: SC-010, FR-014, FR-029.

## Results

### The operator's reading (task T063, SC-007) — 2026-11-18

The operator skimmed the factory's whole source in about 30 minutes, against a target of under 60. SC-007 is met. His one concern was the repo layer, deferred; see research.md, R19.

SC-008 (adding a step by hand from the README in under 30 minutes) has not been timed by the operator. `tests/test_extending.py` shows the mechanics work.

### Real runs — 2026-11-18

All through the command line, on the operator's subscription, against `src/tomfactory-viewer` with the home at `~/.tomfactory`. Costs are the agent program's own estimates. A trial run in a temporary home came first and is described under "What the real runs changed".

| Run | Request | Outcome | Time | Est. cost | Notes |
|-----|---------|---------|------|-----------|-------|
| 1 | Hello-world observability app | **accepted** | 3m 37s | $2.06 | 51 tests from 36 stated edge cases; failed first; code writer passed them on its first attempt. Merged into the viewer's main line. |
| 2 | Show the latest run's outcome and reason; plan sent back once to add the end time | **rejected** | 5m 38s | $3.06 | 134 tests passed. The reviewer rejected for a real defect (one failing query hid the requested values) and, wrongly, for the end time, which the operator had asked for in a comment the reviewer could not see. Not merged. |
| 3 | The same request again, after the fixes, with the architect step | **needs-me** (wrongly) | 5m 24s | $2.96 | Every step in fact succeeded: 123 tests passed, the architect gave three suggestions and a warning, the documentation was written. The adapter misread the usage warning `allowed_warning` as a refusal and failed the architect and documenter steps. Fixed afterwards. Not merged. |
| 4 | Count of accepted runs, with an ideal stated | **needs-me** (wrongly) | 45s | $0.38 | Failed at the plan step for the same reason as run 3. |

**Scenario 2 (doctor)**: all four checks reported ok.

**Scenario 3 (hello world)**: passed as run 1. The viewer's main line holds `viewer.py`, `tests/test_viewer.py`, `docs/viewer.md` and `CHANGELOG.md`. Start it with `python viewer.py` in `src/tomfactory-viewer` and open `http://127.0.0.1:8000/`.

**Scenario 4 (watching, and sending a plan back)**: the plan was sent back and a second version produced in runs 2 and 3. `factory status` answered in 0.08 seconds (SC-005: under 10).

**Scenario 5 (ideals)**: not completed. Run 4 carried the ideal on its record but failed at the plan step through the adapter bug. The enforcement is covered by `tests/test_ideals.py`.

**Scenario 7 (stop)**: not run for real; covered against real detached processes by `tests/test_detached.py`.

**SC-011 (three consecutive real requests through the same cycle)**: **not met as written.** Runs 1 and 2 went through the whole cycle to a genuine outcome. Runs 3 and 4 were cut short by the factory's own bug. No further real runs were made because the operator's five-hour usage window had reached 91%.

**The live hello-world test** (`tests/test_live.py::test_a_real_hello_world_request_runs_to_accepted`) was written but not run, for the same reason. The two shorter live tests pass.

### What the real runs changed

Five things were found only by running the factory for real, and each was fixed test-first:

1. **A home under `~/.claude/` cannot work.** The agent program treats files there as sensitive and refuses to edit them. (A mistake in the trial set-up, but worth knowing.)
2. **A refused edit inside the checkout was retried three times.** It now ends the run at once: trying again cannot help.
3. **The reviewer ran before the documentation existed**, and rejected a correct change for having none. Documentation now comes before review.
4. **The reviewer could not see the operator's plan-stage comments**, and called the operator's own instruction scope creep. Later steps now see the request with those comments. The operator has questioned this fix; see research.md R22.
5. **A usage warning was read as a refusal.** `allowed_warning` now counts as allowed.

### The architect's first real review (run 3)

> The change does what the plan asked in a small, readable way; its maintenance costs are a duplicated database-access block, a positional tuple that carries a domain rule into the renderer, and two separate reads per request that can disagree.

Three suggestions (one shared read-only query helper; a named type in place of a bare tuple; one test helper in place of two near-copies) and one warning (the count and the latest run are read over two connections and can disagree). Because of the adapter bug these did not reach `docs/backlog.md` on a branch; they are on the run's record: `factory show 3`, then `factory show 3 --step 26`.

### After the store became a gateway — 2026-11-18

| Run | Request | Outcome | Time | Est. cost | Notes |
|-----|---------|---------|------|-----------|-------|
| 5 | Show the latest run's outcome and reason | **accepted** | 5m 18s | $3.14 | First real run on the gateway, with the architect and an ideal stated. 118 tests passed. Four commits on the branch: tests, change, backlog, documentation. Merged into the viewer's main line. |

The architect wrote `docs/backlog.md` in the viewer: two warnings and three suggestions, each naming the file, the change, and the ideal it touches. The reviewer accepted, citing the request, the plan and the layering ideal.

Real runs so far: 1 accepted, 2 rejected, 3 and 4 wrongly failed (bug since fixed), 5 accepted. SC-011, three consecutive real requests through the same cycle, is still not met as written.
