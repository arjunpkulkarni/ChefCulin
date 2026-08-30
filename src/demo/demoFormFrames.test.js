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
  it('maps common Foodb labels onto acid / salt / umami from FooDB compounds', () => {
    expect(axesFor('Lemon').acid).toBeGreaterThan(0.4)
    expect(axesFor('Soy sauce').glut).toBeGreaterThan(0.3)
    expect(axesFor('Soy sauce').salt).toBeGreaterThan(0.3)
    expect(axesFor('Vinegar').acid).toBeGreaterThan(0.25)
    expect(axesFor('miso').glut).toBeGreaterThan(0.3)
  })
})
