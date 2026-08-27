/**
 * Client-side Tradition DB — sql.js over traditional_culinary_uses_database_v2.db.
 * Panels never touch SQL; call searchDishes / getDishDetail / listCompanions only.
 */
import initSqlJs from 'sql.js'
import wasmUrl from 'sql.js/dist/sql-wasm.wasm?url'
import dbUrl from '../data/traditional_culinary_uses_database_v2.db?url'

let dbPromise = null

export async function getDb() {
  if (!dbPromise) {
    dbPromise = loadDb()
  }
  return dbPromise
}

async function loadDb() {
  const SQL = await initSqlJs({ locateFile: () => wasmUrl })
  const res = await fetch(dbUrl)
  if (!res.ok) throw new Error(`Failed to fetch tradition DB: ${res.status}`)
  const buf = await res.arrayBuffer()
  return new SQL.Database(new Uint8Array(buf))
}

/** Reset cached DB (tests only). */
export function _resetDbForTests() {
  dbPromise = null
}

export function cuisineSearchTerms(cuisine) {
  const raw = String(cuisine || '').trim()
  if (!raw) return []
  const lower = raw.toLowerCase()
  const aliases = {
    moroccan: 'Morocco',
    chinese: 'China',
    indian: 'India',
    japanese: 'Japan',
    italian: 'Italy',
    mexican: 'Mexico',
    french: 'France',
    spanish: 'Spain',
    korean: 'Korea',
    thai: 'Thailand',
    nigerian: 'Nigeria',
    brazilian: 'Brazil',
    turkish: 'Turkey',
    persian: 'Iran',
    iranian: 'Iran',
    lebanese: 'Lebanon',
    ethiopian: 'Ethiopia',
    german: 'Germany',
    greek: 'Greece',
    peruvian: 'Peru',
    american: 'United States',
  }
  const extra = aliases[lower]
  return extra ? [raw, extra] : [raw]
}

function rowsFrom(stmt) {
  const cols = stmt.getColumnNames()
  const out = []
  while (stmt.step()) {
    const values = stmt.get()
    const row = {}
    cols.forEach((c, i) => {
      row[c] = values[i]
    })
    out.push(row)
  }
  stmt.free()
  return out
}

function runQuery(db, sql, params = []) {
  const stmt = db.prepare(sql)
  stmt.bind(params)
  return rowsFrom(stmt)
}

/**
 * Search use_records. All filters optional; empty query returns a small sample.
 * @param {{ cuisine?: string, source_thread?: string, item_type?: string, keyword?: string, limit?: number }} query
 */
export async function searchDishes(query = {}) {
  const db = await getDb()
  const {
    cuisine = null,
    source_thread = null,
    item_type = null,
    keyword = null,
    limit = 24,
  } = query

  const where = []
  const params = []

  if (cuisine) {
    const terms = cuisineSearchTerms(cuisine)
    const clause = terms
      .map(() => '(LOWER(cuisine) LIKE LOWER(?) OR LOWER(country) LIKE LOWER(?))')
      .join(' OR ')
    where.push(`(${clause})`)
    for (const t of terms) {
      params.push(`%${t}%`, `%${t}%`)
    }
  }
  if (source_thread) {
    where.push('LOWER(source_thread) LIKE LOWER(?)')
    params.push(`%${source_thread}%`)
  }
  if (item_type) {
    where.push('LOWER(item_type) LIKE LOWER(?)')
    params.push(`%${item_type}%`)
  }
  if (keyword) {
    where.push(
      `(LOWER(item) LIKE LOWER(?) OR LOWER(use_or_dish) LIKE LOWER(?) OR LOWER(preparation_or_function) LIKE LOWER(?) OR LOWER(region_or_community) LIKE LOWER(?) OR LOWER(tags) LIKE LOWER(?))`
    )
    const k = `%${keyword}%`
    params.push(k, k, k, k, k)
  }

  const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : ''
  params.push(Math.min(Math.max(Number(limit) || 24, 1), 100))

  return runQuery(
    db,
    `
    SELECT
      record_id, dish_id, cuisine, item, item_type,
      traditionality_class, traditionality_score,
      use_or_dish, use_category, source_thread, country,
      region_or_community, preparation_or_function,
      occasion_or_context, confidence, evidence_basis,
      documentation_status, primary_source_url, wikipedia_url, tags
    FROM use_records
    ${whereSql}
    ORDER BY COALESCE(traditionality_score, -1) DESC, item ASC
    LIMIT ?
    `,
    params
  )
}

export async function listCompanions(dishId) {
  if (!dishId) return []
  const db = await getDb()
  return runQuery(
    db,
    `
    SELECT
      companion_id, dish_id, record_id, cuisine,
      ingredient_name, ingredient_category, role_in_dish,
      is_optional, use_priority, traditional_fit,
      preparation_note, region_or_context
    FROM companion_ingredients
    WHERE dish_id = ?
    ORDER BY use_priority ASC, ingredient_name ASC
    `,
    [dishId]
  )
}

/**
 * Full record + companion ingredient names for selection / calculator.
 * @param {{ record_id?: string, dish_id?: string }} id
 */
export async function getDishDetail(id = {}) {
  const db = await getDb()
  const { record_id = null, dish_id = null } = id
  if (!record_id && !dish_id) return null

  const rows = record_id
    ? runQuery(db, 'SELECT * FROM use_records WHERE record_id = ? LIMIT 1', [record_id])
    : runQuery(db, 'SELECT * FROM use_records WHERE dish_id = ? LIMIT 1', [dish_id])

  const record = rows[0] || null
  if (!record) return null

  const companions = await listCompanions(record.dish_id)
  return {
    ...record,
    companions,
    companionIngredients: companions.map((c) => c.ingredient_name),
  }
}

/** Convenience for demos / console: list distinct cuisines. */
export async function listCuisines() {
  const db = await getDb()
  return runQuery(
    db,
    `
    SELECT cuisine, COUNT(*) AS dish_count
    FROM use_records
    GROUP BY cuisine
    ORDER BY dish_count DESC, cuisine ASC
    `
  )
}

/**
 * Tradition lens for Associate — companions from documented dishes that share
 * a seed ingredient. Replaces the old static TRADITION_GROUPS chip lists.
 *
 * @param {string} seed — ingredient to anchor on (last on dish, or focus)
 * @param {{ exclude?: string[], limit?: number, cuisineScope?: { label: string, keys: string[] } | null }} opts
 */
export async function getTraditionAssociation(seed, opts = {}) {
  const db = await getDb()
  const { exclude = [], limit = 16, cuisineScope = null } = opts
  const skip = new Set(exclude.map((n) => n.toLowerCase()))
  const cap = Math.min(Math.max(Number(limit) || 16, 1), 32)

  const neighborRows = runQuery(
    db,
    `
    SELECT
      ci2.ingredient_name AS name,
      ur.source_thread,
      ur.cuisine,
      ur.country,
      ur.region_or_community,
      COUNT(DISTINCT ci2.dish_id) AS dish_count
    FROM companion_ingredients ci1
    JOIN companion_ingredients ci2
      ON ci1.dish_id = ci2.dish_id
      AND LOWER(ci1.ingredient_name) != LOWER(ci2.ingredient_name)
    JOIN use_records ur ON ur.dish_id = ci1.dish_id
    WHERE LOWER(ci1.ingredient_name) = LOWER(?)
    GROUP BY ci2.ingredient_name, ur.source_thread, ur.cuisine, ur.country, ur.region_or_community
    ORDER BY dish_count DESC, name ASC
    LIMIT ?
    `,
    [seed, cap * 3]
  )

  const seen = new Set()
  const candidates = []
  for (const row of neighborRows) {
    const key = row.name.toLowerCase()
    if (skip.has(key) || seen.has(key)) continue
    seen.add(key)
    const inScope = cuisineInScope(row, cuisineScope)
    candidates.push({
      name: row.name,
      lens: 'tradition',
      reason: row.source_thread || row.cuisine || 'documented tradition',
      meta: {
        thread: row.source_thread,
        cuisine: row.cuisine,
        inScope,
        engaged: false,
        hits: 0,
        dish_count: row.dish_count,
      },
    })
    if (candidates.length >= cap) break
  }

  const threadRows = runQuery(
    db,
    `
    SELECT
      ur.source_thread,
      ur.cuisine,
      ur.country,
      ur.region_or_community,
      GROUP_CONCAT(DISTINCT ci.ingredient_name) AS ingredients
    FROM use_records ur
    JOIN companion_ingredients ci ON ci.dish_id = ur.dish_id
    WHERE ur.dish_id IN (
      SELECT DISTINCT dish_id FROM companion_ingredients WHERE LOWER(ingredient_name) = LOWER(?)
    )
    GROUP BY ur.source_thread, ur.cuisine, ur.country, ur.region_or_community
    ORDER BY COUNT(DISTINCT ur.dish_id) DESC
    LIMIT 12
    `,
    [seed]
  )

  const threads = threadRows.map((row) => ({
    title: row.source_thread || row.cuisine || 'Tradition thread',
    thread: row.source_thread,
    region: regionKeysFromRecord(row),
    regionKeys: regionKeysFromRecord(row).split(',').filter(Boolean),
    inScope: cuisineInScope(row, cuisineScope),
    engaged: false,
    hits: [],
    requires: null,
  }))

  return { seed, candidates, threads }
}

function regionKeysFromRecord(row) {
  const parts = [row.country, row.cuisine, row.region_or_community]
    .filter(Boolean)
    .map((s) => String(s).toLowerCase().replace(/\s+/g, '_'))
  return [...new Set(parts)].join(',')
}

function cuisineInScope(row, cuisineScope) {
  if (!cuisineScope?.keys?.length) return null
  const hay = [row.cuisine, row.country, row.region_or_community]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return cuisineScope.keys.some((k) =>
    k.split(',').some((part) => hay.includes(part.trim().toLowerCase()))
  )
}

const TOKEN_STOP = new Set([
  'the',
  'and',
  'with',
  'family',
  'foods',
  'products',
  'domestic',
  'european',
  'mallard',
  'velvet',
  'type',
  'other',
])

/** Tokens used to rank Tradition records against the focus + plate. */
export function traditionSearchTokens(names = []) {
  const seen = new Set()
  const out = []
  const add = (t) => {
    const s = String(t || '')
      .trim()
      .toLowerCase()
    if (s.length < 3 || TOKEN_STOP.has(s) || seen.has(s)) return
    seen.add(s)
    out.push(s)
  }
  for (const name of names) {
    if (!name) continue
    const lower = String(name).toLowerCase()
    add(lower)
    lower
      .replace(/[()]/g, ' ')
      .split(/[\s,/]+/)
      .forEach(add)
    if (/cattle|beef/.test(lower)) add('beef')
    if (/pig|pork/.test(lower)) add('pork')
    if (/sheep|lamb|mutton/.test(lower)) add('lamb')
  }
  return out.slice(0, 10)
}

function rowToOption(row) {
  const classLabel = row.traditionality_class || 'documented'
  const place = [row.cuisine, row.country].filter(Boolean).join(' · ')
  return {
    id: row.record_id,
    title: row.item,
    subtitle: `${place}${place ? ' — ' : ''}${classLabel}`,
    score: Number(row.traditionality_score) || 0,
    plateHits: Number(row.plate_hits) || 0,
    dish_id: row.dish_id,
  }
}

/**
 * Top documented dishes for the focus ingredient plus anything already gathered.
 * Ranked by how many plate tokens hit companions / dish text, then traditionality.
 */
export async function bestTraditionMatches({
  names = [],
  cuisine = null,
  cuisineScope = null,
  limit = 5,
} = {}) {
  const db = await getDb()
  const tokens = traditionSearchTokens(names)
  const cap = Math.min(Math.max(Number(limit) || 5, 1), 12)
  if (!tokens.length) return []

  const cuisineTerms = cuisine
    ? cuisineSearchTerms(cuisine)
    : cuisineScope?.label
      ? cuisineSearchTerms(cuisineScope.label)
      : []

  const hitLikes = tokens.map(() => 'LOWER(COALESCE(ci.ingredient_name,\'\')) LIKE ?').join(' OR ')
  const whereLikes = tokens
    .map(
      () =>
        `(LOWER(ur.item) LIKE ? OR LOWER(COALESCE(ur.use_or_dish,'')) LIKE ? OR LOWER(COALESCE(ci.ingredient_name,'')) LIKE ?)`
    )
    .join(' OR ')
  const hitParams = tokens.map((t) => `%${t}%`)
  const whereParams = tokens.flatMap((t) => {
    const like = `%${t}%`
    return [like, like, like]
  })

  let cuisineSql = ''
  const cuisineParams = []
  if (cuisineTerms.length) {
    cuisineSql = `AND (${cuisineTerms
      .map(() => '(LOWER(ur.cuisine) LIKE LOWER(?) OR LOWER(ur.country) LIKE LOWER(?))')
      .join(' OR ')})`
    for (const t of cuisineTerms) cuisineParams.push(`%${t}%`, `%${t}%`)
  }

  const rows = runQuery(
    db,
    `
    SELECT
      ur.record_id,
      ur.dish_id,
      ur.item,
      ur.cuisine,
      ur.country,
      ur.traditionality_class,
      ur.traditionality_score,
      ur.source_thread,
      ur.region_or_community,
      COUNT(DISTINCT CASE WHEN (${hitLikes}) THEN LOWER(ci.ingredient_name) END) AS plate_hits
    FROM use_records ur
    LEFT JOIN companion_ingredients ci ON ci.dish_id = ur.dish_id
    WHERE (${whereLikes})
    ${cuisineSql}
    GROUP BY ur.record_id
    ORDER BY plate_hits DESC, COALESCE(ur.traditionality_score, -1) DESC, ur.item ASC
    LIMIT ?
    `,
    [...hitParams, ...whereParams, ...cuisineParams, cap]
  )

  return rows.map(rowToOption)
}

