/**
 * Offline dataset reliability — Tradition DB + Foodb + heuristics.
 * No API server or OpenAI required.
 */
import { afterAll, describe, expect, it } from 'vitest'
import {
  checkFoodbInventory,
  checkRecipeNlgHeuristics,
  formatReport,
} from './reliability/checks.js'
import {
  checkRegionPicksNode,
  checkTraditionAnchorsNode,
  checkTraditionAssociationNode,
  checkTraditionScaleNode,
} from './reliability/traditionNode.js'

const results = []

function record(r) {
  results.push(r)
  expect(r.ok, `${r.label}: ${r.detail}`).toBe(true)
}

describe('reliability — offline datasets', () => {
  it('Foodb inventory is complete and deduplicated', () => {
    record(checkFoodbInventory())
  })

  it('RecipeNLG heuristic mapping is stable for Foodb names', () => {
    record(checkRecipeNlgHeuristics())
  })

  it('Tradition DB has expected scale', async () => {
    record(await checkTraditionScaleNode())
  })

  it('Tradition DB returns resolvable matches for anchor ingredients', async () => {
    for (const r of await checkTraditionAnchorsNode()) record(r)
  })

  it('Tradition association graph has companions and threads for chicken', async () => {
    record(await checkTraditionAssociationNode())
  })

  it('Cuisine scope picks come from documented Tradition rows', async () => {
    record(await checkRegionPicksNode())
  })
})

afterAll(() => {
  console.log(formatReport(results))
})
