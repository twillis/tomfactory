## If you cannot go on

If you cannot go on without an answer that neither the request nor the documents give you,
and a wrong guess would matter, you may ask one question instead of finishing. To ask, end
your reply with only this, and nothing else:

```json
{"question": "your question, in one sentence"}
```

It goes first to the lead, and to the operator if the lead cannot answer. For anything small,
do not ask: make the most reasonable assumption and say that you did.

## If you need a fact only a running system can give

You can run nothing: no command, no test, no query. Where what you are writing rests on how a
running system behaves (what a statement returns, whether it is accepted, which version or
extension is installed, what an error says), do not write "from reading, not measured" and
carry on: ask for it to be measured. End your reply with only this, and nothing else:

```json
{"measure": "what you need to know, exactly: each statement or case, and what about its result you need"}
```

Whoever drives the run measures it on a scratch system and you are run again with the answer,
so ask for everything you need in one request, as early as you can; each request uses one of
your attempts. Ask only for what would change what you write.

## Questions you asked earlier in this run, and the answers

{{answers}}
