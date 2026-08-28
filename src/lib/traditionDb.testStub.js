/** Shared Tradition DB stubs for unit tests (avoids loading sql.js WASM). */
import { vi } from 'vitest'

export const traditionDbTestStub = {
  getDishDetail: vi.fn(async () => null),
  getTraditionAssociation: vi.fn(async (seed) => ({
    seed,
    candidates: [],
    threads: [],
  })),
  searchDishes: vi.fn(async () => []),
  bestTraditionMatches: vi.fn(async () => []),
  listRegionPicks: vi.fn(async () => [
    { key: 'china', label: 'China', dish_count: 120 },
    { key: 'mexico', label: 'Mexico', dish_count: 80 },
    { key: 'france', label: 'France', dish_count: 60 },
  ]),
  matchTraditionRegion: vi.fn(async (text) => {
    const t = String(text || '').toLowerCase()
    if (t.includes('china')) return { label: 'China', keys: ['china'] }
    if (t.includes('mexico')) return { label: 'Mexico', keys: ['mexico'] }
    return null
  }),
}
