# Task: merge the questions that ask for the same decision

Several agents in a planning dialogue have each asked the asker their own questions this round. The asker answers
them from a phone, one at a time. Where two agents ask for the same decision, in other words, the asker should
answer it once, and the answer goes back to both.

## The questions waiting, each with its number and who asked it

{{to_merge}}

## What to do

Find the questions, from different agents, that ask for the same decision. The test: once the asker has answered
one of them, would they have nothing left to decide in the other? Then they are one question; merge them.

Judge what is being decided, not how it is put. Agents word the same choice their own way: their options come in a
different order, under different letters, with their own examples and recommendations, and one may offer an option
the others leave out ("required only on a removal" beside "required only when the past is rewritten"). None of that
makes it a different decision. Three agents asking whether a change must give a reason, each with its own list of
answers, are asking one thing.

Leave apart two questions on the same subject where answering one leaves the other open: "may an end date also be
moved later?" and "must a moved date be marked as a correction?" are both about correcting dates, and answering
either still leaves the other to decide. A question for a measurement merges only with another for a measurement.
Change no file.

Put first in each group the question the asker should see: the one whose options cover the others' (every choice
any of them offers), or, where none does, the clearest. Each agent reads that question with its answer, so an
answer given under its letters is understood.

In your reply's JSON object:

- `merged`: a list of groups, each group a list of its questions' numbers, the one the asker sees first:
  `[["Q3", "Q5"]]` for one group, `[["Q3", "Q5"], ["Q4", "Q7", "Q9"]]` for two. Empty, `[]`, if no two ask for the
  same decision.
