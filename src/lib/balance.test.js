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

  it('fires salt at 0.4, where the old per-axis 0.45 would not have', () => {
    // salt 2 (miso, soy) over n = 4 ingredients + 1 anchor = 0.4 exactly
    const b = computeBalance(dishOf('miso', 'soy', 'rosemary', 'bay'), null)
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
    const b = computeBalance(dishOf('verjus', 'cider vinegar'), null)
    expect(b.widths.acid).toBeCloseTo((2 / 3) * 100)
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
    expect(b.primaryTrend.share).toBeCloseTo(0.75)
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
    // tart cherry is acid AND sweet: each axis offsets the other exactly
    const b = computeBalance(dishOf('tart cherry', 'blood orange', 'pomegranate'), null)
    expect(b.shares.acid).toBeCloseTo(0.75)
    expect(b.trends.map((t) => t.axis)).not.toContain('acid')
    expect(b.trends.map((t) => t.axis)).not.toContain('sweet')
  })
})

describe('E4 — heat is the capsaicin path only', () => {
  it('does not suggest fat/dairy for volatile pungency', () => {
    // three horseradish: pungent share 0.75, but fat does nothing to it
    const b = computeBalance(dishOf('horseradish', 'horseradish', 'horseradish'), null)
    expect(b.shares.heat).toBeCloseTo(0.75)
    expect(b.trends.map((t) => t.axis)).not.toContain('heat')
    // the mechanism is still explained — it just carries no corrective pair
    expect(b.notes.find((x) => x.ax === 'heat').note).toMatch(/Fat does essentially nothing/)
  })

  it('does not suggest fat/dairy for trigeminal tingle', () => {
    const b = computeBalance(dishOf('ginger', 'galangal', 'pink peppercorn'), null)
    expect(b.trends.map((t) => t.axis)).not.toContain('heat')
  })
})

describe('preserved behaviour', () => {
  it('keeps umami synergy on when the anchor carries nucleotide', () => {
    const plain = computeBalance(dishOf('rosemary', 'bay', 'thyme'), null, duckAnchor)
    expect(plain.synergyOn).toBe(true)
    expect(plain.umamiLabel).toBe('Umami ×')
    expect(plain.synGhost).toBeNull()
    // the bar is widened by the synergy multiplier, as before
    expect(plain.widths.umami).toBeCloseTo((1 / 4) * 100 * 2.2)
  })

  it('keeps the two umami notes distinct — added glutamate vs unclaimed', () => {
    const added = computeBalance(dishOf('miso', 'rosemary', 'bay'), null, duckAnchor)
    expect(added.notes[0].note).toMatch(/dashi principle/)

    const unclaimed = computeBalance(dishOf('rosemary', 'bay', 'thyme'), null, duckAnchor)
    expect(unclaimed.notes[0].note).toMatch(/sitting unclaimed/)
  })

  it('defaults to Chicken anchor when none passed', () => {
    const explicit = computeBalance(dishOf('rosemary', 'bay', 'thyme'), null, chickenAnchor)
    const defaulted = computeBalance(dishOf('rosemary', 'bay', 'thyme'), null)
    expect(explicit.widths).toEqual(defaulted.widths)
  })

  it('says nothing is trending when nothing is', () => {
    const b = computeBalance(dishOf('rosemary', 'bay', 'thyme'), null)
    expect(b.primaryTrend).toBeNull()
  })

  it('moves the acid bar when Foodb citrus is gathered', () => {
    const b = computeBalance(dishOf('Lemon', 'Apple', 'Vinegar'), null, chickenAnchor)
    expect(b.shares.acid).toBeGreaterThan(0.4)
    expect(b.primaryTrend?.axis).toBe('acid')
  })
})
