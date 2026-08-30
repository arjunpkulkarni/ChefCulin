/**
 * LLM-generated preparation frames for the focus ingredient.
 * No static preset menus — cards are built per ingredient at runtime.
 */
import { llmChat } from './openai.js'
import { lookupIngredient } from '../data/ingredients.js'
import { registerFrame } from './frameRegistry.js'

const CACHE = new Map()

const SYSTEM = `You are a culinary process advisor. Given one focus ingredient, return preparation frames chefs actually use with it.

Reply with ONLY JSON:
{
  "rationale": "one sentence on how you chose these frames",
  "forms": [
    {
      "name": "Short frame name",
      "title": "Title — what the cook is doing",
      "desc": "One sentence on the process",
      "craft": [{"k":"Texture","v":"..."},{"k":"Temp","v":"..."},{"k":"Sauce","v":"..."}],
      "balance": {
        "produces": ["tender","crisp-skin"],
        "absent": ["long-cook"],
        "overlay": "sear",
        "fat": 0.55,
        "overlayNote": "How aromatics behave in this frame for this ingredient"
      }
    }
  ]
}

Rules:
- Return 6–9 frames, ranked by how natural they are for THIS ingredient.
- "produces" / "absent" use culinary property tokens like: crisp-skin, tender, rendered-fat, dispersed-fat, liquid-body, long-cook, cold, salt-cured, smoke-phenols, fresh-crunch, sauce-medium, intact-roast.
- "overlay" must be one of: sear, roast, confit, cure, broth, braise, ground, smoke, terrine, raw.
- Be specific to the ingredient — not a generic meat checklist unless it is meat.`

function parsePayload(text) {
  const raw = String(text || '').trim()
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i)
  const body = fenced ? fenced[1].trim() : raw
  const start = body.indexOf('{')
  const end = body.lastIndexOf('}')
  if (start < 0 || end <= start) return null
  try {
    return JSON.parse(body.slice(start, end + 1))
  } catch {
    return null
  }
}

function normalizeCard(row) {
  if (!row || typeof row !== 'object') return null
  const name = String(row.name || '').trim()
  if (!name) return null
  const craft = Array.isArray(row.craft)
    ? row.craft
        .map((c) => ({ k: String(c.k || '').trim(), v: String(c.v || '').trim() }))
        .filter((c) => c.k && c.v)
    : []
  if (craft.length < 2) return null
  registerFrame(name, row.balance || {})
  return {
    name,
    title: String(row.title || name).trim(),
    desc: String(row.desc || '').trim() || name,
    craft,
  }
}

/**
 * @returns {Promise<{ forms: object[], source: 'llm'|'cache'|'empty'|'error', rationale?: string, error?: string }>}
 */
export async function fetchFormCards(ingredient, { force = false } = {}) {
  const name = String(ingredient || '').trim()
  if (!name) {
    return { forms: [], source: 'empty', error: 'Choose a focus ingredient first.' }
  }
  if (!force && CACHE.has(name)) return CACHE.get(name)

  const row = lookupIngredient(name)
  const foodb = row
    ? `Foodb name: ${row.name}\nGroup: ${row.food_group}\nSubgroup: ${row.food_subgroup}`
    : `Ingredient: ${name}`

  try {
    const data = await llmChat({
      messages: [
        { role: 'system', content: SYSTEM },
        { role: 'user', content: foodb },
      ],
      temperature: 0.35,
      response_format: { type: 'json_object' },
    })
    const content = data?.choices?.[0]?.message?.content || ''
    const parsed = parsePayload(content)
    const forms = (parsed?.forms || []).map(normalizeCard).filter(Boolean)
    if (!forms.length) {
      const err = { forms: [], source: 'error', error: 'LLM returned no usable form cards.' }
      return err
    }
    const result = {
      forms,
      source: 'llm',
      rationale: typeof parsed?.rationale === 'string' ? parsed.rationale : undefined,
    }
    CACHE.set(name, result)
    return result
  } catch (err) {
    return {
      forms: [],
      source: 'error',
      error: err?.message || String(err),
    }
  }
}

/** @internal tests */
export function _clearFormCache() {
  CACHE.clear()
}
