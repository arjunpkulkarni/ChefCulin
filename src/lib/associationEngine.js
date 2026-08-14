import { COMPOUND_GROUPS } from '../data/compound.js'
import { TRADITION_GROUPS } from '../data/tradition.js'
import { FRAMES, PROP_LABELS } from '../data/domain.js'
import * as defaultApi from '../api.js'

/**
 * Association Engine (D1 + D2).
 *
 * Asks every association lens the same question — "given what is on the plate,
 * what else?" — and returns one payload showing where the answers converge and
 * where they pull apart.
 *
 * It does not choose. It does not rank one lens above another. It writes
 * nothing: no Palate Memory, no POST /palate. See docs/association-engine.md.
 */

/**
 * Presentation order, NOT precedence. Chemistry is listed before tradition
 * before the corpus because a reader needs a stable order, not because one is
 * a better answer than another. Nothing in this module ranks lens against lens.
 */
export const LENSES = ['compound', 'tradition', 'co-occurrence']

/** `Candidate.lens` id → key in the `byLens` payload. */
export const LENS_KEYS = {
  compound: 'compound',
  tradition: 'tradition',
  'co-occurrence': 'cooccurrence',
}

export const LENS_LABELS = {
  compound: 'Compound',
  tradition: 'Tradition',
  'co-occurrence': 'Corpus',
}

/**
 * Corpus hubs — salt, butter, onion — co-occur with everything, so they carry
 * no information about duck specifically. Filtered for display only; the
 * artifact tables still hold them. Shared with CooccurPane.
 */
export const HUBS = new Set([
  'salt',
  'butter',
  'sugar',
  'water',
  'pepper',
  'black pepper',
  'oil',
  'olive oil',
  'vegetable oil',
  'flour',
  'egg',
  'eggs',
  'onion',
  'garlic',
])

const nameOf = (d) => (typeof d === 'string' ? d : d?.name)
const dishNames = (dish) => (dish || []).map(nameOf).filter(Boolean)

/**
 * Compound lens.
 *
 * The static groups are duck-anchored: they answer "what register do you want
 * the fat to carry", not "what goes with the last thing you added". So every
 * chip stays a candidate, and the dish decides *emphasis* — a group the chef has
 * already drawn from is `engaged`, and its remaining chips sort first.
 */
export function collectCompound(dish) {
  const have = new Set(dishNames(dish))
  const out = []
  COMPOUND_GROUPS.forEach((group) => {
    const hits = group.chips.filter((c) => have.has(c))
    group.chips.forEach((name) => {
      if (have.has(name)) return
      out.push({
        name,
        lens: 'compound',
        reason: group.title,
        meta: {
          group: group.title,
          posture: group.posture,
          engaged: hits.length > 0,
          hits: hits.length,
        },
      })
    })
  })
  return out.sort((a, b) => b.meta.hits - a.meta.hits)
}

/**
 * Thread-level view of the Tradition lens: which documented threads the dish is
 * already drawing on, and how each sits against a locked cuisine scope.
 *
 * `inScope` is `null` when no scope is locked. A locked scope **flags, it never
 * filters** — same rule the Tradition pane already follows.
 */
export function traditionThreads(dish, cuisineScope) {
  const have = new Set(dishNames(dish))
  return TRADITION_GROUPS.map((group) => {
    const chips = group.chips
    const extend = group.extend?.chips || []
    const keys = group.region ? group.region.split(',') : []
    const hits = [...chips, ...extend].filter((c) => have.has(c))
    return {
      title: group.title,
      thread: group.thread,
      region: group.region,
      regionKeys: keys,
      inScope: cuisineScope ? keys.some((k) => cuisineScope.keys.includes(k)) : null,
      engaged: hits.length > 0,
      hits,
      requires: group.whyBox?.requires || null,
      group,
    }
  })
}

/**
 * Tradition lens. Includes `extend` chips — they break the thread but serve the
 * same architecture, and the pane already offers them, so hiding them here
 * would make the merged view narrower than the tab it summarises.
 */
export function collectTradition(dish, cuisineScope, threads = traditionThreads(dish, cuisineScope)) {
  const have = new Set(dishNames(dish))
  const out = []
  threads.forEach((t) => {
    const push = (name, isExtend) => {
      if (have.has(name)) return
      out.push({
        name,
        lens: 'tradition',
        reason: isExtend ? `${t.thread || t.title} — extends the principle` : t.thread || t.title,
        meta: {
          group: t.title,
          thread: t.thread,
          region: t.region,
          inScope: t.inScope,
          extend: Boolean(isExtend),
          engaged: t.engaged,
          hits: t.hits.length,
        },
      })
    }
    t.group.chips.forEach((n) => push(n, false))
    ;(t.group.extend?.chips || []).forEach((n) => push(n, true))
  })
  return out.sort((a, b) => b.meta.hits - a.meta.hits)
}

/**
 * Co-occurrence lens — the live corpus, via the same precomputed artifact API
 * the Co-occurrence pane uses. No CSV is scanned here.
 *
 * `api` is injectable so the merge can be tested without a running backend.
 */
export async function collectCooccur(seed, options = {}) {
  const { api = defaultApi, n = 24, exclude = [], limit = 16 } = options
  const res = await api.cooccur(seed, n)
  const canonical = res?.canonical || seed
  const skip = new Set(exclude)
  const rows = (res?.results || [])
    .filter((r) => !skip.has(r.ingredient) && !HUBS.has(r.ingredient))
    .slice(0, limit)
  return {
    canonical,
    candidates: rows.map((r) => ({
      name: r.ingredient,
      lens: 'co-occurrence',
      reason: `Co-occurs with ${canonical} across the corpus`,
      meta: { confidence: r.confidence, freq: r.freq },
    })),
  }
}

/**
 * Merge the three answers by ingredient name.
 *
 * `agreement: 'multi'` means two or more lenses named it independently — that is
 * the only cross-lens claim this engine makes, and it is a count, not a verdict.
 * Sorting is by that count descending; ties keep LENSES order, which is
 * presentation order and nothing more.
 *
 * `primaryLens` is the first lens in LENSES order that named the candidate. It
 * is what a chip uses for colour and what `addIngredient` records as provenance,
 * so a dish item's lens is always one of the three real lenses — the merged view
 * never invents a fourth source. (See docs/association-engine.md.)
 */
export function mergeCandidates(byLens) {
  const map = new Map()
  LENSES.forEach((lens) => {
    const list = byLens[LENS_KEYS[lens]] || []
    list.forEach((c) => {
      const cur = map.get(c.name)
      if (cur) {
        if (!cur.lenses.includes(lens)) cur.lenses.push(lens)
        cur.reasons.push(c.reason)
        cur.meta = { ...c.meta, ...cur.meta }
        cur.engaged = cur.engaged || Boolean(c.meta?.engaged)
        return
      }
      map.set(c.name, {
        name: c.name,
        lenses: [lens],
        reasons: [c.reason],
        agreement: 'single',
        primaryLens: lens,
        engaged: Boolean(c.meta?.engaged),
        meta: { ...c.meta },
      })
    })
  })

  const combined = [...map.values()]
  combined.forEach((c) => {
    c.agreement = c.lenses.length > 1 ? 'multi' : 'single'
  })
  /* Stable sort: convergence first, then whether the dish already engages that
     thread. Everything below that keeps the order the lenses produced. */
  return combined.sort(
    (a, b) => b.lenses.length - a.lenses.length || Number(b.engaged) - Number(a.engaged)
  )
}

const namesOf = (list) => list.map((c) => c.name)

/**
 * D2 — resolution approach: **flag, don't suppress.**
 *
 * The same rule cuisine scope already follows. Nothing is dropped because
 * another lens disagrees, and no lens is declared the winner. Where the lenses
 * genuinely describe the plate differently, that difference is surfaced as a
 * thing to notice — two valid frames, not an error to fix.
 */
export function findDisagreements({
  byLens,
  threads = [],
  cuisineScope = null,
  form = null,
  seed = 'duck',
  cooccurStatus = 'ok',
} = {}) {
  const out = []
  const compound = byLens.compound || []
  const tradition = byLens.tradition || []
  const cooccurrence = byLens.cooccurrence || []
  const corpusNames = new Set(namesOf(cooccurrence))

  const divergence = (list, lens, label) => {
    if (cooccurStatus !== 'ok' || !cooccurrence.length || !list.length) return
    if (namesOf(list).some((n) => corpusNames.has(n))) return
    out.push({
      theme: `corpus vs ${label}`,
      lenses: ['co-occurrence', lens],
      summary: `Nothing the corpus puts near ${seed} appears in ${label} for this set. Neither is wrong — ${label} describes why something works, the corpus describes what cooks actually wrote down. A gap here usually means the dish is off the well-trodden path, which may be the point.`,
      candidates: [
        { lens: 'co-occurrence', names: namesOf(cooccurrence).slice(0, 8) },
        { lens, names: namesOf(list).slice(0, 8) },
      ],
    })
  }
  divergence(compound, 'compound', 'chemistry')
  divergence(tradition, 'tradition', 'tradition')

  if (cuisineScope) {
    const inScope = threads.filter((t) => t.inScope)
    const outScope = threads.filter((t) => t.inScope === false)
    if (outScope.length) {
      out.push({
        theme: 'scope vs thread',
        lenses: ['tradition'],
        summary: `Scope is locked to ${cuisineScope.label}. ${outScope.length} documented thread${outScope.length > 1 ? 's fall' : ' falls'} outside it and ${outScope.length > 1 ? 'are' : 'is'} still listed — a scope flags, it never filters. Ingredients from an out-of-scope thread stay one click away.`,
        candidates: [
          {
            lens: 'tradition',
            names: inScope.flatMap((t) => t.group.chips).slice(0, 8),
            note: 'in scope',
          },
          {
            lens: 'tradition',
            names: outScope.flatMap((t) => t.group.chips).slice(0, 8),
            note: 'outside scope',
          },
        ],
      })
    }
  }

  /* Form is context, not a chip source: it can contradict a thread the dish is
     already drawing on, and that contradiction is worth naming. */
  const frame = form && FRAMES[form.name]
  if (frame) {
    const absent = new Set(frame.absent || [])
    const clashes = threads.filter(
      (t) => t.engaged && (t.requires || []).some((r) => absent.has(r))
    )
    clashes.forEach((t) => {
      const missing = (t.requires || [])
        .filter((r) => absent.has(r))
        .map((r) => PROP_LABELS[r] || r)
      out.push({
        theme: 'form vs thread',
        lenses: ['tradition'],
        summary: `You are drawing on ${t.thread || t.title}, but the locked form ${form.name} does not produce ${missing.join(', ')}. Keep the form and adapt the thread, or change the form — both are real answers.`,
        candidates: [{ lens: 'tradition', names: t.hits, note: t.thread || t.title }],
      })
    })
  }

  if (cooccurStatus === 'error') {
    out.push({
      theme: 'corpus unavailable',
      lenses: ['co-occurrence'],
      summary:
        'The corpus lens did not answer, so this merge is chemistry and tradition only. Convergence below is between two lenses, not three — start the API (cd pipeline && python -m culin_etl.serve) to hear the third.',
      candidates: [],
    })
  }

  return out
}

/**
 * D1 — orchestration. Ask every lens, merge, and report the disagreements.
 *
 * Never throws for a corpus outage: the co-occurrence lens degrades to empty and
 * says so in `disagreements`, because two lenses answering is still useful.
 */
export async function associate(state = {}, deps = {}) {
  const { dish = [], form = null, cuisineScope = null } = state
  const names = dishNames(dish)
  const seed = names.length ? names[names.length - 1] : 'duck'

  const threads = traditionThreads(dish, cuisineScope)
  const byLens = {
    compound: collectCompound(dish),
    tradition: collectTradition(dish, cuisineScope, threads),
    cooccurrence: [],
  }

  let cooccur = { status: 'ok', seed, canonical: seed, error: null }
  try {
    const res = await collectCooccur(seed, { api: deps.api, exclude: names })
    byLens.cooccurrence = res.candidates
    cooccur = { ...cooccur, canonical: res.canonical }
  } catch (err) {
    cooccur = { status: 'error', seed, canonical: seed, error: err?.message || String(err) }
  }

  const combined = mergeCandidates(byLens)
  const disagreements = findDisagreements({
    byLens,
    threads,
    cuisineScope,
    form,
    seed: cooccur.canonical,
    cooccurStatus: cooccur.status,
  })

  return {
    seed: cooccur.canonical,
    dish: names,
    form: form ? { name: form.name, overlay: FRAMES[form.name]?.overlay || null } : null,
    cuisineScope,
    threads: threads.map(({ group, ...rest }) => rest),
    byLens,
    combined,
    disagreements,
    cooccur,
  }
}
