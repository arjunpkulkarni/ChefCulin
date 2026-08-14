import { describe, expect, it, vi } from 'vitest'
import {
  HUBS,
  associate,
  collectCompound,
  collectCooccur,
  collectTradition,
  findDisagreements,
  mergeCandidates,
  traditionThreads,
} from './associationEngine.js'

const ing = (name) => ({ name, lens: 'compound', mode: null, modeNote: null, axAdd: null })
const dishOf = (...names) => names.map(ing)

/** A corpus stub: `results` shaped like GET /cooccur. */
const stubApi = (names, extra = {}) => ({
  cooccur: vi.fn(async (seed) => ({
    canonical: extra.canonical || seed,
    results: names.map((ingredient, i) => ({
      ingredient,
      confidence: 0.9 - i * 0.05,
      freq: 1000 - i * 10,
    })),
  })),
})

const failingApi = () => ({
  cooccur: vi.fn(async () => {
    throw new Error('Corpus API unreachable')
  }),
})

const nameSet = (list) => new Set(list.map((c) => c.name))
const find = (list, name) => list.find((c) => c.name === name)

describe('collectCompound', () => {
  it('returns chips from the static groups, minus what is already on the dish', () => {
    const c = collectCompound(dishOf('rosemary'))
    expect(nameSet(c).has('rosemary')).toBe(false)
    expect(nameSet(c).has('juniper')).toBe(true)
    expect(find(c, 'juniper').lens).toBe('compound')
    expect(find(c, 'juniper').reason).toBe('Fat carries these')
  })

  it('marks the group the dish already draws on as engaged, and sorts it first', () => {
    const c = collectCompound(dishOf('rosemary', 'juniper'))
    expect(find(c, 'bay').meta).toMatchObject({ engaged: true, hits: 2 })
    expect(find(c, 'miso').meta.engaged).toBe(false)
    expect(c[0].meta.engaged).toBe(true)
  })
})

describe('collectTradition', () => {
  it('includes thread chips and extend chips, tagged by thread', () => {
    const c = collectTradition(dishOf(), null)
    expect(find(c, 'hoisin').meta.thread).toMatch(/Beijing/)
    expect(find(c, 'lettuce cup').meta.extend).toBe(true)
    expect(find(c, 'lettuce cup').reason).toMatch(/extends the principle/)
  })

  it('leaves inScope null when no cuisine scope is locked', () => {
    const c = collectTradition(dishOf(), null)
    expect(find(c, 'hoisin').meta.inScope).toBeNull()
  })

  it('flags scope without filtering anything out', () => {
    const scoped = collectTradition(dishOf(), { label: 'China', keys: ['china'] })
    const unscoped = collectTradition(dishOf(), null)

    expect(nameSet(scoped).size).toBe(nameSet(unscoped).size)
    expect(find(scoped, 'hoisin').meta.inScope).toBe(true)
    // a Mexican thread ingredient is out of scope and still present
    expect(find(scoped, 'ancho chile').meta.inScope).toBe(false)
  })
})

describe('collectCooccur', () => {
  it('filters hubs and anything already on the dish', async () => {
    const api = stubApi(['salt', 'butter', 'thyme', 'orange', 'cherry'])
    const res = await collectCooccur('duck', { api, exclude: ['cherry'] })

    const names = res.candidates.map((c) => c.name)
    expect(names).toEqual(['thyme', 'orange'])
    expect(names.some((n) => HUBS.has(n))).toBe(false)
  })

  it('carries corpus confidence through as meta', async () => {
    const api = stubApi(['thyme'])
    const res = await collectCooccur('duck', { api })
    expect(res.candidates[0].meta.confidence).toBeCloseTo(0.9)
    expect(res.candidates[0].lens).toBe('co-occurrence')
  })

  it('uses the canonical name the API resolved', async () => {
    const api = stubApi(['thyme'], { canonical: 'duck breast' })
    const res = await collectCooccur('duck breasts', { api })
    expect(res.canonical).toBe('duck breast')
  })
})

describe('mergeCandidates', () => {
  it('marks an ingredient named by two lenses as multi and keeps both reasons', () => {
    const combined = mergeCandidates({
      compound: [{ name: 'miso', lens: 'compound', reason: 'browning', meta: {} }],
      tradition: [{ name: 'miso', lens: 'tradition', reason: 'a thread', meta: {} }],
      cooccurrence: [{ name: 'thyme', lens: 'co-occurrence', reason: 'corpus', meta: {} }],
    })

    const miso = find(combined, 'miso')
    expect(miso.agreement).toBe('multi')
    expect(miso.lenses).toEqual(['compound', 'tradition'])
    expect(miso.reasons).toEqual(['browning', 'a thread'])
    expect(find(combined, 'thyme').agreement).toBe('single')
  })

  it('sorts convergence first', () => {
    const combined = mergeCandidates({
      compound: [{ name: 'solo', lens: 'compound', reason: 'x', meta: {} }],
      tradition: [{ name: 'both', lens: 'tradition', reason: 'y', meta: {} }],
      cooccurrence: [{ name: 'both', lens: 'co-occurrence', reason: 'z', meta: {} }],
    })
    expect(combined[0].name).toBe('both')
  })

  it('gives primaryLens in LENSES order so provenance stays a real lens', () => {
    const combined = mergeCandidates({
      compound: [],
      tradition: [{ name: 'miso', lens: 'tradition', reason: 'y', meta: {} }],
      cooccurrence: [{ name: 'miso', lens: 'co-occurrence', reason: 'z', meta: {} }],
    })
    expect(find(combined, 'miso').primaryLens).toBe('tradition')
    expect(['compound', 'tradition', 'co-occurrence']).toContain(
      find(combined, 'miso').primaryLens
    )
  })
})

describe('D1 — associate', () => {
  it('asks all three lenses and returns one combined payload', async () => {
    const api = stubApi(['thyme', 'orange'])
    const data = await associate({ dish: dishOf('rosemary') }, { api })

    expect(api.cooccur).toHaveBeenCalledWith('rosemary', 24)
    expect(data.byLens.compound.length).toBeGreaterThan(0)
    expect(data.byLens.tradition.length).toBeGreaterThan(0)
    expect(data.byLens.cooccurrence.length).toBe(2)
    expect(data.combined.length).toBeGreaterThan(0)
    expect(data.seed).toBe('rosemary')
  })

  it('seeds from the last dish ingredient, or duck when the dish is empty', async () => {
    const api = stubApi(['thyme'])
    await associate({ dish: dishOf('miso', 'cherry') }, { api })
    expect(api.cooccur).toHaveBeenCalledWith('cherry', 24)

    const empty = stubApi(['thyme'])
    await associate({ dish: [] }, { api: empty })
    expect(empty.cooccur).toHaveBeenCalledWith('duck', 24)
  })

  it('finds the multi-lens intersection across static data and the mocked corpus', async () => {
    // juniper is in all three; bergamot is compound + corpus; miso is compound +
    // tradition; pear is corpus alone
    const api = stubApi(['juniper', 'bergamot', 'pear'])
    const data = await associate({ dish: dishOf() }, { api })

    expect(find(data.combined, 'juniper').lenses).toEqual([
      'compound',
      'tradition',
      'co-occurrence',
    ])
    expect(find(data.combined, 'bergamot').lenses).toEqual(['compound', 'co-occurrence'])
    expect(find(data.combined, 'miso').lenses).toEqual(['compound', 'tradition'])
    expect(find(data.combined, 'pear')).toMatchObject({
      agreement: 'single',
      lenses: ['co-occurrence'],
      primaryLens: 'co-occurrence',
    })
  })

  it('sorts three-lens convergence above two-lens', async () => {
    const api = stubApi(['juniper', 'bergamot'])
    const data = await associate({ dish: dishOf() }, { api })
    expect(data.combined[0].name).toBe('juniper')
    expect(data.combined[0].lenses).toHaveLength(3)
  })

  it('includes locked form as context, never as a candidate', async () => {
    const api = stubApi(['thyme'])
    const data = await associate({ dish: dishOf('rosemary'), form: { name: 'Confit' } }, { api })

    expect(data.form).toMatchObject({ name: 'Confit', overlay: 'confit' })
    expect(nameSet(data.combined).has('Confit')).toBe(false)
  })

  it('degrades to two lenses when the corpus is down, and says so', async () => {
    const data = await associate({ dish: dishOf('rosemary') }, { api: failingApi() })

    expect(data.cooccur.status).toBe('error')
    expect(data.byLens.cooccurrence).toEqual([])
    expect(data.byLens.compound.length).toBeGreaterThan(0)
    expect(data.disagreements.map((d) => d.theme)).toContain('corpus unavailable')
  })

  it('writes nothing — no palate helper exists on the injected client', async () => {
    const api = stubApi(['thyme'])
    const data = await associate({ dish: dishOf('rosemary') }, { api })
    expect(Object.keys(api)).toEqual(['cooccur'])
    expect(data).not.toHaveProperty('saved')
  })
})

describe('D2 — disagreement handling: flag, do not suppress', () => {
  it('flags corpus vs tradition when nothing overlaps', async () => {
    const api = stubApi(['nothing-culinary-here', 'another-unknown'])
    const data = await associate({ dish: dishOf() }, { api })

    const themes = data.disagreements.map((d) => d.theme)
    expect(themes).toContain('corpus vs tradition')
    expect(themes).toContain('corpus vs chemistry')

    const d = data.disagreements.find((x) => x.theme === 'corpus vs tradition')
    expect(d.lenses).toEqual(['co-occurrence', 'tradition'])
    expect(d.summary).toMatch(/Neither is wrong/)
    expect(d.candidates.map((c) => c.lens).sort()).toEqual(['co-occurrence', 'tradition'])
  })

  it('does not flag divergence when the lenses do overlap', async () => {
    const api = stubApi(['miso', 'juniper'])
    const data = await associate({ dish: dishOf() }, { api })
    const themes = data.disagreements.map((d) => d.theme)
    expect(themes).not.toContain('corpus vs tradition')
    expect(themes).not.toContain('corpus vs chemistry')
  })

  it('keeps every tradition candidate in combined when a scope is locked', async () => {
    const api = stubApi(['thyme'])
    const scoped = await associate(
      { dish: dishOf(), cuisineScope: { label: 'China', keys: ['china'] } },
      { api }
    )
    const open = await associate({ dish: dishOf() }, { api })

    expect(scoped.byLens.tradition.length).toBe(open.byLens.tradition.length)
    expect(nameSet(scoped.combined).size).toBe(nameSet(open.combined).size)
    // a Mexican thread ingredient survives a China scope
    expect(nameSet(scoped.combined).has('ancho chile')).toBe(true)

    const d = scoped.disagreements.find((x) => x.theme === 'scope vs thread')
    expect(d).toBeTruthy()
    expect(d.summary).toMatch(/flags, it never filters/)
  })

  it('flags a locked form that contradicts a thread the dish is drawing on', () => {
    // the Beijing thread requires crisp skin; Broth system does not produce it
    const dish = dishOf('pancake', 'hoisin')
    const threads = traditionThreads(dish, null)
    const out = findDisagreements({
      byLens: { compound: [], tradition: [], cooccurrence: [] },
      threads,
      form: { name: 'Broth system' },
    })

    const d = out.find((x) => x.theme === 'form vs thread')
    expect(d).toBeTruthy()
    expect(d.summary).toMatch(/Broth system/)
    expect(d.summary).toMatch(/crisp skin/)
  })

  it('does not flag a form clash for a thread the dish is not using', () => {
    const threads = traditionThreads(dishOf(), null)
    const out = findDisagreements({
      byLens: { compound: [], tradition: [], cooccurrence: [] },
      threads,
      form: { name: 'Broth system' },
    })
    expect(out.map((d) => d.theme)).not.toContain('form vs thread')
  })
})
