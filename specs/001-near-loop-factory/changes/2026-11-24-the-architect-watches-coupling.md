# Change record: the architect watches for unnecessary coupling (2026-11-24)

Made outside spec kit, for spec kit to review later.

**Asked for by the operator, 2026-11-24**, after the orchestrator flagged that bttr_erp's run 92 would make a
public JSON shape follow PostgreSQL's session settings: "If I were arch persona I would have flagged this as a
warning of unnecessary coupling perhaps. Im not interested in supporting any other database engine but still",
then "The persona change I would hope would work would be to look out for unnecessary coupling not just coupling to
the database but anything. The architecture must remain flexible so that it can adapt to change over time. I don't
want to be sitting around redoing all of this because version 20 just dropped and broke everything if you get what
I mean?", and "approve your persona changes".

**Changed**

- **`personas/architect.md`.** A new priority 5, "Unnecessary coupling": for every dependency a change adds or leans
  on, what the next major version, deprecation or replacement would cost; necessary coupling in one owned place is
  fine; warn where it spreads, leaks into a public contract, or rests on unstated behaviour. Priorities 5 to 7 are
  renumbered 6 to 8. A new "must not": accept "we only support X" as a reason to couple. No requirement changes
  (FR-042 to FR-044 and FR-048 hold), and no step entry or prompt changed.

**Why now.** The architect reviewed three runs (89 to 91) that leaned on PostgreSQL's `to_jsonb` text and
`record_send` binary format and did not warn. And at the merge of run 92 the orchestrator found bttr_erp's
contained tests ran on Python 3.14 while its pyproject allowed 3.13, where a `-> list[dict]` annotation in a class
with a `list` method failed at import: the code rested on what one interpreter version happened to allow.

Tests: none new, since no behaviour of the factory's code changed.
