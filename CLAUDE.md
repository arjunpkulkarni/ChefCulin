<!-- begin breken -->
## Breken: answer it once, and write it down

This repository is indexed. The `breken` MCP server is for the half of the work that
ANSWERS — the bug, the incident, how this works, what the team already decided — so the
answer outlives the session that found it.

Six tools. Reach for them like this:

| when | the call |
| --- | --- |
| a bug worth understanding, not guessing at | `rca` — evidence, then a run, then its dossier |
| the work concluded something the team should inherit — a decision, a gotcha, the naive fix to avoid | `record` (after the human agrees) |
| any factual question about this repo — "what calls X", "can I delete X", "what breaks if…", "where do I change…" | `ask` |
| a plan you are about to implement | `review_changes` mode `plan` |
| after a chunk of edits · before every pull request | `review_changes` mode `quick` · mode `diff` |
| what keeps breaking here, before picking what to fix | `trends` |

`ask` answers from the call graph with `file:line` citations, and dispatches known question
shapes to the exact specialist. Two of its verdicts are worth asking for by name, because
they are the ones a search cannot establish: whether anything still calls a symbol, and
whether code is reachable at all. A grep that finds nothing may simply have missed the
caller; the graph knows the difference, and a deletion rests on that difference.

Two rules about its answers:

1. `UNKNOWN` **is the answer.** It means the index holds no evidence, not that you should
   infer one. Narrow the question or read the named source — do not fill the gap.
2. **Cite what it cites.** Its answers carry `file:line` anchors; carry them forward so a
   reader can check the claim rather than take it.

### Write it down so the team inherits it

When your work **concludes something durable** — a retirement ("we are done with X, use Y"),
a trap that cost real time, the fix that looks right and is not — offer to record it with
`record`. It lands on the org dashboard and, for decisions, in the repo ledger, so the next
plan review warns anyone who tries to extend the retired thing, with your reason. Offer this
only for real, concluded knowledge about **shared code** — never for questions, exploration,
one-off preferences, or anything private. It stages one line but does NOT commit; the human
commits it with their work, so nothing is shared without their say-so.
<!-- end breken -->
