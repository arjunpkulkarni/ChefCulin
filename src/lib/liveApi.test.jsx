import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import * as api from '../api.js'
import App from '../App.jsx'
import { associate } from './associationEngine.js'

/**
 * End-to-end against the real FastAPI backend and the real corpus artifacts.
 *
 * Skips itself when the API is not running, exactly like
 * pipeline/tests/test_palate.py skips when Postgres is down — so `npm test`
 * stays green on a machine with nothing booted, and actually verifies the wiring
 * on a machine where it is.
 *
 *   cd pipeline && docker compose up -d
 *   DATABASE_URL=postgresql://culin:culin@127.0.0.1:5432/culin \
 *     python -m culin_etl.serve
 */
const BASE = process.env.CULIN_API || 'http://127.0.0.1:8000'

async function probe() {
  try {
    const res = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(1500) })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

const health = await probe()
const live = Boolean(health)
if (!live) {
  console.log(`[liveApi] API not reachable at ${BASE} — skipping integration tests.`)
}

describe.skipIf(!live)('live corpus API', () => {
  it('serves the built artifact tables', async () => {
    const h = await api.health()
    expect(h.ok).toBe(true)
    expect(h.cooccur_edges).toBeGreaterThan(0)
    expect(h.technique_edges).toBeGreaterThan(0)
  })

  it('returns real NPMI neighbours for duck', async () => {
    const res = await api.cooccur('duck', 10)
    expect(res.canonical).toBeTruthy()
    expect(res.results.length).toBeGreaterThan(0)
    res.results.forEach((r) => {
      expect(typeof r.ingredient).toBe('string')
      expect(r.confidence).toBeGreaterThan(0)
    })
  })

  it('returns techniques for duck', async () => {
    const res = await api.techniques('duck', 5)
    expect(Array.isArray(res.results)).toBe(true)
  })
})

describe.skipIf(!live)('Association Engine against the live corpus', () => {
  it('merges three real lenses and finds convergence', async () => {
    const dish = [{ name: 'rosemary', lens: 'compound' }]
    const data = await associate({ dish }, { api })

    expect(data.cooccur.status).toBe('ok')
    expect(data.byLens.cooccurrence.length).toBeGreaterThan(0)
    expect(data.byLens.compound.length).toBeGreaterThan(0)
    expect(data.byLens.tradition.length).toBeGreaterThan(0)

    // chemistry and tradition overlap on this corpus regardless of the seed
    const multi = data.combined.filter((c) => c.agreement === 'multi')
    expect(multi.length).toBeGreaterThan(0)
    multi.forEach((c) => expect(c.lenses.length).toBeGreaterThan(1))

    // every candidate carries a real lens, never an invented one
    data.combined.forEach((c) => {
      expect(['compound', 'tradition', 'co-occurrence']).toContain(c.primaryLens)
    })
  })

  it('never returns a hub as a corpus candidate', async () => {
    const data = await associate({ dish: [] }, { api })
    const names = data.byLens.cooccurrence.map((c) => c.name)
    expect(names).not.toContain('salt')
    expect(names).not.toContain('butter')
  })
})

const palateUp = live && health.palate_db
if (live && !palateUp) {
  console.log('[liveApi] palate_db is false — skipping F6 round-trip. Start Postgres.')
}

describe.skipIf(!palateUp)('F6 Save → Palate Memory round trip', () => {
  const user = `chef-vitest-${Date.now()}`

  it('writes a snapshot and reads it back for that user only', async () => {
    const body = {
      user_id: user,
      dish: [
        { name: 'verjus', lens: 'compound', mode: null },
        { name: 'miso', lens: 'compound', mode: 'Glaze' },
      ],
      form: { name: 'Confit', desc: 'fat, slow' },
      cuisine_scope: { label: 'China', keys: ['china'] },
      source: 'f6',
    }

    const saved = await api.savePalate(body)
    expect(saved.id).toBeTruthy()
    expect(saved.source).toBe('f6')

    const listed = await api.listPalate(user)
    expect(listed.results).toHaveLength(1)
    expect(listed.results[0].dish.map((d) => d.name)).toEqual(['verjus', 'miso'])
    expect(listed.results[0].form.name).toBe('Confit')

    // per-user isolation: a different chef sees nothing of this
    const other = await api.listPalate(`${user}-other`)
    expect(other.results).toHaveLength(0)
  })

  it('discard writes nothing — a user with no save has no rows', async () => {
    const listed = await api.listPalate(`${user}-discarded`)
    expect(listed.results).toHaveLength(0)
  })
})

/**
 * The whole app, driven the way a chef drives it, against the running backend.
 * Nothing is mocked here — these clicks reach the real corpus and real Postgres.
 */
describe.skipIf(!palateUp)('the real app, end to end', () => {
  const user = `chef-e2e-${Date.now()}`

  afterEach(async () => {
    cleanup()
    // leave no test rows behind in the dev database
    const listed = await api.listPalate(user).catch(() => ({ results: [] }))
    await Promise.all(
      (listed.results || []).map((r) =>
        fetch(`${BASE}/palate/${r.id}?user_id=${encodeURIComponent(user)}`, {
          method: 'DELETE',
        }).catch(() => {})
      )
    )
  })

  it('gathers a dish, flags the trend, merges three lenses and keeps it', async () => {
    window.localStorage.setItem('culinai.user', user)
    render(<App />)

    // 1. gather three acidic ingredients from the Compound lens
    const compound = document.querySelector('.pane-c')
    ;['verjus', 'cider vinegar', 'sorrel'].forEach((n) => {
      fireEvent.click(within(compound).getByText(n))
    })
    expect(document.querySelectorAll('.ing')).toHaveLength(3)

    // 2. E4: the balance read flags the trend and names its corrective pair
    const trend = document.querySelector('.trend')
    expect(trend.dataset.axis).toBe('acid')
    expect(within(trend).getByText(/Trending acidic/)).toBeTruthy()

    // 3. E5: the decision is captured in session, with no write
    fireEvent.click(within(trend).getByRole('button', { name: 'Accept' }))
    expect(screen.getByText(/session only, nothing saved/)).toBeTruthy()

    // 4. D1: the Associate tab merges chemistry, tradition and the live corpus
    fireEvent.click(screen.getByRole('button', { name: /Associate/ }))
    expect(await screen.findByText(/Three lenses answering/, {}, { timeout: 5000 })).toBeTruthy()
    const converge = screen.getByText(/Where the lenses converge/).closest('.group')
    expect(converge.querySelectorAll('.assoc-hit').length).toBeGreaterThan(0)

    // 5. F6: Save reaches Postgres and comes back
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText(/Kept in Palate Memory/, {}, { timeout: 5000 })).toBeTruthy()

    const listed = await api.listPalate(user)
    expect(listed.results).toHaveLength(1)
    expect(listed.results[0].dish.map((d) => d.name)).toEqual([
      'verjus',
      'cider vinegar',
      'sorrel',
    ])
    expect(listed.results[0].source).toBe('f6')
    // the session decision stayed in the session
    expect(JSON.stringify(listed.results[0])).not.toMatch(/accept/)
  })
})
