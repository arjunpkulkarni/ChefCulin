import { describe, expect, it } from 'vitest'
import { TREND_PAIRS, TREND_THRESHOLD, computeBalance } from './balance.js'
import { anchorFor } from '../data/domain.js'

const chickenAnchor = anchorFor('Chicken')
const duckAnchor = anchorFor('Mallard duck')

/** Dish entries as the workspace builds them: name + lens, no form yet. */
const ing = (name) => ({ name, lens: 'compound', mode: null, modeNote: null, axAdd: null })
const dishOf = (...names) => names.map(ing)

const ALLOWED_PAIRS = ['sweet', 'acid', 'fat', 'dairy']

describe('trending detection — threshold', () => {
  it('is fixed at 40% and applies to every axis', () => {
    expect(TREND_THRESHOLD).toBe(0.4)
  })

  it('fires salt at 0.4 with five gathered ingredients and no phantom anchor', () => {
    const b = computeBalance(
      dishOf('miso', 'soy', 'rosemary', 'bay', 'thyme'),
      null,
      anchorFor(null)
    )
    expect(b.shares.salt).toBe(0.4)
    expect(b.primaryTrend).toMatchObject({ axis: 'salt', pair: 'fat', trend: 'high' })
  })

  it('does not fire below the threshold', () => {
    // acid 1 over n = 5 = 0.2
    const b = computeBalance(dishOf('vinegar', 'rosemary', 'bay', 'thyme'), null)
    expect(b.trends).toEqual([])
    expect(b.primaryTrend).toBeNull()
  })
})

describe('trending detection — gate', () => {
  it('reports no trend under 3 ingredients, however lopsided', () => {
    const b = computeBalance(dishOf('verjus', 'cider vinegar'), null)
    expect(b.trends).toEqual([])
    expect(b.primaryTrend).toBeNull()
    expect(b.msg).toBe('Balance check begins at 3 ingredients. (2/3)')
  })

  it('still draws bars under the gate', () => {
    const b = computeBalance(dishOf('verjus', 'cider vinegar'), null, anchorFor(null))
    expect(b.widths.acid).toBeCloseTo(100)
  })
})

describe('E4 — flag + corrective pair', () => {
  it('flags a dish heavy on acid and suggests sweet', () => {
    const b = computeBalance(dishOf('verjus', 'cider vinegar', 'sorrel'), null)
    expect(b.primaryTrend).toMatchObject({
      axis: 'acid',
      trend: 'high',
      pair: 'sweet',
    })
    expect(b.primaryTrend.share).toBeCloseTo(1)
    expect(b.primaryTrend.suggestion).toMatch(/acidic/i)
    expect(b.flaggedAxes).toContain('acid')
  })

  it('flags salt toward fat', () => {
    const b = computeBalance(dishOf('miso', 'soy', 'anchovy'), null)
    expect(b.primaryTrend).toMatchObject({ axis: 'salt', pair: 'fat' })
  })

  it('flags sweet toward acid', () => {
    const b = computeBalance(dishOf('sugar', 'grape', 'raisin'), null)
    expect(b.primaryTrend).toMatchObject({ axis: 'sweet', pair: 'acid' })
  })

  it('flags fat toward acid', () => {
    const b = computeBalance(dishOf('peanut', 'almond', 'sesame'), null)
    expect(b.primaryTrend).toMatchObject({ axis: 'fat', pair: 'acid' })
  })

  it('flags capsaicin heat toward dairy', () => {
    const b = computeBalance(dishOf('chile', 'ancho chile', 'pasilla chile'), null)
    expect(b.primaryTrend).toMatchObject({ axis: 'heat', pair: 'dairy' })
  })

  it('never suggests a pair outside the MVP table', () => {
    const dishes = [
      dishOf('verjus', 'cider vinegar', 'sorrel'),
      dishOf('miso', 'soy', 'anchovy'),
      dishOf('sugar', 'grape', 'raisin'),
      dishOf('peanut', 'almond', 'sesame'),
      dishOf('chile', 'ancho chile', 'pasilla chile'),
      dishOf('bacon', 'parmesan', 'red curry paste', 'coconut milk'),
    ]
    const pairs = dishes.flatMap((d) => computeBalance(d, null).trends.map((x) => x.pair))
    expect(pairs.length).toBeGreaterThan(0)
    pairs.forEach((p) => expect(ALLOWED_PAIRS).toContain(p))
    Object.values(TREND_PAIRS).forEach((spec) => expect(ALLOWED_PAIRS).toContain(spec.pair))
  })

  it('returns structure, not only prose', () => {
    const t = computeBalance(dishOf('verjus', 'cider vinegar', 'sorrel'), null).primaryTrend
    expect(Object.keys(t).sort()).toEqual(
      ['axis', 'note', 'pair', 'share', 'suggestion', 'trend'].sort()
    )
    expect(typeof t.share).toBe('number')
  })
})

describe('E4 — offset guard', () => {
  it('does not flag an axis its counterweight already matches', () => {
    const b = computeBalance(dishOf('Apple', 'Apple', 'Apple'), null)
    expect(b.shares.acid).toBeGreaterThan(0.5)
    expect(b.trends.map((t) => t.axis)).not.toContain('acid')
    expect(b.trends.map((t) => t.axis)).not.toContain('sweet')
  })
})

describe('E4 — heat is the capsaicin path only', () => {
  it('does not suggest fat/dairy for volatile pungency', () => {
    const b = computeBalance(dishOf('horseradish', 'horseradish', 'horseradish'), null)
    expect(b.shares.heat).toBeGreaterThan(0.9)
    expect(b.trends.map((t) => t.axis)).not.toContain('heat')
    const heatNote = b.notes.find((x) => x.ax === 'heat')?.note || ''
    expect(heatNote).toMatch(/Fat does essentially nothing|do not respond to the same correction/)
  })

  it('does not suggest fat/dairy for trigeminal tingle', () => {
    const b = computeBalance(dishOf('ginger', 'galangal', 'pink peppercorn'), null)
    expect(b.trends.map((t) => t.axis)).not.toContain('heat')
  })
})

describe('empty start — no presets', () => {
  it('reads all zeros with an empty plate and no form', () => {
    const b = computeBalance([], null, anchorFor('Chicken'))
    expect(b.widths.fat).toBe(0)
    expect(b.widths.umami).toBe(0)
    expect(b.shares.fat).toBe(0)
    expect(b.msg).toMatch(/Gather ingredients/)
  })

  it('does not seed fat from focus until something is on the plate or a form is set', () => {
    const b = computeBalance([], null, anchorFor('Chicken'))
    expect(b.shares.fat).toBe(0)
  })
})

describe('preserved behaviour', () => {
  it('keeps umami synergy on when the anchor carries nucleotide and plate adds glutamate', () => {
    const withGlut = computeBalance(dishOf('miso', 'rosemary', 'bay'), null, duckAnchor)
    expect(withGlut.synergyOn).toBe(true)
    expect(withGlut.umamiLabel).toBe('Umami ×')
  })

  it('notes unclaimed nucleotide when anchor has IMP but no glutamate yet', () => {
    const plain = computeBalance(dishOf('rosemary', 'bay', 'thyme'), null, duckAnchor)
    expect(plain.synergyOn).toBe(false)
    expect(plain.notes.some((n) => /sitting unclaimed/i.test(n.note))).toBe(true)
  })

  it('keeps the two umami notes distinct — added glutamate vs unclaimed', () => {
    const added = computeBalance(dishOf('miso', 'rosemary', 'bay'), null, duckAnchor)
    expect(added.notes[0].note).toMatch(/dashi principle/)

    const unclaimed = computeBalance(dishOf('rosemary', 'bay', 'thyme'), null, duckAnchor)
    expect(unclaimed.notes[0].note).toMatch(/sitting unclaimed/)
  })

  it('uses a neutral anchor when none passed', () => {
    const neutral = computeBalance(dishOf('rosemary', 'bay', 'thyme'), null, anchorFor(null))
    const defaulted = computeBalance(dishOf('rosemary', 'bay', 'thyme'), null)
    expect(neutral.widths).toEqual(defaulted.widths)
  })

  it('says nothing is trending when nothing is', () => {
    const b = computeBalance(dishOf('rosemary', 'bay', 'thyme'), null)
    expect(b.primaryTrend).toBeNull()
  })

  it('moves the acid bar when Foodb citrus is gathered', () => {
    const b = computeBalance(dishOf('Lemon', 'verjus', 'cider vinegar'), null, anchorFor(null))
    expect(b.shares.acid).toBeGreaterThan(0.4)
    expect(b.primaryTrend?.axis).toBe('acid')
  })
})
