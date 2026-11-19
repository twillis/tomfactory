# Research: Contain the Code Agents Write

**Date**: 2026-11-19 | **Spec**: [spec.md](spec.md)

Everything here was measured on the operator's machine (Ubuntu 26.04.1, kernel 7.0.0-43, user in the `docker` group) unless marked otherwise.

## R1. The problem, measured

A harmless stand-in test, run through the factory's own test path (`proc.run` with `config.test_argv`), reported 7 of 7 capabilities: it read `~/.ssh`, the factory's database and code; wrote outside its checkout; reached the internet; connected to `/var/run/docker.sock`; and left two processes running after the factory stopped its process group. The last is a gap in feature 001: a child that calls `setsid` leaves the group the factory stops.

## R2. Prior art

- **Anthropic's sandbox runtime (`srt`)**, the sandbox behind Claude Code: bubblewrap plus a seccomp filter on Linux, network forced through a host-side proxy with a domain allowlist. Wraps arbitrary processes. Beta research preview. [README](https://cdn.jsdelivr.net/gh/anthropics/sandbox-runtime/README.md), [Claude Code docs](https://code.claude.com/docs/en/sandboxing)
- **Codex CLI**: bubblewrap plus seccomp on Linux. [Internals](https://codex.danielvaughan.com/2026/05/03/codex-cli-sandbox-internals-seatbelt-bubblewrap-landlock-windows-dacl/)
- **Containers and micro-VMs** (OpenHands on Docker, E2B on Firecracker; IndyDevDan's follow-up ran the factory in a throwaway VM): stronger isolation, much heavier.
- **Sandbox escapes** were reported across several coding agents in 2026. [Report](https://codex.danielvaughan.com/2026/07/28/week-of-sandbox-escapes-pillar-security-codex-cli-cursor-gemini-docker-socket-git-hooks-defence/) One layer is not enough to trust alone.

Both mainstream coding agents converged on bubblewrap. That is the primitive.

## R3. The three options, measured with the same stand-in test

| The test could | Uncontained | `srt` as designed | `srt`, seccomp off | Plain bubblewrap |
|---|---|---|---|---|
| Read `~/.ssh` | yes | — | no | no |
| Read the factory's database | yes | — | no | no |
| Read the factory's code | yes | — | no | no |
| Write outside its checkout, lasting | yes | — | no | no (private `/tmp`, discarded) |
| Reach the internet | yes | — | no | no |
| Reach the docker socket | yes | — | **yes** | no |
| Leave a process running | yes | — | no | no |

- **`srt` as designed does not run here.** Ubuntu's `kernel.apparmor_restrict_unprivileged_userns=1` strips capabilities from the nested user namespace its seccomp helper needs. Its README's fixes are to turn the restriction off machine-wide or add an AppArmor profile for the helper. Both need `sudo` and change the machine's security settings.
- **`srt` with `allowAllUnixSockets` (no seccomp layer)** runs, and blocks everything except Unix sockets: the docker socket, root-equivalent for this user, stayed reachable.
- **Plain bubblewrap** works with no system change, because Ubuntu ships an AppArmor profile for `/usr/bin/bwrap`. Its one apparent write landed in a private `/tmp` that exists only inside the sandbox.

## R4. Decision: plain bubblewrap, for the test command only

- **Decision**: wrap the target's test command in `bwrap`. Defer `srt` to phase 2 (containing the agent program, which needs a network allowlist, which needs the AppArmor change).
- **Rationale**: it works today, closes every measured hole including the docker socket and the escaping process, and adds about 10 ms per test run (measured: wrapping `true`). The viewer's full suite, 434 tests including local HTTP servers, passed contained in 24.9 s, the same as uncontained.
- **Alternatives**: `srt` (needs a machine-wide security change, or leaks the docker socket); Docker (needs an image kept in step with the factory, and the docker group is root-equivalent); a VM (out of proportion for a codebase's own tests).
- **Accepted limits**: no seccomp filter, so a kernel bug reachable by an unprivileged process could break out. No resource limits. The network is all or nothing (spec clarification 1).

## R5. The arguments, as measured

```text
bwrap --ro-bind / /                       the system, read-only
      --dev /dev --proc /proc             private device and process views
      --tmpfs /home --tmpfs /tmp --tmpfs /run      hide home, private /tmp; /run hides the docker socket (/var/run -> /run)
      --ro-bind <factory venv> <same>     the Python the factory runs on, and pytest
      --ro-bind <sys.base_prefix> <same>  that Python's own install (under ~/.asdf here)
      --bind <checkout> <same>            the only writable place that lasts
      --chdir <checkout>
      --unshare-all [--share-net]         network only when the codebase allows it
      --new-session --die-with-parent     no terminal injection; dies with the factory
      --clearenv --setenv PATH … HOME /tmp TMPDIR /tmp LANG C.UTF-8 PYTHONDONTWRITEBYTECODE 1
      <the test command>
```

- `--unshare-all` gives a new PID namespace. When the factory stops `bwrap` (it is the leader of the group `proc.run` stops), the namespace's first process dies and the kernel kills everything left in it. That closes R1's escape.
- `--unshare-all` gives a network namespace with only loopback, brought up by bubblewrap. Local HTTP servers inside the tests work (the viewer's do).
- `--clearenv` keeps the operator's environment out (FR-073). The variables set are the ones the viewer's suite needed.
- `--ro-bind / /` and then `--tmpfs` over parts is the simplest whole: everything system-wide is readable and nothing is writable. Hiding `/home` wholesale, then binding back only three paths, makes the home's contents an allowlist.

## R6. Where target code is run

One place: `checks.run_tests`, used by the `baseline`, `tests_fail_first` and `tests_pass` checks, which cover every kind of run (change, tidy, spec kit). Nothing else in the factory executes the target's code. Git, the notification command and the agent program are not target code.

## R7. When containment is unavailable

`bwrap` is checked once per process with a trial run of `bwrap … true`. If it fails, running the tests raises a specific error that the driver turns into the `error` failure, which ends the run as needs-me (rule 4 of `next_step`). This matters because a failed `tests_fail_first` would otherwise send the run back to `write_tests` and loop.
