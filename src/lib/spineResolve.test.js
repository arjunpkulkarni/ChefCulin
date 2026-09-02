import { describe, expect, it } from 'vitest'
import {
  looseKey,
  resolveIngredient,
  resolveAll,
  searchSpine,
  SPINE,
  SPINE_PICKER_LIST,
} from './spineResolve.js'

describe('spine resolution — member level', () => {
  it('resolves garlic to the garlic member, not the cluster', () => {
    const r = resolveIngredient('garlic')
    expect(r.state).toBe('resolved')
    expect(r.spine_member).toMatch(/^GARLIC/)
    expect(r.display).toBe('Garlic')
  })

  it('never renders an entry id as the display name', () => {
    // culin:leek holds ten alliums and has display_name: null.
    for (const name of ['garlic', 'onion', 'chive', 'leek']) {
      const r = resolveIngredient(name)
      if (r.state !== 'resolved') continue
      expect(r.display).not.toMatch(/^culin:/)
      expect(r.display.toLowerCase()).not.toBe('leek')
      expect(r.display.toLowerCase().startsWith(name)).toBe(true)
    }
  })

  it('keeps members of one cluster distinct', () => {
    const garlic = resolveIngredient('garlic')
    const chive = resolveIngredient('chive')
    expect(garlic.spine_id).toBe(chive.spine_id)
    expect(garlic.member_id).not.toBe(chive.member_id)
  })

  it('distinguishes mace from nutmeg, which share one entry', () => {
    const mace = resolveIngredient('mace')
    const nutmeg = resolveIngredient('nutmeg')
    expect(mace.spine_id).toBe('culin:mace')
    expect(nutmeg.spine_id).toBe('culin:mace')
    expect(mace.member_id).not.toBe(nutmeg.member_id)
    expect(nutmeg.display).toBe('Nutmeg')
  })
})

describe('spine resolution — match order and normalisation', () => {
  it('is deterministic across repeated calls', () => {
    const a = resolveIngredient('tomato')
    const b = resolveIngredient('tomato')
    expect(a).toEqual(b)
  })

  it('resolves tomato, the original picker failure', () => {
    const r = resolveIngredient('tomato')
    expect(r.state).toBe('resolved')
    expect(r.spine_id).toBeTruthy()
  })

  it('collapses plural and case without a hand-written alias', () => {
    expect(resolveIngredient('Tomatoes').spine_id).toBe(resolveIngredient('tomato').spine_id)
    expect(resolveIngredient('GARLIC').spine_id).toBe(resolveIngredient('garlic').spine_id)
  })

  it('reports which tier matched', () => {
    expect(resolveIngredient('garlic').matched_on).toBe('member')
    expect(resolveIngredient('Tomatoes').matched_on).toBe('loose')
  })

  it('returns unknown rather than guessing', () => {
    const r = resolveIngredient('xyzzy not a food')
    expect(r.state).toBe('unknown')
    expect(r.spine_id).toBeNull()
    expect(r.display).toBe('xyzzy not a food')
  })

  it('treats an empty query as unknown', () => {
    expect(resolveIngredient('').state).toBe('unknown')
    expect(resolveIngredient(null).state).toBe('unknown')
  })

  it('resolves a list in order', () => {
    const out = resolveAll(['garlic', 'nutmeg'])
    expect(out.map((r) => r.display)).toEqual(['Garlic', 'Nutmeg'])
  })
})

describe('looseKey', () => {
  it('collapses the separators that differ between corpus and chef', () => {
    expect(looseKey('Extra-Virgin Olive Oil')).toBe(looseKey('extra virgin olive oil'))
    expect(looseKey('tomatoes')).toBe(looseKey('tomato'))
  })
})

describe('picker list', () => {
  it('offers culinary members only, sorted, with no duplicates', () => {
    expect(SPINE_PICKER_LIST.length).toBeGreaterThan(300)
    const labels = SPINE_PICKER_LIST.map((r) => r.label)
    expect([...new Set(labels)].length).toBe(labels.length)
    expect([...labels].sort((a, b) => a.localeCompare(b))).toEqual(labels)
  })

  it('every picker entry resolves — no dead options', () => {
    // The FooDB picker offered 933 names of which only 148 had a spine route.
    // Whatever the picker offers must resolve by construction.
    const dead = SPINE_PICKER_LIST.filter((r) => resolveIngredient(r.label).state === 'unknown')
    expect(dead).toEqual([])
  })

  it('searches by prefix first', () => {
    const hits = searchSpine('gar')
    expect(hits.length).toBeGreaterThan(0)
    expect(hits[0].label.toLowerCase().startsWith('gar')).toBe(true)
  })
})

describe('spine bundle shape', () => {
  it('carries 360 entries', () => {
    expect(SPINE.length).toBe(360)
  })

  it('has exactly the entries with no display name that the resolver compensates for', () => {
    const nulls = SPINE.filter((e) => !e.display_name).map((e) => e.spine_id).sort()
    expect(nulls).toEqual([
      'culin:bilberry',
      'culin:chekur',
      'culin:kuini',
      'culin:leek',
      'culin:summer_savory',
    ])
  })
})
