import { describe, expect, it } from 'vitest'
import {
  DEFAULT_FOCUS,
  INGREDIENT_LIST,
  INGREDIENTS,
  compoundGroups,
  lookupIngredient,
  searchIngredients,
  seedKey,
} from './ingredients.js'

describe('Foodb ingredient list', () => {
  it('covers hundreds of culinary foods', () => {
    expect(INGREDIENTS.length).toBe(933)
    expect(INGREDIENT_LIST.length).toBe(933)
    expect(DEFAULT_FOCUS).toBe('Chicken')
    expect(INGREDIENT_LIST).toContain('Chicken')
    expect(INGREDIENT_LIST).toContain('Garlic')
    expect(INGREDIENT_LIST).toContain('Cattle (Beef, Veal)')
    expect(INGREDIENT_LIST).toContain('Sweet orange')
  })

  it('looks up by case-insensitive name', () => {
    expect(lookupIngredient('chicken')?.name).toBe('Chicken')
    expect(lookupIngredient('Chicken')?.food_group).toBe('Animal foods')
    expect(lookupIngredient('no-such-food')).toBeNull()
  })

  it('seedKey lowercases for corpus queries', () => {
    expect(seedKey('Chicken')).toBe('chicken')
    expect(seedKey('')).toBe('chicken')
  })

  it('searchIngredients finds Foodb names', () => {
    const hits = searchIngredients('orange', { limit: 20 })
    expect(hits.some((n) => /orange/i.test(n))).toBe(true)
    expect(searchIngredients('zzzz-nope')).toEqual([])
  })

  it('compoundGroups covers Foodb families and excludes the focus', () => {
    const groups = compoundGroups('Chicken', { perGroup: 24 })
    expect(groups.length).toBeGreaterThan(5)
    expect(groups.map((g) => g.title)).toContain('Herbs and Spices')
    expect(groups.map((g) => g.title)).toContain('Animal foods')
    groups.forEach((g) => {
      expect(g.chips).not.toContain('Chicken')
      expect(g.lens).toBe('compound')
    })
  })

  it('compoundGroups can return the full family for Associate', () => {
    const herbs = compoundGroups('Chicken', { perGroup: 500 }).find(
      (g) => g.title === 'Herbs and Spices'
    )
    expect(herbs.chips.length).toBeGreaterThan(24)
  })
})
