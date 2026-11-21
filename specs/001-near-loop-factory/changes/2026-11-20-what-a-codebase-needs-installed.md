# Change record: what a codebase needs installed, and feature folders that do not clash (2026-11-20)

Made outside spec kit with the operator's agreement ("yes make the change and loosen the containment
enough to make the setup stuff work"), for spec kit to review later.

**Found before the first run on a second codebase.** The next codebase is a Python project with
packages (SQLAlchemy, Pyramid, a PostgreSQL driver). Containment (feature 002, the day before) lets a
test command see the factory's own Python and nothing else, with no network. So nothing could install
a codebase's packages, and nothing installed could be seen. A Rust codebase would have failed the same
way: `uv` and `cargo` both live in the operator's home. The viewer, built entirely on the standard
library, never showed it. The operator: "if the factory cannot do this, then it is not a useful
factory", and "the software factory was supposed to be language agnostic".

**The shape.** The factory still knows nothing about any language. A codebase says what it needs in
its committed `.factory.toml`, which no agent may change, and the factory lets in exactly that:

- **FR-084, `tools`.** Programs on the operator's PATH, by name. Each is bound read-only as one file.
  A path is refused, so the setting cannot expose a folder.
- **FR-083, `setup_command`.** Run by the factory's code before every run of the tests, contained,
  with the network. The network is the loosening the operator agreed to; it is limited to this step.
- **FR-085, the codebase's own home.** A folder per codebase under the factory's home, standing in for
  `$HOME` inside containment. Setup writes to it; tests read it. It is why a cache works for any
  installer without the factory knowing where that installer keeps one. This relaxes FR-070 for the
  setup command only.
- **FR-086.** A failed setup, or a tool that is not installed, fails the step and says which.

**Also found, proving it.** With the network allowed, names could not be looked up: `/etc/resolv.conf`
is a link into `/run`, which containment hides. That had been true of `test_network = true` since
feature 002; the stand-in test only ever tried an address. The resolver file is now let in, read-only,
whenever the network is. Test: `test_code_given_the_network_can_also_look_names_up`.

**Measured, 2026-11-20**, through the factory's own test path, on a scratch codebase with
`tools = ["uv"]`, `setup_command = "uv sync"`, and SQLAlchemy, psycopg, Pyramid, PyYAML and pytest as
its packages:

| | |
|---|---|
| First setup, downloading 22 packages | passed |
| Later setup and tests, from the codebase's home | 1.6 seconds |
| A test starts its own PostgreSQL 18 and queries it through SQLAlchemy, with no network | passed |
| The operator's `~/.ssh` from inside the tests | not there |
| What setup left in the checkout | `uv.lock`, which the step's commit takes |

**FR-087, feature folders.** The operator asked for run names by timestamp so that several people on
one repository do not clash. Branches and run records already were (FR-081, the day before). The
counter left was the spec kit feature folder, `specs/001-…`, numbered from the folders one checkout
can see. It now carries the branch's name.

**Not changed, and worth knowing**

- What a setup command downloads and runs is contained, but it has the network. A hostile package
  could reach the operator's local network. It cannot read the operator's home.
- A tool that is a version manager's shim (asdf's `cargo`) is one file that needs many. It will not
  work as a tool; the real program must be on the PATH.
- `.specify/feature.json` is still one committed file that every spec kit run rewrites, so two
  people's runs will conflict on it when merged. Not addressed.

Tests: `tests/test_sandbox.py` (the last section), `tests/test_speckit.py` (FR-087).
