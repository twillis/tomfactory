---
description: Orchestrate tomfactory on a target codebase — write requests, watch runs, bring me the decisions
argument-hint: [target path | what I want next | status | retro]
---

Act as tomfactory's orchestrator. The factory is at `@TOMFACTORY@`. Read its playbook,
`@TOMFACTORY@/orchestrator/playbook.md`, first and follow it, then `@TOMFACTORY@/README.md` for
the factory's commands. Run them as `uv run --project @TOMFACTORY@ python -m factory <command>`.

The target is the codebase I name, or else the current directory if it has a `.factory.toml`,
or else ask me which.

What I want: $ARGUMENTS
