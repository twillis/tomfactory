# Contract: Containing a Command

`factory/sandbox.py` is the only module that knows how a command is contained. It decides nothing about when; `checks.run_tests` calls it for every run of the target's test command.

```text
command(argv, checkout, network=False) -> argv
    The argv that runs `argv` contained, with `checkout` as its only lasting writable place,
    the factory's Python readable, and the network only if `network`.
    Raises Unavailable(reason) if containment does not work on this machine.

available() -> (bool, reason)
    Whether containment works here, by a trial run, checked once per process.
```

## Guarantees

The contained command:

1. reads and writes `checkout`; reads the system read-only and the factory's Python and its libraries;
2. does not see `/home` otherwise, `/run` (so not `/var/run/docker.sock`), or the operator's environment;
3. writes nowhere else that lasts: `/tmp` is private and discarded;
4. has no network unless `network` is true; loopback always works;
5. cannot outlive the step: stopping the process `proc.run` started ends everything inside.

## What uses it

| Caller | How |
|--------|-----|
| `checks.run_tests` | wraps the test command; `network` is the target's committed `test_network` |
| `operations.doctor` | reports `available()` as the "containment" line |
| the driver | turns `Unavailable` into the `error` failure: the run ends as needs-me, and the tests are not run |

## The target's setting

`.factory.toml`, read from the run's starting commit:

```toml
test_network = false      # true lets this codebase's tests reach the network
```
