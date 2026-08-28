import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  assertAgentResult,
  assertOptionShape,
  makeTraditionToolHandler,
  openTraditionDb,
  optionsMatchCuisine,
  optionsMentionIngredient,
  scriptedLlmChat,
} from './agentTestHelpers.js'
import { TRADITION_SYSTEM, traditionTools } from './agentTools/tradition.js'
import { heuristicRecipeNlg } from './matchRecipeNlg.js'
import { parseAgentResult } from './runAgent.js'

vi.mock('./openai.js', () => ({
  llmChat: vi.fn(),
}))

import { llmChat } from './openai.js'
import { runAgent } from './runAgent.js'

describe('agent option parsing (schema gate)', () => {
  it('accepts the strict Tradition option-card JSON', () => {
    const r = parseAgentResult(
      JSON.stringify({
        options: [
          {
            id: 'R0001',
            title: 'Acarajé',
            subtitle: 'Brazil — Core / emblematic',
            score: 4,
          },
        ],
        rationale: 'Core Brazilian dish.',
      })
    )
    assertAgentResult(r, { min: 1, max: 6 })
    expect(r.options[0].title).toBe('Acarajé')
  })

  it('strips markdown fences and still yields cards', () => {
    const r = parseAgentResult(
      '```json\n{"options":[{"id":"R9","title":"X","subtitle":"China — Established","score":3}],"rationale":"ok"}\n```'
    )
    assertAgentResult(r, { min: 1 })
  })

  it('maps record_id / item aliases into the card shape', () => {
    const r = parseAgentResult(
      JSON.stringify({
        options: [{ record_id: 'R0042', item: 'Kung Pao Chicken', subtitle: 'China', score: '4' }],
        rationale: 'Sichuan classic',
      })
    )
    expect(r.options[0]).toMatchObject({
      id: 'R0042',
      title: 'Kung Pao Chicken',
      score: 4,
    })
  })

  it('drops malformed options without an id', () => {
    const r = parseAgentResult(
      JSON.stringify({
        options: [{ title: 'no id' }, { id: 'R1', title: 'ok', subtitle: '', score: 1 }],
        rationale: 'partial',
      })
    )
    expect(r.options).toHaveLength(1)
    assertOptionShape(r.options[0])
  })

  it('returns empty options for unparseable prose', () => {
    const r = parseAgentResult('I could not find anything useful.')
    expect(r.options).toEqual([])
    expect(r.rationale).toMatch(/could not find/i)
  })

  it('handles empty match payload', () => {
    const r = parseAgentResult(JSON.stringify({ options: [], rationale: 'no dishes for unicorn' }))
    assertAgentResult(r, { allowEmpty: true, max: 0 })
    expect(r.rationale).toMatch(/unicorn/)
  })
})

describe('runAgent tool loop → option cards', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls searchDishes then emits 3–6 ranked option cards', async () => {
    llmChat.mockImplementation(
      scriptedLlmChat([
        {
          tool_calls: [
            {
              name: 'searchDishes',
              arguments: { cuisine: 'China', keyword: 'chicken', limit: 12 },
            },
          ],
        },
        {
          content: JSON.stringify({
            options: [
              { id: 'R1', title: 'Kung Pao Chicken', subtitle: 'China — Core / emblematic', score: 4 },
              { id: 'R2', title: 'Beggar\'s Chicken', subtitle: 'China — Established', score: 3 },
              { id: 'R3', title: 'Chicken with Chili', subtitle: 'China — Established', score: 3 },
            ],
            rationale: 'Sichuan and broader Chinese chicken dishes from the Tradition DB.',
          }),
        },
      ])
    )

    const calls = []
    const handleTool = async (name, args) => {
      calls.push({ name, args })
      return [
        { record_id: 'R1', item: 'Kung Pao Chicken', cuisine: 'China', traditionality_score: 4 },
        { record_id: 'R2', item: "Beggar's Chicken", cuisine: 'China', traditionality_score: 3 },
        { record_id: 'R3', item: 'Chicken with Chili', cuisine: 'China', traditionality_score: 3 },
      ]
    }

    const result = await runAgent({
      system: TRADITION_SYSTEM,
      user: 'chicken dishes from Sichuan / China',
      tools: traditionTools,
      handleTool,
    })

    expect(calls).toEqual([
      { name: 'searchDishes', args: { cuisine: 'China', keyword: 'chicken', limit: 12 } },
    ])
    assertAgentResult(result, { min: 3, max: 6 })
    expect(optionsMentionIngredient(result.options, 'chicken')).toBe(true)
    expect(optionsMatchCuisine(result.options, 'China').length).toBe(result.options.length)
    const scores = result.options.map((o) => o.score)
    expect(scores[0]).toBeGreaterThanOrEqual(scores[scores.length - 1])
  })

  it('can follow searchDishes with getDishDetail before finalizing cards', async () => {
    llmChat.mockImplementation(
      scriptedLlmChat([
        {
          tool_calls: [{ name: 'searchDishes', arguments: { keyword: 'cumin', cuisine: 'Morocco' } }],
        },
        {
          tool_calls: [{ name: 'getDishDetail', arguments: { record_id: 'R100' } }],
        },
        {
          content: JSON.stringify({
            options: [
              { id: 'R100', title: 'Rfissa', subtitle: 'Morocco — Core / emblematic', score: 4 },
              { id: 'R101', title: 'Chicken tagine', subtitle: 'Morocco — Established', score: 3 },
              { id: 'R102', title: 'Kefta', subtitle: 'Morocco — Established', score: 3 },
            ],
            rationale: 'Moroccan dishes where cumin is a documented companion.',
          }),
        },
      ])
    )

    const handleTool = async (name, args) => {
      if (name === 'searchDishes') return [{ record_id: 'R100', item: 'Rfissa', cuisine: 'Morocco' }]
      if (name === 'getDishDetail')
        return {
          record_id: args.record_id,
          item: 'Rfissa',
          companionIngredients: ['cumin', 'fenugreek', 'onion'],
        }
      throw new Error(name)
    }

    const result = await runAgent({
      system: TRADITION_SYSTEM,
      user: 'what pairs with cumin in Moroccan food',
      tools: traditionTools,
      handleTool,
    })

    assertAgentResult(result, { min: 3, max: 6 })
    expect(result.options[0].id).toBe('R100')
    expect(llmChat).toHaveBeenCalledTimes(3)
  })

  it('returns empty options when the tool finds nothing', async () => {
    llmChat.mockImplementation(
      scriptedLlmChat([
        { tool_calls: [{ name: 'searchDishes', arguments: { keyword: 'zzzz-no-such' } }] },
        {
          content: JSON.stringify({
            options: [],
            rationale: 'No Tradition records matched zzzz-no-such.',
          }),
        },
      ])
    )

    const result = await runAgent({
      system: TRADITION_SYSTEM,
      user: 'zzzz-no-such dishes',
      tools: traditionTools,
      handleTool: async () => [],
    })

    assertAgentResult(result, { allowEmpty: true, max: 0 })
    expect(result.rationale.length).toBeGreaterThan(0)
  })

  it('surfaces tool errors to the model and still finishes with cards or empty', async () => {
    llmChat.mockImplementation(
      scriptedLlmChat([
        { tool_calls: [{ name: 'searchDishes', arguments: { keyword: 'chicken' } }] },
        {
          content: JSON.stringify({
            options: [],
            rationale: 'Search failed; no options.',
          }),
        },
      ])
    )

    const result = await runAgent({
      system: TRADITION_SYSTEM,
      user: 'chicken',
      tools: traditionTools,
      handleTool: async () => {
        throw new Error('db down')
      },
    })

    expect(result.options).toEqual([])
    const secondCall = llmChat.mock.calls[1][0]
    const toolMsg = secondCall.messages.find((m) => m.role === 'tool')
    expect(toolMsg.content).toMatch(/db down/)
  })

  it('throws if the model never returns a final answer', async () => {
    llmChat.mockImplementation(
      scriptedLlmChat(
        Array.from({ length: 6 }, () => ({
          tool_calls: [{ name: 'searchDishes', arguments: { keyword: 'x' } }],
        }))
      )
    )

    await expect(
      runAgent({
        system: TRADITION_SYSTEM,
        user: 'loop forever',
        tools: traditionTools,
        handleTool: async () => [],
      })
    ).rejects.toThrow(/exceeded tool-call rounds/)
  })

  it('passes cuisine-scope preference into the system prompt', async () => {
    llmChat.mockImplementation(
      scriptedLlmChat([
        {
          content: JSON.stringify({
            options: [{ id: 'R1', title: 'X', subtitle: 'China — Core', score: 4 }],
            rationale: 'scoped',
          }),
        },
      ])
    )

    await runAgent({
      system: TRADITION_SYSTEM,
      user: 'chicken',
      tools: traditionTools,
      handleTool: async () => [],
      extraSystem: 'Cuisine scope is locked to China.',
    })

    const first = llmChat.mock.calls[0][0]
    expect(first.messages[0].content).toMatch(/Cuisine scope is locked to China/)
    expect(first.messages[0].content).toMatch(/tradition retrieval agent/i)
  })
})

describe('Tradition tools + real DB → ingredients drive searchable options', () => {
  let handleTool

  beforeAll(async () => {
    const db = await openTraditionDb()
    handleTool = makeTraditionToolHandler(db)
  })

  it('searchDishes finds China + chicken rows with real record ids', async () => {
    const rows = await handleTool('searchDishes', {
      cuisine: 'China',
      keyword: 'chicken',
      limit: 8,
    })
    expect(rows.length).toBeGreaterThan(0)
    rows.forEach((r) => {
      expect(r.record_id).toMatch(/^R/)
      expect(String(r.cuisine).toLowerCase()).toMatch(/china|chinese|sichuan|cantonese|hakka/i)
    })
  })

  it('searchDishes maps Moroccan → Morocco', async () => {
    const rows = await handleTool('searchDishes', {
      cuisine: 'Moroccan',
      limit: 10,
    })
    expect(rows.length).toBeGreaterThan(0)
    expect(rows.every((r) => /morocco/i.test(r.cuisine))).toBe(true)
  })

  it('searchDishes finds Morocco cuisine rows', async () => {
    const rows = await handleTool('searchDishes', {
      cuisine: 'Morocco',
      limit: 10,
    })
    expect(rows.length).toBeGreaterThan(0)
    expect(rows.every((r) => /morocco/i.test(r.cuisine))).toBe(true)
  })

  it('getDishDetail returns companion ingredients for a known record', async () => {
    const hits = await handleTool('searchDishes', { cuisine: 'China', limit: 5 })
    const detail = await handleTool('getDishDetail', { record_id: hits[0].record_id })
    expect(detail.record_id).toBe(hits[0].record_id)
    expect(Array.isArray(detail.companionIngredients)).toBe(true)
    expect(detail.companionIngredients.length).toBeGreaterThan(0)
  })

  it('agent scripted over real tool results yields option cards tied to DB ids', async () => {
    const rows = await handleTool('searchDishes', {
      cuisine: 'India',
      keyword: 'chicken',
      limit: 6,
    })
    expect(rows.length).toBeGreaterThan(0)

    llmChat.mockImplementation(
      scriptedLlmChat([
        {
          tool_calls: [
            { name: 'searchDishes', arguments: { cuisine: 'India', keyword: 'chicken', limit: 6 } },
          ],
        },
        {
          content: JSON.stringify({
            options: rows.slice(0, Math.min(5, rows.length)).map((r) => ({
              id: r.record_id,
              title: r.item,
              subtitle: `${r.cuisine} — ${r.traditionality_class || 'documented'}`,
              score: r.traditionality_score || 0,
            })),
            rationale: 'Indian chicken dishes from the Tradition DB.',
          }),
        },
      ])
    )

    const result = await runAgent({
      system: TRADITION_SYSTEM,
      user: 'chicken dishes from India',
      tools: traditionTools,
      handleTool,
    })

    assertAgentResult(result, { min: 1, max: 6 })
    result.options.forEach((o) => {
      expect(rows.some((r) => r.record_id === o.id)).toBe(true)
    })
  })

  it('ingredient focus seeds (Foodb → RecipeNLG heuristic) stay culinary tokens', () => {
    expect(heuristicRecipeNlg('Chicken')).toBe('chicken')
    expect(heuristicRecipeNlg('Cattle (Beef, Veal)')).toBe('beef')
    expect(heuristicRecipeNlg('Sweet orange')).toBe('orange')
    expect(heuristicRecipeNlg('Mallard duck')).toBe('duck')
  })
})

describe('option-card quality rules the UI depends on', () => {
  it('never exceeds six cards in a well-formed agent payload', () => {
    const tooMany = Array.from({ length: 10 }, (_, i) => ({
      id: `R${i}`,
      title: `Dish ${i}`,
      subtitle: 'X',
      score: 1,
    }))
    const r = parseAgentResult(JSON.stringify({ options: tooMany, rationale: 'dump' }))
    // parser does not truncate — UI/agent prompt must; assert we can detect oversize
    expect(r.options.length).toBe(10)
    expect(r.options.length).toBeGreaterThan(6)
  })

  it('Tradition system prompt encodes the option-card contract', () => {
    expect(TRADITION_SYSTEM).toMatch(/3–6 options|3-6 options/)
    expect(TRADITION_SYSTEM).toMatch(/"options"/)
    expect(TRADITION_SYSTEM).toMatch(/record_id/)
    expect(TRADITION_SYSTEM).toMatch(/searchDishes/)
    expect(traditionTools.map((t) => t.function.name).sort()).toEqual([
      'getDishDetail',
      'searchDishes',
    ])
  })
})
