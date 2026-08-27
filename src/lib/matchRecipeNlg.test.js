import { describe, expect, it } from 'vitest'
import { heuristicRecipeNlg } from './matchRecipeNlg.js'

describe('heuristicRecipeNlg', () => {
  it('maps Foodb animal labels to recipe tokens', () => {
    expect(heuristicRecipeNlg('Cattle (Beef, Veal)')).toBe('beef')
    expect(heuristicRecipeNlg('Domestic pig')).toBe('pork')
    expect(heuristicRecipeNlg('Sheep (Mutton, Lamb)')).toBe('lamb')
    expect(heuristicRecipeNlg('Mallard duck')).toBe('duck')
    expect(heuristicRecipeNlg('Chicken')).toBe('chicken')
  })

  it('maps citrus Foodb names to orange', () => {
    expect(heuristicRecipeNlg('Sweet orange')).toBe('orange')
    expect(heuristicRecipeNlg('Mandarin orange (Clementine, Tangerine)')).toBe('orange')
  })
})
