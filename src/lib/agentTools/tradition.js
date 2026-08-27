import { getDishDetail, searchDishes } from '../traditionDb.js'

/** OpenAI function-calling tools for the Tradition panel. Handlers run client-side. */

export const traditionTools = [
  {
    type: 'function',
    function: {
      name: 'searchDishes',
      description:
        'Search traditional culinary use records by cuisine, source thread, item type, and/or free-text keyword. Returns a short list of matching dishes.',
      parameters: {
        type: 'object',
        properties: {
          cuisine: { type: 'string', description: 'Cuisine or country name fragment, e.g. Sichuan, China, Morocco' },
          source_thread: { type: 'string', description: 'Named tradition thread if known' },
          item_type: { type: 'string', description: 'Record item type filter if known' },
          keyword: {
            type: 'string',
            description: 'Free-text match against dish name, use, preparation, region, tags',
          },
          limit: { type: 'integer', description: 'Max rows (default 12, max 24)' },
        },
        additionalProperties: false,
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'getDishDetail',
      description:
        'Fetch one use_records row by record_id or dish_id, including companion ingredients.',
      parameters: {
        type: 'object',
        properties: {
          record_id: { type: 'string' },
          dish_id: { type: 'string' },
        },
        additionalProperties: false,
      },
    },
  },
]

export async function handleTraditionTool(name, args) {
  if (name === 'searchDishes') {
    const rows = await searchDishes({
      cuisine: args.cuisine,
      source_thread: args.source_thread,
      item_type: args.item_type,
      keyword: args.keyword,
      limit: args.limit ?? 12,
    })
    return rows.map((r) => ({
      record_id: r.record_id,
      dish_id: r.dish_id,
      item: r.item,
      cuisine: r.cuisine,
      country: r.country,
      traditionality_class: r.traditionality_class,
      traditionality_score: r.traditionality_score,
      source_thread: r.source_thread,
      region_or_community: r.region_or_community,
      preparation_or_function: r.preparation_or_function,
      confidence: r.confidence,
    }))
  }
  if (name === 'getDishDetail') {
    const detail = await getDishDetail({
      record_id: args.record_id,
      dish_id: args.dish_id,
    })
    if (!detail) return { error: 'not_found' }
    return {
      record_id: detail.record_id,
      dish_id: detail.dish_id,
      item: detail.item,
      cuisine: detail.cuisine,
      traditionality_class: detail.traditionality_class,
      traditionality_score: detail.traditionality_score,
      source_thread: detail.source_thread,
      preparation_or_function: detail.preparation_or_function,
      historical_or_cultural_note: detail.historical_or_cultural_note,
      primary_source_url: detail.primary_source_url,
      wikipedia_url: detail.wikipedia_url,
      companionIngredients: detail.companionIngredients,
    }
  }
  throw new Error(`Unknown tradition tool: ${name}`)
}

export const TRADITION_SYSTEM = `You are a culinary tradition retrieval agent — not a chatbot.
Your only job is to translate the user's ask into tool calls against the Tradition database, then return a short ranked list of option cards as JSON.

Rules:
- Always use searchDishes (and getDishDetail when you need companions or confirmation) before answering.
- Aim for 3–6 options. Never dump raw SQL or long prose.
- Prefer higher traditionality_score / Core-emblematic when ranking, but respect the user's cuisine/region/keyword constraints.
- Final message MUST be a single JSON object with this exact shape:
  {"options":[{"id":"<record_id>","title":"<dish item name>","subtitle":"<cuisine — traditionality_class>","score":<traditionality_score or 0>}],"rationale":"<one short sentence>"}
- Do not wrap the JSON in markdown fences.
- If nothing matches, return {"options":[],"rationale":"why nothing matched"}.`
