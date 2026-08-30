/**
 * Curated reliability expectations — grounded in vendor graph + corpus artifacts.
 * These are falsifiable checks, not subjective "tastes right" judgments.
 */

/** @typedef {{ id: string, label: string, run: (ctx: object) => Promise<{ ok: boolean, detail?: string }> }} ReliabilityCheck */

export const MIN_HEALTH = {
  cooccur_edges: 10_000,
  compound_edges: 5_000,
  technique_edges: 1_000,
  tradition_records: 200,
  foodb_ingredients: 900,
}

/** Compound lens — flavor-network (vendor CSV → neighbors.jsonl). */
export const COMPOUND_ANCHORS = [
  {
    focus: 'Garlic',
    token: 'garlic',
    minNeighbors: 5,
    mustInclude: ['white_wine', 'beer'],
    topNeighbor: 'white_wine',
    forbidSameBase: ['garlic', 'raw_garlic', 'fried_garlic'],
  },
  {
    focus: 'Chicken',
    token: 'chicken',
    minNeighbors: 3,
    mustInclude: [],
    forbidSameBase: ['chicken', 'fried_chicken', 'roasted_chicken', 'raw_chicken'],
  },
]

/** Co-occurrence lens — RecipeNLG NPMI artifacts. */
export const COOCCUR_ANCHORS = [
  {
    seed: 'garlic',
    minNeighbors: 5,
    mustInclude: ['olive oil', 'oregano'],
    sortedBy: 'confidence',
  },
  {
    seed: 'duck',
    minNeighbors: 4,
    mustInclude: ['onion', 'butter'],
    sortedBy: 'confidence',
  },
  {
    seed: 'chicken',
    minNeighbors: 4,
    mustInclude: ['rice'],
    sortedBy: 'confidence',
  },
]

/** Tradition DB — documented dishes must resolve and mention the focus. */
export const TRADITION_ANCHORS = [
  { focus: 'Chicken', minMatches: 3, cuisine: null },
  { focus: 'Garlic', minMatches: 1, cuisine: null },
  { focus: 'Chicken', minMatches: 1, cuisine: 'China' },
]

/** Foodb → RecipeNLG mapping (heuristic path — always available offline). */
export const RECIPE_NLG_HEURISTIC = [
  ['Cattle (Beef, Veal)', 'beef'],
  ['Sweet orange', 'orange'],
  ['Mallard duck', 'duck'],
  ['Domestic pig', 'pork'],
  ['Chicken', 'chicken'],
]
