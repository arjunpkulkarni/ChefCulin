/**
 * Live reliability — API artifacts + optional OpenAI.
 *
 *   npm run demo          # in another terminal
 *   npm run test:reliability:live
 *
 * Skips when API is down. LLM checks skip without VITE_OPENAI_API_KEY.
 */
// @vitest-environment node
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import * as api from '../api.js'
import { openaiConfigured } from './openai.js'
import {
  assertAgentResult,
  makeTraditionToolHandler,
  openTraditionDb,
  optionsMatchCuisine,
} from './agentTestHelpers.js'
import { TRADITION_SYSTEM, traditionTools } from './agentTools/tradition.js'
import { runAgent } from './runAgent.js'
import {
  checkAssociateIntegrity,
  checkCooccurAnchors,
  checkCompoundAnchors,
  checkFormSchemaLive,
  checkHealth,
  formatReport,
} from './reliability/checks.js'
import { makeTraditionDbNode } from './reliability/traditionNode.js'

const BASE = process.env.CULIN_API || import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001'

async function probe() {
  try {
    const url = BASE.startsWith('http') ? `${BASE}/health` : `http://127.0.0.1:8001/health`
    const res = await fetch(url, { signal: AbortSignal.timeout(2000) })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

const health = await probe()
const apiLive = Boolean(health)
const llmLive = openaiConfigured()

if (!apiLive) {
  console.log(`[reliability:live] API not reachable at ${BASE} — skipping live dataset checks.`)
}
if (!llmLive) {
  console.log('[reliability:live] VITE_OPENAI_API_KEY not set — skipping LLM/agent checks.')
}

const results = []
function record(r) {
  results.push(r)
  expect(r.ok, `${r.label}: ${r.detail}`).toBe(true)
}

describe.skipIf(!apiLive)('reliability — live artifact API', () => {
  it('health and artifact scale', async () => {
    record(await checkHealth(api))
  })

  it('compound neighbors match flavor-network anchors', async () => {
    for (const r of await checkCompoundAnchors(api)) record(r)
  })

  it('corpus NPMI neighbors match RecipeNLG anchors', async () => {
    for (const r of await checkCooccurAnchors(api)) record(r)
  })

  it('associate merges three lenses without invented provenance', async () => {
    record(await checkAssociateIntegrity(api, { traditionDb: makeTraditionDbNode() }))
  })
})

describe.skipIf(!llmLive)('reliability — live LLM outputs', () => {
  it('form cards for Chicken are valid LLM JSON', async () => {
    record(await checkFormSchemaLive())
  }, 60_000)
})

describe.skipIf(!llmLive)('reliability — live agent + Tradition DB', () => {
  let handleTool

  beforeAll(async () => {
    const db = await openTraditionDb()
    handleTool = makeTraditionToolHandler(db)
  }, 60_000)

  it('agent option ids resolve in Tradition DB', async () => {
    const result = await runAgent({
      system: TRADITION_SYSTEM,
      user: 'documented chicken dishes from China',
      tools: traditionTools,
      handleTool,
    })
    assertAgentResult(result, { min: 2, max: 6 })
    const fails = []
    for (const o of result.options) {
      const detail = await handleTool('getDishDetail', { record_id: o.id })
      if (detail.error) fails.push(`${o.id}: ${detail.error}`)
    }
    if (!optionsMatchCuisine(result.options, 'China').length && !/china/i.test(result.rationale)) {
      fails.push('no China signal in options or rationale')
    }
    record({
      id: 'agent.tradition.china',
      label: 'Agent cards reference real Tradition records',
      ok: fails.length === 0,
      detail: fails.join('; ') || result.options.map((o) => o.title).join(', '),
    })
  }, 90_000)
})

afterAll(() => {
  if (results.length) console.log(formatReport(results))
})
