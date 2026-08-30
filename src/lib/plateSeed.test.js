import { describe, expect, it } from 'vitest'
import { plateSeed } from './plateSeed.js'

describe('plateSeed', () => {
  it('uses focus when the dish is empty', () => {
    expect(plateSeed([], 'Chicken')).toBe('Chicken')
    expect(plateSeed(null, 'Garlic')).toBe('Garlic')
  })

  it('returns null when nothing is provided', () => {
    expect(plateSeed([], null)).toBeNull()
    expect(plateSeed([])).toBeNull()
  })

  it('uses the last gathered ingredient once the plate has items', () => {
    expect(
      plateSeed(
        [
          { name: 'Garlic' },
          { name: 'Miso' },
        ],
        'Chicken'
      )
    ).toBe('Miso')
  })

  it('skips blank names', () => {
    expect(plateSeed([{ name: '' }, { name: 'Thyme' }], 'Chicken')).toBe('Thyme')
  })
})
