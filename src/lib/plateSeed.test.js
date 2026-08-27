import { describe, expect, it } from 'vitest'
import { plateSeed } from './plateSeed.js'

describe('plateSeed', () => {
  it('uses focus when the dish is empty', () => {
    expect(plateSeed([], 'Chicken')).toBe('Chicken')
    expect(plateSeed(null, 'Garlic')).toBe('Garlic')
  })

  it('defaults to Chicken when nothing is provided', () => {
    expect(plateSeed([], null)).toBe('Chicken')
    expect(plateSeed([])).toBe('Chicken')
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
