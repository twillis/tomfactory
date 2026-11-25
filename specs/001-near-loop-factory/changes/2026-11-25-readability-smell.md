# Change record: a readability smell in place of the line count (2026-11-25)

Made outside spec kit, for spec kit to review later. Built as FR-148 and FR-149, amending FR-039 and SC-007.

**Asked for by the operator.** The line-count test on the factory's own code (`tests/test_size.py`, FR-039) failed
the suite when `factory/*.py` passed a number of non-blank lines. It was raised four times in two days and stopped
nothing. His ideals put readability first ("Code a competent newcomer can read top to bottom and follow without
executing it in their head"); least code was retired on 2026-11-21 for producing terse code. He asked "why not a
readability check?" and agreed to retire the count for a readability smell. With the orchestrator, after: cognitive
complexity (SonarSource's measure) first, 15 as the starting limit, per codebase; a flag, never a gate; given to the
architect to judge, and a confirmed one becomes a backlog entry.

**Changed**

1. **`factory/config.py`**: three settings, `readability_command` (run after each step that writes code; `""`, the
   default, measures nothing), `readability_report` (the JSON it writes) and `readability_limit` (15); and
   `readability_argv`, as for the other commands. `factory init-target` writes them, commented, like every setting.
2. **`factory/checks.py`**: the `readable` smell and its two parts. `readability_scores` reads the report:
   complexipy's JSON, a list of functions each with `path`, `function_name`, `complexity`, `line_start` and
   `line_end`; anything else is no report. `changed_over` keeps the functions over the limit that hold a line the step
   added. The smell runs the command contained, with `_contained`, as the tests and the probe are (the codebase's
   `tools`, no network), removes the report before and after (so it is never committed and an old one never counts),
   and names each as `file:function (score)`. A report it cannot read is said, as a smell, not passed as clean.
3. **`factory/workspace.py`**: `added_lines(name)`, the line numbers a file gained since the last commit, taken out of
   `long_lines_added`, which now uses it: the line-length smell and the readability smell ask the same question.
4. **`factory/tables.py`**: `readable` among the smells of the two steps that write code, the build (and so spec
   kit's and the sprint's, which reuse it) and the code tidy. The architect is given the new `readability` input.
5. **`factory/driver.py`**: the `readability` input (FR-149): the latest `readable` finding of each step that
   measured it, so a step sent back and done again is told once; or a sentence saying none scored over the limit.
6. **`prompts/architecture_review.md`**: a section giving the architect those functions, telling it a score is a flag
   not a verdict (a flat dispatch can score high and read fine; a dense one-liner can score low and read badly), and
   to make each it finds hard to follow a backlog entry: the file, the function, what makes it hard to read.
7. **`README.md`**: "Readability: functions hard to follow, flagged for the architect", with the settings, what is
   reported and why a low score does not mean readable; the smells list names coverage and readability; `uv sync`
   says it installs complexipy.
8. **`specs/001-near-loop-factory/spec.md`**: FR-039 and SC-007 amended (what is measured and reported in place of a
   line limit, never a reason to fail); FR-148 and FR-149 added.
9. **`pyproject.toml`, `uv.lock`**: `complexipy` in the dev group only. The factory itself stays standard library.
10. **`tests/test_size.py`** removed, and **`tests/test_own_code.py`** in its place (FR-039): it scores `factory/`
    with complexipy, reads the report with the factory's own `readability_scores`, and reports the non-blank lines
    and the functions over 15 as a warning in pytest's summary. It never fails for them; it fails only if the
    measure cannot be read, so it tests the reader against complexipy's real output, which the cycle tests' stand-in
    cannot. It is skipped where complexipy is not installed.
11. **`tests/test_readability.py`**: the tests for FR-148 and FR-149, written first and seen to fail.
12. **`tests/test_overrides.py`**: the build's smells now include `readable`, so the expected list after an
    override that adds two smells names it too.

**Decided in the build, for the operator to confirm**

- **A non-failing test, not none.** The factory's own figures are seen in every run of its suite, as a warning
  line in pytest's summary, which is where the operator already looks; and the test is the one place the reader meets
  complexipy's real output. A test that only printed would be pointless; this one fails if the measure breaks.
- **Cyclomatic complexity left out.** Ruff's C901 and pylint's branch, return and statement counts would be a second
  tool and a second format, and they score a flat dispatch (`workflow.next_step`, 18 returns) as high as a tangle,
  which is the false alarm the architect would then have to dismiss. Nesting depth and length are what cognitive
  complexity already weighs. Added later, it is a second reader beside `readability_scores`, not a change to it.
- **One report shape, complexipy's.** As coverage is read as coverage.py's JSON and failures as JUnit XML. Another
  language's tool is used by putting its output in that shape (five keys per function).
- **"Changed" means holding a line the step added**, from git, as the line-length smell decides it; a function whose
  only change is a deleted line is not reported. The step is the unit, as for the other smells; the architect is
  given the latest finding per step.
- **The limit is the codebase's, 15 by default**, SonarSource's own starting point. On the factory 15 of 395
  functions are over it; on bttr_erp 9 of 594.

The suite: 717 passed before, 738 after (the line-count test gone, the own-code test in its place, and 21 new,
counting each parametrised case), with one warning: the factory's own figures.
