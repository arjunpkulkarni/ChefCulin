# Board tasks: Trending detection (E4 + E5)

While the chef composes, the workspace notices when the plate is leaning too far on
one axis, flags it, and names the corrective pair. It does not pick the ingredient,
and it does not remember the answer past this session.

| Task | Job | Persisted? |
|------|-----|------------|
| **E4. Trending detection + corrective pair** | Flag an axis over threshold; suggest its counterweight | No |
| **E5. Chef decision capture** | Accept / Adjust / Override on the active flag | **Session only** |

---

## The one rule

```text
share(axis) = axisTotal / n        n = dish.length + 1
trend fires  when  share >= 0.40  AND  counterweightTotal < axisTotal
```

`n` counts the contributors on the plate: every gathered ingredient plus the duck
anchor, which carries fat and glutamate/inosinate of its own. This is the same
normalisation the balance bars already used, so a bar drawn at 40% and a trend
firing at 0.40 are the same number — there is no second scale to reconcile.

**Fixed at 0.40 for every axis.** The old per-axis constants (`0.4` acid, `0.45`
salt, `0.55` fat) are gone, along with their hand-tuned offset guards. The
counterweight check generalises the old "acidic with little to offset it" clause:
an axis is only flagged if the thing that would fix it is not already there.

Nothing reads Palate Memory and nothing adapts to the chef. **Adaptive thresholds
are G3 and are deliberately not built here.**

The gate stays where it was: **balance checking begins at 3 ingredients.** Below
that a single pickle is a third of the plate by share and the flag would be an
artefact of the divisor.

## Corrective pairs — the whole table

| Flagged axis | Suggest toward (`pair`) | Mechanism |
|--------------|------------------------|-----------|
| `acid` | `sweet` | Mutual suppression — sugar pulls perceived tartness down |
| `sweet` | `acid` | The same suppression, run the other way |
| `salt` | `fat` | Fat impedes sodium release from the matrix. **One way only** |
| `fat` | `acid` | Sourness brightens, astringency dries. Salt will not cut fat |
| `heat` | `dairy` | Capsaicin is lipophilic |

`TREND_PAIRS` in `src/lib/balance.js` is the table. A suggestion outside it is a bug.

**Heat is the capsaicin path only.** The heat *bar* sums every pungency mechanism,
but the trend rule reads `t.capsaicin` alone. Volatile pungency (isothiocyanates —
horseradish, wasabi, mustard) and trigeminal tingle (sanshool, ginger, galangal)
must never produce a fat/dairy suggestion, because fat does nothing to either. Both
still get their explanatory note; a note is context, not a correction.

## Shape

`computeBalance(dish, form)` returns bars and mechanism notes as before, plus:

```ts
trends: Trend[]          // every axis over threshold, highest share first
primaryTrend: Trend|null // trends[0] — the one the UI acts on
notes: Note[]            // umami / pungency mechanism prose. No pair, not actionable
shares: Record<Axis, number>
flaggedAxes: string[]    // which bars to highlight

type Trend = {
  axis: 'acid'|'sweet'|'salt'|'fat'|'heat'
  trend: 'high'
  share: number          // 0–1
  pair: 'sweet'|'acid'|'fat'|'dairy'
  suggestion: string     // chef-facing one-liner
  note: string           // short mechanism
}
```

Structured, not only prose — the UI renders fields, it does not parse sentences.

`trends` and `notes` are separate on purpose. A note explains something true about
the plate; a trend is a thing the chef can answer. Only trends get buttons.

## E5 — session, not memory

`DishSidebar` renders the primary trend with **Accept / Adjust / Override**. Each
click calls `recordBalanceDecision(decision, trend)` in `WorkspaceContext`, which
appends to `balanceDecisions` and does nothing else:

```text
{ axis, pair, decision, share, at, dishSnapshot: string[] }
```

- **No API call.** Not `savePalate`, not `POST /palate`, not `fetch`. Asserted in
  `src/context/WorkspaceContext.test.jsx`.
- **No auto-add.** The suggestion names an axis. Choosing the ingredient is the
  creative act and it stays with the chef.
- **Answered flags settle**, then return if the dish changes — `balanceDecisionFor`
  matches on axis *and* dish snapshot, because a different plate is a different
  question.
- **In memory only.** Reload and the log is gone.

### The distinction that matters

```text
E4/E5 balance decisions ──► WorkspaceContext.balanceDecisions   (session, in memory)
F6 Save                 ──► POST /palate ──► Postgres           (per-user, kept)
```

Working balance decisions are not a committed dish. A chef overriding an acid flag
six times while composing has not told you anything they want remembered — they were
thinking. Palate Memory records what they chose to keep, and **F6 Save is the only
thing that writes it** (see [`corpus-and-palate-memory.md`](corpus-and-palate-memory.md)).

## Where it lives

| Piece | Location |
|-------|----------|
| Threshold, pair table, trend math | `src/lib/balance.js` |
| Flag UI + Accept/Adjust/Override | `src/components/DishSidebar.jsx` |
| `balanceDecisions`, `recordBalanceDecision` | `src/context/WorkspaceContext.jsx` |

Not in the corpus ETL, not in the cooccur API. This is dish-local math on axis tags
already in `src/data/domain.js` — no corpus lookup, no multi-hop graph.

## Tests

```bash
npm test
```

`src/lib/balance.test.js` — threshold and gate, every pair in the table, the
capsaicin-only heat path, the offset guard, preserved bar/synergy behaviour.

`src/context/WorkspaceContext.test.jsx` — flag renders with its pair, the three
controls append to session state, no palate helper and no `fetch` is ever called,
no chip is added to the dish.

## Out of scope

- Adaptive thresholds / Palate-driven personalization (G3)
- Multi-hop graph or co-occurrence for suggestions
- Auto-committing corrective ingredients
- Persisting balance decisions to Postgres
