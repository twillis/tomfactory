# Task: check the specification, plan and tasks against each other

Before anything is built, check that the specification, the plan and the task list agree
with each other and with the rules below, following spec kit's analyze and checklist
instructions. Change no file.

## The request

{{request}}

## If your last reply was not accepted

{{failure}}

## What to produce

The operator reads your summary to decide whether to approve the plan and tasks, so say
plainly what the plan is, what the tasks are, and anything that does not agree.

In your reply's JSON object:

- `plan`: a summary of the plan and tasks for the operator, naming the files they are in
- `findings`: each inconsistency, gap or broken rule you found, most serious first; empty if none
