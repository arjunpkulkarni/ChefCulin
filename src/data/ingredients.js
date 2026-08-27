/**
 * Culinary ingredient list — Foodb-derived (933 foods).
 * Source: culin-wiki-test/data/processed/ingredients.json
 */
import raw from './ingredients.json'

export const INGREDIENTS = raw

export const DEFAULT_FOCUS = 'Chicken'

/** Display names, sorted. */
export const INGREDIENT_LIST = INGREDIENTS.map((r) => r.name).sort((a, b) =>
  a.localeCompare(b)
)

const byNameLower = new Map()
for (const row of INGREDIENTS) {
  byNameLower.set(row.name.toLowerCase(), row)
}

export function lookupIngredient(name) {
  if (!name) return null
  return byNameLower.get(String(name).toLowerCase()) || null
}

/** Seed string for corpus / Tradition queries (lowercase). */
export function seedKey(name) {
  return String(name || DEFAULT_FOCUS).trim().toLowerCase()
}

/**
 * Compound lens groups = Foodb food_group buckets.
 * Chips are real Foodb names; focus ingredient is excluded.
 */
export function compoundGroups(focusIngredient = DEFAULT_FOCUS, { perGroup = 24 } = {}) {
  const focusLower = String(focusIngredient || '').toLowerCase()
  const buckets = new Map()
  for (const row of INGREDIENTS) {
    if (row.name.toLowerCase() === focusLower) continue
    const g = row.food_group || 'Other'
    if (!buckets.has(g)) buckets.set(g, [])
    buckets.get(g).push(row)
  }

  const order = [
    'Herbs and Spices',
    'Vegetables',
    'Fruits',
    'Aquatic foods',
    'Animal foods',
    'Cereals and cereal products',
    'Pulses',
    'Nuts',
    'Milk and milk products',
    'Soy',
    'Baking goods',
    'Confectioneries',
    'Cocoa and cocoa products',
    'Beverages',
    'Gourds',
  ]

  const titles = [
    ...order.filter((t) => buckets.has(t)),
    ...[...buckets.keys()].filter((t) => !order.includes(t)).sort(),
  ]

  return titles.map((title) => {
    const rows = buckets.get(title) || []
    const chips = rows
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name))
      .slice(0, perGroup)
      .map((r) => r.name)
    return {
      title,
      thread: null,
      posture: 'foodb',
      postureClass: 'p-est',
      why: `${rows.length} foods in Foodb · ${title}. Showing ${chips.length}${
        rows.length > chips.length ? ` of ${rows.length}` : ''
      }.`,
      region: null,
      chips,
      extend: null,
      whyBox: {
        sections: [
          {
            label: 'Source · Foodb',
            className: '',
            text: 'Compound browses the shared culinary ingredient list — not a protein-specific pairing guide. Pick by chemical/culinary family; Tradition and Co-occurrence answer what cooks actually documented.',
          },
        ],
        requires: null,
        thread: null,
      },
      lens: 'compound',
    }
  })
}

export function searchIngredients(query, { limit = 40 } = {}) {
  const q = String(query || '')
    .trim()
    .toLowerCase()
  if (!q) return INGREDIENT_LIST.slice(0, limit)
  const hits = []
  for (const name of INGREDIENT_LIST) {
    if (name.toLowerCase().includes(q)) hits.push(name)
    if (hits.length >= limit) break
  }
  return hits
}
