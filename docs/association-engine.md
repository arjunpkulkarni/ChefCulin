# Board tasks: Association Engine (D1 + D2)

> Here's what chemistry, tradition, and the corpus each suggest for this set — and
> where they agree or pull apart.

The chef shouldn't have to mentally merge three tabs. Given what's on the dish, the
engine asks every association lens, combines the answers, and surfaces both the
agreement and the disagreement. It does not choose the dish.

| Task | Job | Persisted? |
|------|-----|------------|
| **D1. Orchestration** | Ask Compound + Tradition + Co-occurrence, merge into one payload | No |
| **D2. Disagreement handling** | Flag where the lenses diverge — never suppress | No |

This is not trending/balance (E4/E5), not Palate Memory, and **it does not replace
the individual lens panes** — every tab still stands on its own.

---

## D1 — Orchestration

`associate({ dish, form, cuisineScope }, { api })` in
[`src/lib/associationEngine.js`](../src/lib/associationEngine.js) returns:

```ts
{
  seed, dish, form, cuisineScope,
  threads:       Thread[],           // tradition threads + engagement + scope flags
  byLens:        { compound, tradition, cooccurrence },
  combined:      CombinedCandidate[],
  disagreements: Disagreement[],
  cooccur:       { status: 'ok'|'error', canonical, error }
}
```

### How each lens is asked

| Lens | Source | Rule |
|------|--------|------|
| Compound | `COMPOUND_GROUPS` | Every chip is a candidate; a group the dish already draws on is `engaged` and sorts first |
| Tradition | `TRADITION_GROUPS` + `extend` | Same, plus thread/region tags. A locked scope **flags, never filters** |
| Co-occurrence | `api.cooccur(seed, 24)` | Live artifact API — same seed rule and hub filter as `CooccurPane` |
| Form | `FRAMES` | **Context, not a chip source.** Contributes the locked form name and its overlay, and can raise a `form vs thread` disagreement |

The static lenses are duck-anchored — they answer "what register do you want the fat
to carry", not "what goes with the last thing you added". So the dish decides
*emphasis*, not membership: it marks groups `engaged` and sorts them up. Filtering
the static groups by the last chip added would be inventing a relevance signal the
data does not carry.

The seed for the corpus is the last dish ingredient, or `duck` when the dish is
empty — identical to `CooccurPane`, and hubs (salt, butter, onion…) are filtered the
same way. `HUBS` now lives in the engine and `CooccurPane` imports it, so the two
views cannot drift apart.

### Merging

```ts
CombinedCandidate = {
  name, lenses: Lens[], reasons: string[],
  agreement: 'single' | 'multi',   // multi = 2+ lenses named it independently
  primaryLens: Lens, engaged: boolean, meta
}
```

**`agreement` is a count, not a verdict.** It says how many ways of looking arrived
at the same ingredient. Sorting is by that count descending, then by whether the
dish already engages the thread; ties keep `LENSES` order, which is presentation
order and nothing more. Nothing in this module ranks chemistry against tradition
against the corpus — there is deliberately no cross-lens score, because any such
number would be an argument that science beat culture or the reverse.

**`primaryLens`** is the first lens in `LENSES` order that named the candidate. It
drives the chip colour and is what `addIngredient(name, lens)` records as
provenance — so a dish item's `lens` is always one of the three real lenses
(`compound` / `tradition` / `co-occurrence`) and `COLORS` needs no fourth entry. The
merged view never invents a source that isn't a real lens.

**Corpus outage is not fatal.** `associate` never throws for an unreachable API: the
co-occurrence lens degrades to empty, `cooccur.status` becomes `'error'`, and a
`corpus unavailable` disagreement says the merge is two lenses, not three.

---

## D2 — Resolution approach: **flag, don't suppress**

The chosen approach, matching what cuisine scope already does everywhere else in
this codebase. Nothing is dropped because another lens disagreed, and no lens is
declared the winner.

```ts
Disagreement = {
  theme, lenses: string[], summary,
  candidates: { lens, names, note? }[]
}
```

| Theme | Fires when | What it says |
|-------|-----------|--------------|
| `corpus vs tradition` | Zero name overlap between the corpus and tradition | Tradition says *why* something works; the corpus says what cooks wrote down. A gap usually means the dish is off the well-trodden path — which may be the point |
| `corpus vs chemistry` | Zero overlap between the corpus and compound | Same shape, different frame |
| `scope vs thread` | A scope is locked and threads fall outside it | Names how many, and that they are still listed and still one click away |
| `form vs thread` | The locked form's `absent` properties hit the `requires` of a thread the dish is **already drawing on** | e.g. "You're drawing on the Beijing thread, but Broth system does not produce crisp skin" |
| `corpus unavailable` | The artifact API did not answer | This merge is two lenses, not three |

`form vs thread` only fires for *engaged* threads. Flagging a contradiction with a
thread the chef isn't using would be noise.

### What the UI does with it

[`AssociationPanel.jsx`](../src/components/AssociationPanel.jsx), the **Associate**
tab (after Co-occurrence, before Form):

1. **Where the lenses converge** — multi-lens hits as cards with their lens tags and
   reasons. The three lens tags have deliberately equal visual weight.
2. **Where they pull apart** — every disagreement, in full.
3. **`<Lens>` alone** — single-lens candidates, one section per lens, in that lens's
   own order. There is no merged ranking of single-lens items, because ordering them
   against each other would be exactly the cross-lens verdict this engine refuses to
   make. Long lists are capped for display with a count of the rest — a display cap,
   never a filter.

---

## Session, not memory

The Association Engine reads. It writes nothing:

- No `savePalate`, no `POST /palate`. Asserted in the tests.
- No Postgres, no persisted association results.
- Clicking a chip adds an ingredient to the dish exactly like any lens tab. That's
  it — the panel keeps no memory of what you did in it.

**Palate Memory is still F6 Save only**
(see [`corpus-and-palate-memory.md`](corpus-and-palate-memory.md)).

The corpus is read through the existing precomputed artifact API (`GET /cooccur`).
No CSV is scanned at request time, and no `GET /associate` endpoint was added —
frontend orchestration is the accepted MVP. If the merge later needs to be shared
with another client, that is the point to move it server-side.

## Where it lives

| Piece | Location |
|-------|----------|
| Collectors, merge, disagreements | `src/lib/associationEngine.js` |
| Debounced, cancelling hook | `src/lib/useAssociation.js` |
| Associate tab UI | `src/components/AssociationPanel.jsx` |
| Tab wiring | `src/components/Surface.jsx` |
| Shared hub filter | `HUBS`, exported from the engine, used by `CooccurPane` |

## Tests

```bash
npm test
```

`src/lib/associationEngine.test.js` — each collector, hub/dish filtering, the
multi-lens intersection against a stubbed corpus, `primaryLens` provenance, every
disagreement theme, corpus-outage degradation, and that a locked scope changes the
candidate count by zero.

`src/components/AssociationPanel.test.jsx` — three lenses reach one panel,
convergence renders distinctly from single-lens items, chips add under a real lens,
the scope flag appears without shortening the tradition list, and no palate helper
is ever called.

## Out of scope

- Replacing Compound/Tradition static content with an LLM
- Adaptive / personalization / trending (E4–E5, separate board)
- Graph DB, multi-hop traversal
- Persisting association results to Postgres
