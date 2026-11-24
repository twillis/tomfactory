# Task: write the spike's findings

The factory has run the probe. Write what the spike found, as one note that a person reads top to
bottom, with the code in it. The operator: "I would like to see the code while reading the outcome
of the spike sort of like as a narrative".

## The question

{{request}}

## The plan

{{plan}}

## What the probe changed, on this run's branch ({{branch}})

{{diff}}

## How the factory ran the probe, and what it printed

{{probe_output}}

## Where the note goes

You may create or change files only under: {{docs_paths}}

Write one note, `docs/spikes/{{run_name}}.md`, and nothing else. In this order:

1. What was asked, and the guess.
2. In the order it happened, each thing that was tried: the probe's own lines that tried it,
   quoted in a fenced code block, and what it printed, quoted in a block fenced as `text`.
3. What surprised you.
4. What it would take to build properly.
5. What the spike did not find out.
6. That the whole probe is on the branch `{{branch}}`, which is kept and never merged.

The factory checks every quote. A code block must be whole lines of a file on the branch, exactly
as they are there (indentation may be shifted as a whole); to leave lines out, close the block and
open another. A `text` block must be exactly lines the probe printed, above. A quote that is not
there sends the note back.

## If your last note was sent back

{{failure}}

In your reply's JSON object:

- `summary`: what the spike found, in one sentence
- `outcome`: `answered` if the probe's output settles the question as the plan said it would;
  otherwise `inconclusive`
- `reason`: why, in a sentence, naming what the probe printed
