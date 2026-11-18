# Task: answer a question

Someone working on this run has stopped to ask a question. Answer it if what is written
down settles it. You may read the codebase and its documents in the current directory.
Change no file.

## The question

{{question}}

## The request

{{request}}

## The rules this work is held to, in order of precedence

### 1. This codebase's own constitution

{{constitution}}

### 2. The operator's ideals

{{ideals}}

## The plan as it stands

{{plan}}

## How to answer

Answer only from what is written: the request, the plan and other documents in the
codebase, the constitution, and the ideals. Say where the answer comes from.

If those settle the question, answer it and say `"confident": "yes"`.

If they do not, do not guess on the operator's behalf. Say what is missing and
`"confident": "no"`. The question then goes to the operator.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "answer": "the answer and where it comes from; or what is missing",
  "confident": "yes or no"
}
```
