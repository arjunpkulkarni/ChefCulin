import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { beforeAll, describe, expect, it } from 'vitest'
import initSqlJs from 'sql.js'
import { cuisineSearchTerms, plateTokensFromNames, traditionSearchTokens } from './traditionDb.js'

const root = join(dirname(fileURLToPath(import.meta.url)), '../..')
const dbPath = join(root, 'src/data/traditional_culinary_uses_database_v2.db')

/**
 * Node smoke test for the Tradition schema + query shapes used by traditionDb.js.
 * Loads the same .db via sql.js without going through the Vite fetch URL path.
 */
describe('traditionDb (sql.js smoke)', () => {
  let db

  beforeAll(async () => {
    const SQL = await initSqlJs()
    const filebuffer = readFileSync(dbPath)
    db = new SQL.Database(filebuffer)
  })

  it('opens use_records with expected scale', () => {
    const [{ c }] = db.exec('SELECT COUNT(*) AS c FROM use_records')[0].values.map(([c]) => ({
      c,
    }))
    expect(c).toBe(316)
  })

  it('searchDishes-shaped query returns Sichuan-ish chicken rows when keyword matches', () => {
    const stmt = db.prepare(`
      SELECT record_id, dish_id, cuisine, item, traditionality_score
      FROM use_records
      WHERE LOWER(cuisine) LIKE LOWER(?)
        AND (LOWER(item) LIKE LOWER(?) OR LOWER(use_or_dish) LIKE LOWER(?))
      ORDER BY traditionality_score DESC, item ASC
      LIMIT ?
    `)
    stmt.bind(['%China%', '%chicken%', '%chicken%', 6])
    const rows = []
    while (stmt.step()) {
      const [record_id, dish_id, cuisine, item, traditionality_score] = stmt.get()
      rows.push({ record_id, dish_id, cuisine, item, traditionality_score })
    }
    stmt.free()
    expect(rows.length).toBeGreaterThan(0)
    expect(rows[0].record_id).toMatch(/^R/)
  })

  it('getDishDetail companions resolve for a known dish_id', () => {
    const dish = db.exec(
      `SELECT dish_id FROM use_records WHERE cuisine = 'China' LIMIT 1`
    )[0].values[0][0]
    const stmt = db.prepare(
      `SELECT ingredient_name FROM companion_ingredients WHERE dish_id = ?`
    )
    stmt.bind([dish])
    const names = []
    while (stmt.step()) names.push(stmt.get()[0])
    stmt.free()
    expect(names.length).toBeGreaterThan(0)
  })

  it('getTraditionAssociation-shaped query returns tradition neighbors', () => {
    const stmt = db.prepare(`
      SELECT ci2.ingredient_name AS name, COUNT(DISTINCT ci2.dish_id) AS dish_count
      FROM companion_ingredients ci1
      JOIN companion_ingredients ci2
        ON ci1.dish_id = ci2.dish_id AND ci1.ingredient_name != ci2.ingredient_name
      WHERE LOWER(ci1.ingredient_name) = LOWER(?)
      GROUP BY ci2.ingredient_name
      ORDER BY dish_count DESC
      LIMIT 8
    `)
    stmt.bind(['chicken'])
    const rows = []
    while (stmt.step()) {
      const [name, dish_count] = stmt.get()
      rows.push({ name, dish_count })
    }
    stmt.free()
    expect(rows.length).toBeGreaterThan(0)
  })
})

describe('cuisineSearchTerms', () => {
  it('maps adjective cuisines to the country stored in the DB', () => {
    expect(cuisineSearchTerms('Moroccan')).toEqual(['Moroccan', 'Morocco'])
    expect(cuisineSearchTerms('Chinese')).toEqual(['Chinese', 'China'])
    expect(cuisineSearchTerms('China')).toEqual(['China'])
  })
})

describe('traditionSearchTokens', () => {
  it('splits Foodb names into searchable tokens', () => {
    expect(traditionSearchTokens(['Chicken', 'Garlic'])).toEqual(
      expect.arrayContaining(['chicken', 'garlic'])
    )
    expect(traditionSearchTokens(['Cattle (Beef, Veal)'])).toEqual(
      expect.arrayContaining(['beef'])
    )
  })
})

describe('plateTokensFromNames', () => {
  it('excludes focus tokens from plate ranking', () => {
    expect(plateTokensFromNames('Chicken', ['Chicken', 'Garlic'])).toEqual(['garlic'])
    expect(plateTokensFromNames('Chicken', ['Garlic', 'Rice'])).toEqual(
      expect.arrayContaining(['garlic', 'rice'])
    )
  })
})
