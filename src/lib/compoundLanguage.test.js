import { describe, expect, it } from 'vitest'
import { groupPhrase, groupsFor, sharedCompoundSentence, topCompounds } from './compoundLanguage.js'

const SHARED = [
  { compound_id: 'a', compound_group: 'Bases', idf: 3.9, raw_compound: 'pyrazine' },
  { compound_id: 'b', compound_group: 'Bases', idf: 2.1, raw_compound: 'pyridine' },
  { compound_id: 'c', compound_group: 'Furans', idf: 3.1, raw_compound: 'furfural' },
  { compound_id: 'd', compound_group: 'Sulfur compounds', idf: 4.4, raw_compound: 'thiol' },
]

describe('compound language', () => {
  it('ranks groups by how many compounds they contribute', () => {
    const g = groupsFor(SHARED)
    expect(g[0].group).toBe('Bases')
    expect(g[0].count).toBe(2)
  })

  it('speaks in groups, not scores', () => {
    const s = sharedCompoundSentence(SHARED)
    expect(s).toContain('pyrazines and pyridines')
    expect(s).not.toMatch(/\d\.\d/)
  })

  it('says nothing when there is nothing shared', () => {
    expect(sharedCompoundSentence([])).toBeNull()
  })

  it('names the rarest compounds first, since IDF is what makes a pairing distinctive', () => {
    expect(topCompounds(SHARED, { limit: 2 }).map((c) => c.raw_compound)).toEqual([
      'thiol',
      'pyrazine',
    ])
  })

  it('passes unknown groups through rather than dropping them', () => {
    expect(groupPhrase('Quinoxalines')).toBe('quinoxalines')
    expect(groupPhrase(null)).toBe('unclassified compounds')
  })
})
