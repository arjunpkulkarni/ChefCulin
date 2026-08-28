/**
 * Live Tradition agent tests — real OpenAI + real Tradition SQLite.
 *
 * Skips unless VITE_OPENAI_API_KEY or OPENAI_API_KEY is set:
 *   VITE_OPENAI_API_KEY=sk-... npm run test:agent:live
 *
 * Never hardcode keys in this file.
 */
import { beforeAll, describe, expect, it, vi } from 'vitest'
import {
  assertAgentResult,
  makeTraditionToolHandler,
  openTraditionDb,
  optionsMatchCuisine,
  optionsMentionIngredient,
} from './agentTestHelpers.js'
import { TRADITION_SYSTEM, traditionTools } from './agentTools/tradition.js'

const HAS_KEY = Boolean(
  process.env.VITE_OPENAI_API_KEY?.trim() || process.env.OPENAI_API_KEY?.trim()
)

vi.mock('./openai.js', async () => {
  const { openAiChat } = await import('./agentTestHelpers.js')
  return {
    llmChat: vi.fn(async (body) => openAiChat(body)),
    openaiConfigured: () => HAS_KEY,
  }
})

import { runAgent } from './runAgent.js'
import { matchRecipeNlg, _clearMatchCache } from './matchRecipeNlg.js'

describe.skipIf(!HAS_KEY)('live Tradition agent — option cards from real LLM + DB', () => {
  let handleTool

  beforeAll(async () => {
    const db = await openTraditionDb()
    handleTool = makeTraditionToolHandler(db)
  }, 60_000)

  async function ask(user, extraSystem = '') {
    return runAgent({
      system: TRADITION_SYSTEM,
      user,
      tools: traditionTools,
      handleTool,
      extraSystem,
    })
  }

  it(
    'returns 3–6 option cards for China / chicken with DB record ids',
    async () => {
      const result = await ask('chicken dishes from China, especially Sichuan if present')
      assertAgentResult(result, { min: 3, max: 6 })
      expect(optionsMentionIngredient(result.options, 'chicken') || result.rationale.toLowerCase().includes('chicken')).toBe(
        true
      )
      const chinaish = optionsMatchCuisine(result.options, 'China')
      expect(chinaish.length).toBeGreaterThan(0)
      for (const o of result.options) {
        const detail = await handleTool('getDishDetail', { record_id: o.id })
        expect(detail.error).toBeUndefined()
        expect(detail.item).toBeTruthy()
      }
    },
    90_000
  )

  it(
    'returns Moroccan options when asked about Morocco',
    async () => {
      const result = await ask('documented Moroccan dishes from the Tradition database')
      assertAgentResult(result, { min: 1, max: 6 })
      expect(
        optionsMatchCuisine(result.options, 'Morocco').length > 0 ||
          /morocco/i.test(result.rationale)
      ).toBe(true)
      for (const o of result.options) {
        const detail = await handleTool('getDishDetail', { record_id: o.id })
        expect(detail.error).toBeUndefined()
      }
    },
    90_000
  )

  it(
    'cumin + Morocco ask still yields valid card ids when options are returned',
    async () => {
      const result = await ask('Moroccan dishes that use cumin or warm spices')
      assertAgentResult(result, { allowEmpty: true, max: 6 })
      expect(result.rationale.length).toBeGreaterThan(5)
      for (const o of result.options) {
        const detail = await handleTool('getDishDetail', { record_id: o.id })
        expect(detail.error).toBeUndefined()
      }
    },
    90_000
  )

  it(
    'returns empty options honestly for nonsense cuisine/ingredient asks',
    async () => {
      const result = await ask(
        'traditional dishes of Atlantis featuring unicorn marrow and fairy dust'
      )
      assertAgentResult(result, { allowEmpty: true, max: 6 })
      // Prefer empty; if the model still returns something, ids must still resolve
      for (const o of result.options) {
        const detail = await handleTool('getDishDetail', { record_id: o.id })
        expect(detail.error).toBeUndefined()
      }
      expect(result.rationale.length).toBeGreaterThan(5)
    },
    90_000
  )

  it(
    'respects cuisine scope preference in the extra system prompt',
    async () => {
      const result = await ask('chicken dishes', 'Cuisine scope is locked to Japan. Prefer Japanese matches.')
      assertAgentResult(result, { min: 1, max: 6 })
      const jp = optionsMatchCuisine(result.options, 'Japan')
      // Soft assert: most cards should be Japan when scope is locked
      expect(jp.length).toBeGreaterThanOrEqual(Math.min(1, result.options.length))
    },
    90_000
  )

  it(
    'India + chicken yields cards whose titles or cuisine reference the ask',
    async () => {
      const result = await ask('documented chicken dishes from India')
      assertAgentResult(result, { min: 2, max: 6 })
      const relevant = result.options.filter(
        (o) =>
          /india|chicken/i.test(o.title) ||
          /india|chicken/i.test(o.subtitle) ||
          /india/i.test(result.rationale)
      )
      expect(relevant.length).toBeGreaterThan(0)
    },
    90_000
  )
})

describe.skipIf(!HAS_KEY)('live Foodb → RecipeNLG name matching', () => {
  beforeAll(() => {
    _clearMatchCache()
  })

  const cases = [
    ['Cattle (Beef, Veal)', ['beef', 'veal']],
    ['Sweet orange', ['orange']],
    ['Mallard duck', ['duck']],
    ['Domestic pig', ['pork']],
    ['Sheep (Mutton, Lamb)', ['lamb', 'mutton']],
    ['Chicken', ['chicken']],
    ['Shiitake', ['shiitake', 'mushroom']],
  ]

  it.each(cases)(
    'maps %s to a RecipeNLG-like token',
    async (foodb, allowed) => {
      const { canonical, source } = await matchRecipeNlg(foodb, { force: true })
      expect(source).toMatch(/llm|cache|heuristic/)
      expect(allowed.some((a) => canonical === a || canonical.includes(a))).toBe(true)
    },
    60_000
  )
})
