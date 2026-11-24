# Task: merge the questions that ask the same thing

Several agents in a planning dialogue have each asked the asker their own questions this round. The asker answers
them from a phone, one at a time. Where two agents ask the same thing, in other words, the asker should answer it
once, and the answer goes back to both.

## The questions waiting, each with its number and who asked it

{{to_merge}}

## What to do

Find the questions, from different agents, that ask the same thing: the same answer would answer each. Merge only
those. Two questions on the same subject that could be answered differently are not the same; leave them apart. A
question for a measurement merges only with another for a measurement. When in doubt, do not merge: a question
asked twice costs the asker a few seconds, one merged wrongly loses an answer. Change no file.

In your reply's JSON object:

- `merged`: each group of questions that ask the same thing, as a list of their numbers (`["Q3", "Q5"]`), the
  clearest of them first: that one is the question the asker sees. Empty if none ask the same thing.
