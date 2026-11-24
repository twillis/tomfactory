# Task: build the spike's probe

Build the probe the plan describes: the ugliest thing that answers the question. You may change
anything in the current directory except the codebase's settings, its ideals and its constitution.
Nothing you write is merged; it is kept on this run's own branch, and the findings quote it.

## The question

{{request}}

## The plan

{{plan}}

## How the factory will run it

You can run nothing. The factory runs the probe itself, contained, with this command, `{path}`
being the file you name below:

    {{probe_command}}

Make the probe print each measurement plainly, labelled, because what it prints is all the
findings will have. Exiting with an error is allowed where the error is what is measured. Tests
live under: {{test_paths}}

## If the probe could not be run last time

What happened, if anything. Mend the probe so that it runs, and change nothing else:

{{failure}}

In your reply's JSON object:

- `summary`: what the probe does, in one sentence
- `probe_file`: the probe's file, relative to the current directory, as `{path}` will be given it
- `files_changed`: every file you added or changed
