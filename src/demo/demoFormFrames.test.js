import { describe, expect, it } from 'vitest'
import { FORM_CARDS, FORM_LIBRARY, formsForIngredient } from '../data/formCards.js'
import { FRAMES, axesFor } from '../data/domain.js'

describe('demo Form frames', () => {
  it('every library card has a matching FRAMES entry', () => {
    Object.values(FORM_LIBRARY).forEach((card) => {
      expect(FRAMES[card.name], card.name).toBeTruthy()
      expect(card.craft.length).toBeGreaterThan(0)
      expect(card.desc.length).toBeGreaterThan(0)
    })
  })

  it('animal foods still get sear/confit/braise', () => {
    const names = formsForIngredient('Chicken').map((c) => c.name)
    expect(names).toEqual(expect.arrayContaining(['Seared', 'Confit', 'Braise']))
    expect(FORM_CARDS.map((c) => c.name)).toEqual(expect.arrayContaining(['Seared', 'Confit']))
  })

  it('fruit and herbs do not inherit the duck confit menu', () => {
    const lemon = formsForIngredient('Lemon').map((c) => c.name)
    expect(lemon).toEqual(expect.arrayContaining(['Fresh / raw', 'Pickled', 'Roasted']))
    expect(lemon).not.toContain('Confit')
    expect(lemon).not.toContain('Terrine / rillette')

    const herb = formsForIngredient('Rosemary').map((c) => c.name)
    expect(herb).toEqual(expect.arrayContaining(['Fresh garnish', 'Infused', 'Bloomed in fat']))
    expect(herb).not.toContain('Crisp-skinned roast')
  })
})

describe('Foodb names move the balance axes', () => {
  it('maps common Foodb labels onto acid / salt / heat', () => {
    expect(axesFor('Lemon')).toMatchObject({ acid: 1 })
    expect(axesFor('Soy sauce')).toMatchObject({ glut: 1, salt: 1 })
    expect(axesFor('Vinegar')).toMatchObject({ acid: 1 })
    expect(axesFor('miso')).toMatchObject({ glut: 1, salt: 1 })
  })
})
