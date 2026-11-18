# Task: write the specification

Turn the request below into a specification, following spec kit's specify instructions.
Read the codebase in the current directory first.

## The request

{{request}}

## The rules this work is held to, in order of precedence

When two of these disagree, the earlier one wins. Say plainly where that happens.

### 1. This codebase's own constitution

{{constitution}}

### 2. The operator's ideals

{{ideals}}

### 3. Spec kit's own instructions, where any are given further down

These come last. Follow them where they do not conflict with the two above.

## If the specification was sent back, or this is a return to planning

The operator's comment, if there was one:

{{comment}}

What was found that changes the requirement, or what was wrong with your last reply, if anything:

{{failure}}

If either is given, revise the existing specification in place. Do not start a new one.

## Spec kit, if this codebase uses it

{{speckit_instructions}}

### What the factory has set up

{{speckit_context}}

If both of those say (none), this codebase does not use spec kit: ignore this section.

## What to produce

The specification document, at the path the factory has set up.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "summary": "what the specification says, in two or three sentences",
  "assumptions": ["each assumption you made where the request was silent; empty if none"]
}
```
