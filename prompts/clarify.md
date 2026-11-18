# Task: clarify the specification

Find what the specification leaves unclear, following spec kit's clarify instructions, and
settle it in the specification itself.

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

## If your last reply was not accepted

{{failure}}

## Spec kit, if this codebase uses it

{{speckit_instructions}}

### What the factory has set up

{{speckit_context}}

If both of those say (none), this codebase does not use spec kit: ignore this section.

## What to produce

The specification, updated so that nothing important is left unclear. The operator reads
your summary to decide whether to approve the specification, so make it stand on its own.

End your reply with one JSON object, and nothing after it, in exactly this shape:

```json
{
  "plan": "a summary of the specification for the operator, naming the file it is in",
  "clarified": ["each thing that was unclear and how you settled it; empty if nothing was"]
}
```
