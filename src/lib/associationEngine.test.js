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

/** Compound API mock: flavor-network neighbors. */
const stubCompoundApi = (names, extra = {}) => ({
  compound: vi.fn(async (seed) => ({
    canonical: extra.canonical || seed,
    results: names.map((display, i) => ({
      ingredient: display.toLowerCase().replace(/\s+/g, '_'),
      display,
      weight: 50 - i,
      confidence: 0.9 - i * 0.05,
    })),
  })),
})

const stubApi = (names, extra = {}) => ({
  cooccur: vi.fn(async (seed) => ({
    canonical: extra.canonical || seed,
    results: names.map((ingredient, i) => ({
      ingredient,
      confidence: 0.9 - i * 0.05,
      freq: 1000 - i * 10,
    })),
  })),
  compound: vi.fn(async (seed) => ({
    canonical: extra.compoundCanonical || seed,
    results: (extra.compound || names).map((display, i) => ({
      ingredient: display.toLowerCase().replace(/\s+/g, '_'),
      display,
      weight: 40 - i,
      confidence: 0.8 - i * 0.05,
    })),
  })),
})

const failingApi = () => ({
  cooccur: vi.fn(async () => {
    throw new Error('Corpus API unreachable')
  }),
  compound: vi.fn(async (seed) => ({
    canonical: seed,
    results: [
      { ingredient: 'white_wine', display: 'White Wine', weight: 50, confidence: 0.8 },
    ],
  })),
})

/** Tradition DB mock for Associate. */
const stubTraditionDb = (names, extra = {}) => ({
  getTraditionAssociation: vi.fn(async (seed, opts = {}) => ({
    seed,
    candidates: names.map((name, i) => ({
      name,
      lens: 'tradition',
      reason: extra.reason || 'documented thread',
      meta: {
        thread: extra.thread || 'thread',
        inScope: extra.inScope ?? null,
        engaged: false,
        hits: 0,
        dish_count: 10 - i,
      },
    })),
    threads: extra.threads || [],
  })),
})

const identityMatch = async (name) => ({
  canonical: String(name || '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim(),
  source: 'test',
})

/** Prefer culinary token when Foodb-style names appear in tests. */
const smartMatch = async (name) => {
  const { heuristicRecipeNlg } = await import('./matchRecipeNlg.js')
  return { canonical: heuristicRecipeNlg(name), source: 'test' }
}

const nameSet = (list) => new Set(list.map((c) => c.name))
const find = (list, name) => list.find((c) => c.name === name)

describe('collectCompound', () => {
  it('returns flavor-network neighbors, minus what is already on the dish', async () => {
    const api = stubCompoundApi(['White Wine', 'Thyme', 'Rosemary'])
    const c = await collectCompound(dishOf('Rosemary'), 'Chicken', { api })
    expect(nameSet(c).has('Rosemary')).toBe(false)
    expect(nameSet(c).has('White Wine')).toBe(true)
    expect(find(c, 'White Wine').lens).toBe('compound')
    expect(find(c, 'White Wine').meta.weight).toBeGreaterThan(0)
    expect(api.compound).toHaveBeenCalled()
  })

  it('sorts by shared compound weight from the API', async () => {
    const api = stubCompoundApi(['White Wine', 'Thyme'])
    const c = await collectCompound(dishOf(), 'Garlic', { api })
    expect(c[0].meta.weight).toBeGreaterThanOrEqual(c[1]?.meta.weight ?? 0)
  })
})

describe('collectTradition', () => {
  it('loads candidates from the Tradition DB module', async () => {
    const traditionDb = stubTraditionDb(['hoisin', 'scallion'])
    const { candidates } = await collectTradition(dishOf(), null, {
      traditionDb,
      matchIngredient: smartMatch,
    })
    expect(traditionDb.getTraditionAssociation).toHaveBeenCalledWith('chicken', {
      exclude: [],
      limit: 16,
      cuisineScope: null,
    })
    expect(find(candidates, 'hoisin').lens).toBe('tradition')
  })

  it('seeds from the last dish ingredient', async () => {
    const traditionDb = stubTraditionDb(['thyme'])
    await collectTradition(dishOf('miso', 'cherry'), null, {
      traditionDb,
      matchIngredient: identityMatch,
    })
    expect(traditionDb.getTraditionAssociation).toHaveBeenCalledWith(
      'cherry',
      expect.any(Object)
    )
  })
})

describe('collectCooccur', () => {
  it('filters hubs and anything already on the dish', async () => {
    const api = stubApi(['salt', 'butter', 'thyme', 'orange', 'cherry'])
    const res = await collectCooccur('chicken', { api, exclude: ['cherry'] })

    const names = res.candidates.map((c) => c.name)
    expect(names).toEqual(['thyme', 'orange'])
    expect(names.some((n) => HUBS.has(n))).toBe(false)
  })

  it('carries corpus confidence through as meta', async () => {
    const api = stubApi(['thyme'])
    const res = await collectCooccur('chicken', { api })
    expect(res.candidates[0].meta.confidence).toBeCloseTo(0.9)
    expect(res.candidates[0].lens).toBe('co-occurrence')
  })

  it('uses the canonical name the API resolved', async () => {
    const api = stubApi(['thyme'], { canonical: 'chicken breast' })
    const res = await collectCooccur('chicken breasts', { api })
    expect(res.canonical).toBe('chicken breast')
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
    const traditionDb = stubTraditionDb(['miso', 'Garlic'])
    const data = await associate({ dish: dishOf('Rosemary') }, { api, traditionDb, matchIngredient: smartMatch })

    expect(api.cooccur).toHaveBeenCalledWith('rosemary', 24)
    expect(data.byLens.compound.length).toBeGreaterThan(0)
    expect(data.byLens.tradition.length).toBe(2)
    expect(data.byLens.cooccurrence.length).toBe(2)
    expect(data.combined.length).toBeGreaterThan(0)
    expect(data.seed).toBe('rosemary')
  })

  it('seeds from the last dish ingredient, or focus when the dish is empty', async () => {
    const api = stubApi(['thyme'])
    const traditionDb = stubTraditionDb(['garlic'])
    await associate(
      { dish: dishOf('miso', 'cherry') },
      { api, traditionDb, matchIngredient: identityMatch }
    )
    expect(api.cooccur).toHaveBeenCalledWith('cherry', 24)
    expect(traditionDb.getTraditionAssociation).toHaveBeenCalledWith(
      'cherry',
      expect.any(Object)
    )

    const emptyApi = stubApi(['thyme'])
    const emptyTradition = stubTraditionDb(['garlic'])
    await associate(
      { dish: [], focusIngredient: 'Chicken' },
      { api: emptyApi, traditionDb: emptyTradition, matchIngredient: smartMatch }
    )
    expect(emptyApi.cooccur).toHaveBeenCalledWith('chicken', 24)
    expect(emptyTradition.getTraditionAssociation).toHaveBeenCalledWith(
      'chicken',
      expect.any(Object)
    )
  })

  it('finds the multi-lens intersection across lenses', async () => {
    const api = stubApi(['Garlic', 'bergamot', 'pear'], { compound: ['Garlic', 'Miso'] })
    const traditionDb = stubTraditionDb(['Garlic', 'Miso'])
    const data = await associate({ dish: dishOf() }, { api, traditionDb, matchIngredient: smartMatch })

    expect(find(data.combined, 'Garlic').lenses).toEqual([
      'compound',
      'tradition',
      'co-occurrence',
    ])
    expect(find(data.combined, 'Miso').lenses).toEqual(['compound', 'tradition'])
    expect(find(data.combined, 'pear')).toMatchObject({
      agreement: 'single',
      lenses: ['co-occurrence'],
      primaryLens: 'co-occurrence',
    })
  })

  it('sorts three-lens convergence above two-lens', async () => {
    const api = stubApi(['Garlic', 'bergamot'])
    const traditionDb = stubTraditionDb(['Garlic'])
    const data = await associate({ dish: dishOf() }, { api, traditionDb, matchIngredient: smartMatch })
    expect(data.combined[0].name).toBe('Garlic')
    expect(data.combined[0].lenses).toHaveLength(3)
  })

  it('includes locked form as context, never as a candidate', async () => {
    const api = stubApi(['thyme'])
    const traditionDb = stubTraditionDb(['garlic'])
    const data = await associate(
      { dish: dishOf('Rosemary'), form: { name: 'Confit' } },
      { api, traditionDb, matchIngredient: smartMatch }
    )

    expect(data.form).toMatchObject({ name: 'Confit', overlay: 'confit' })
    expect(nameSet(data.combined).has('Confit')).toBe(false)
  })

  it('degrades to two lenses when the corpus is down, and says so', async () => {
    const traditionDb = stubTraditionDb(['miso'])
    const data = await associate({ dish: dishOf('Rosemary') }, {
      api: failingApi(),
      traditionDb,
      matchIngredient: smartMatch,
    })

    expect(data.cooccur.status).toBe('error')
    expect(data.byLens.cooccurrence).toEqual([])
    expect(data.byLens.compound.length).toBeGreaterThan(0)
    expect(data.disagreements.map((d) => d.theme)).toContain('corpus unavailable')
  })

  it('writes nothing — no palate helper exists on the injected client', async () => {
    const api = stubApi(['thyme'])
    const traditionDb = stubTraditionDb(['garlic'])
    const data = await associate({ dish: dishOf('Rosemary') }, {
      api,
      traditionDb,
      matchIngredient: smartMatch,
    })
    expect(Object.keys(api).sort()).toEqual(['cooccur', 'compound'].sort())
    expect(data).not.toHaveProperty('saved')
  })
})

describe('D2 — disagreement handling: flag, do not suppress', () => {
  it('flags corpus vs tradition when nothing overlaps', async () => {
    const api = stubApi(['nothing-culinary-here', 'another-unknown'], {
      compound: ['compound-only-ingredient'],
    })
    const traditionDb = stubTraditionDb(['tradition-only'])
    const data = await associate({ dish: dishOf() }, { api, traditionDb, matchIngredient: smartMatch })

    const themes = data.disagreements.map((d) => d.theme)
    expect(themes).toContain('corpus vs tradition')
    expect(themes).toContain('corpus vs chemistry')

    const d = data.disagreements.find((x) => x.theme === 'corpus vs tradition')
    expect(d.lenses).toEqual(['co-occurrence', 'tradition'])
    expect(d.summary).toMatch(/Neither is wrong/)
    expect(d.candidates.map((c) => c.lens).sort()).toEqual(['co-occurrence', 'tradition'])
  })

  it('does not flag divergence when the lenses do overlap', async () => {
    const api = stubApi(['Miso', 'Garlic'], { compound: ['Miso', 'Garlic'] })
    const traditionDb = stubTraditionDb(['Miso', 'Garlic'])
    const data = await associate({ dish: dishOf() }, { api, traditionDb, matchIngredient: smartMatch })
    const themes = data.disagreements.map((d) => d.theme)
    expect(themes).not.toContain('corpus vs tradition')
    expect(themes).not.toContain('corpus vs chemistry')
  })

  it('keeps every tradition candidate in combined when a scope is locked', async () => {
    const api = stubApi(['thyme'])
    const traditionDb = stubTraditionDb(['hoisin', 'ancho chile'], {
      threads: [
        { title: 'China thread', thread: 'China', inScope: true },
        { title: 'Mexico thread', thread: 'Mexico', inScope: false },
      ],
    })
    const scoped = await associate(
      { dish: dishOf(), cuisineScope: { label: 'China', keys: ['china'] } },
      { api, traditionDb, matchIngredient: smartMatch }
    )
    const open = await associate({ dish: dishOf() }, { api, traditionDb, matchIngredient: smartMatch })

    expect(scoped.byLens.tradition.length).toBe(open.byLens.tradition.length)
    expect(nameSet(scoped.combined).size).toBe(nameSet(open.combined).size)
    expect(nameSet(scoped.combined).has('ancho chile')).toBe(true)

    const d = scoped.disagreements.find((x) => x.theme === 'scope vs thread')
    expect(d).toBeTruthy()
    expect(d.summary).toMatch(/flags, it never filters/)
  })

  it('traditionThreads is empty — static threads removed', () => {
    expect(traditionThreads(dishOf('pancake'), null)).toEqual([])
  })
})
