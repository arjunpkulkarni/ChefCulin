/**
 * Map Foodb / UI ingredient names → RecipeNLG-style seeds via OpenAI.
 * Corpus tables use simple lowercase tokens (chicken, orange, beef); Foodb uses
 * "Cattle (Beef, Veal)", "Sweet orange", "Mallard duck", etc.
 */
import { llmChat } from '../api.js'
import { seedKey } from '../data/ingredients.js'

const MEMORY = new Map()
const STORAGE_KEY = 'culin.recipenlg.match.v1'

const SYSTEM = `You map culinary ingredient names to RecipeNLG corpus tokens.
RecipeNLG uses short, everyday English ingredient names in lowercase — the kind that appear in US home-cooking recipes (e.g. chicken, beef, orange, garlic, onion, soy sauce, duck).

Rules:
- Return ONE best canonical token that cooks would write in a recipe ingredient list.
- Prefer the edible culinary name over taxonomic/scientific labels.
- Examples:
  - "Cattle (Beef, Veal)" → "beef"
  - "Sweet orange" → "orange"
  - "Mallard duck" → "duck"
  - "Sheep (Mutton, Lamb)" → "lamb"
  - "Domestic pig" → "pork"
  - "Chicken" → "chicken"
  - "Shiitake" → "shiitake"
  - "Mandarin orange (Clementine, Tangerine)" → "orange"
- Do NOT invent multi-word phrases unless they are standard recipe tokens (olive oil, soy sauce, fish sauce, coconut milk).
- If unsure, pick the simplest edible synonym.
- Reply with ONLY a JSON object: {"canonical":"<token>","confidence":0-1,"rationale":"<short>"}`

function loadStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const obj = JSON.parse(raw)
    Object.entries(obj).forEach(([k, v]) => {
      if (typeof v === 'string' && v) MEMORY.set(k, v)
    })
  } catch {
    /* ignore */
  }
}

function saveStorage(key, value) {
  try {
    const obj = {}
    MEMORY.forEach((v, k) => {
      obj[k] = v
    })
    obj[key] = value
    localStorage.setItem(STORAGE_KEY, JSON.stringify(obj))
  } catch {
    /* ignore quota */
  }
}

loadStorage()

/** Deterministic guesses before calling the LLM. */
export function heuristicRecipeNlg(name) {
  const raw = String(name || '').trim()
  if (!raw) return 'chicken'

  // Prefer parenthetical culinary names: "Cattle (Beef, Veal)" → beef
  const paren = raw.match(/\(([^)]+)\)/)
  if (paren) {
    const parts = paren[1]
      .split(/[,/]/)
      .map((p) => p.trim().toLowerCase())
      .filter(Boolean)
    const preferred = parts.find((p) =>
      /^(beef|veal|pork|lamb|mutton|duck|chicken|turkey|goat|orange)$/.test(p)
    )
    if (preferred) return preferred === 'mutton' ? 'lamb' : preferred
    // Mandarin orange (Clementine, Tangerine) → orange from outer name
    if (/\borange\b/i.test(raw)) return 'orange'
    if (parts[0]) return parts[0].replace(/\s+/g, ' ')
  }

  let s = raw.toLowerCase()
  s = s.replace(/\b(mallard|velvet|domestic|european|wild)\b/g, '').trim()
  s = s.replace(/\b(sweet|sour|bitter)\s+(orange|cherry|apple)\b/g, '$2')
  s = s.replace(/\s+/g, ' ').trim()

  const known = {
    chicken: 'chicken',
    turkey: 'turkey',
    garlic: 'garlic',
    rosemary: 'rosemary',
    shiitake: 'shiitake',
    miso: 'miso',
    cinnamon: 'cinnamon',
  }
  if (known[s]) return known[s]
  if (/duck/.test(s)) return 'duck'
  if (/cattle|beef/.test(s)) return 'beef'
  if (/pig|pork/.test(s)) return 'pork'
  if (/sheep|lamb|mutton/.test(s)) return 'lamb'
  if (/orange/.test(s)) return 'orange'

  return seedKey(s)
}

/**
 * Resolve a display/Foodb name to a RecipeNLG corpus token.
 * Uses cache → LLM → heuristic fallback.
 *
 * @returns {Promise<{ canonical: string, source: 'cache'|'llm'|'heuristic', rationale?: string }>}
 */
export async function matchRecipeNlg(name, { force = false } = {}) {
  const display = String(name || '').trim()
  const cacheKey = display.toLowerCase()
  if (!force && MEMORY.has(cacheKey)) {
    return { canonical: MEMORY.get(cacheKey), source: 'cache' }
  }

  const fallback = heuristicRecipeNlg(display)

  try {
    const data = await llmChat({
      messages: [
        { role: 'system', content: SYSTEM },
        {
          role: 'user',
          content: `Foodb / UI name: ${display}\nHeuristic guess: ${fallback}\nReturn the RecipeNLG token JSON.`,
        },
      ],
      temperature: 0,
    })
    const content = data?.choices?.[0]?.message?.content || ''
    const parsed = parseJson(content)
    const canonical = normalizeToken(parsed?.canonical) || fallback
    MEMORY.set(cacheKey, canonical)
    saveStorage(cacheKey, canonical)
    return {
      canonical,
      source: 'llm',
      rationale: typeof parsed?.rationale === 'string' ? parsed.rationale : undefined,
      confidence: typeof parsed?.confidence === 'number' ? parsed.confidence : undefined,
    }
  } catch {
    MEMORY.set(cacheKey, fallback)
    saveStorage(cacheKey, fallback)
    return { canonical: fallback, source: 'heuristic' }
  }
}

function normalizeToken(s) {
  if (!s || typeof s !== 'string') return null
  return s
    .trim()
    .toLowerCase()
    .replace(/[_/]+/g, ' ')
    .replace(/\s+/g, ' ')
}

function parseJson(text) {
  const t = String(text || '').trim()
  const fenced = t.match(/```(?:json)?\s*([\s\S]*?)```/i)
  const body = fenced ? fenced[1].trim() : t
  const start = body.indexOf('{')
  const end = body.lastIndexOf('}')
  if (start < 0 || end <= start) return null
  try {
    return JSON.parse(body.slice(start, end + 1))
  } catch {
    return null
  }
}

/** Test helper */
export function _clearMatchCache() {
  MEMORY.clear()
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}
