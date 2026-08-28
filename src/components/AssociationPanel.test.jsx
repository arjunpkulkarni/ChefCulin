import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { WorkspaceProvider, useWorkspace } from '../context/WorkspaceContext.jsx'
import AssociationPanel from './AssociationPanel.jsx'

const api = vi.hoisted(() => ({
  cooccur: vi.fn(async (seed) => ({
    canonical: seed,
    results: [
      { ingredient: 'Garlic', confidence: 0.81, freq: 900 },
      { ingredient: 'salt', confidence: 0.79, freq: 880 },
      { ingredient: 'pear', confidence: 0.52, freq: 400 },
    ],
  })),
  techniques: vi.fn(async () => ({ results: [] })),
  compound: vi.fn(async (seed) => ({
    canonical: seed,
    results: [
      { ingredient: 'garlic', display: 'Garlic', weight: 50, confidence: 0.81 },
      { ingredient: 'miso', display: 'Miso', weight: 40, confidence: 0.6 },
      { ingredient: 'pear', display: 'Pear', weight: 30, confidence: 0.52 },
    ],
  })),
  health: vi.fn(async () => ({})),
  savePalate: vi.fn(),
  listPalate: vi.fn(),
}))
vi.mock('../api.js', () => api)

vi.mock('../lib/traditionDb.js', () => ({
  getTraditionAssociation: vi.fn(async (seed, opts = {}) => ({
    seed,
    candidates: [
      {
        name: 'Garlic',
        lens: 'tradition',
        reason: 'thread',
        meta: { inScope: opts.cuisineScope ? true : null, engaged: false, hits: 0 },
      },
      {
        name: 'Miso',
        lens: 'tradition',
        reason: 'thread',
        meta: { inScope: opts.cuisineScope ? true : null, engaged: false, hits: 0 },
      },
      {
        name: 'hoisin',
        lens: 'tradition',
        reason: 'Beijing',
        meta: { inScope: opts.cuisineScope ? true : null, engaged: false, hits: 0 },
      },
      {
        name: 'ancho chile',
        lens: 'tradition',
        reason: 'Mexico',
        meta: { inScope: opts.cuisineScope ? false : null, engaged: false, hits: 0 },
      },
    ],
    threads: [
      { title: 'China thread', thread: 'China', inScope: opts.cuisineScope ? true : null, engaged: false, hits: [] },
      { title: 'Mexico thread', thread: 'Mexico', inScope: opts.cuisineScope ? false : null, engaged: false, hits: [] },
    ],
  })),
  _resetDbForTests: vi.fn(),
  listRegionPicks: vi.fn(async () => [{ key: 'china', label: 'China', dish_count: 1 }]),
  matchTraditionRegion: vi.fn(async () => null),
  bestTraditionMatches: vi.fn(async () => []),
}))

vi.mock('../lib/matchRecipeNlg.js', () => ({
  matchRecipeNlg: vi.fn(async (name) => ({
    canonical: String(name || 'chicken')
      .toLowerCase()
      .replace(/\s+/g, ' ')
      .trim() || 'chicken',
    source: 'test',
  })),
  heuristicRecipeNlg: (name) =>
    String(name || 'chicken')
      .toLowerCase()
      .replace(/\s+/g, ' ')
      .trim() || 'chicken',
}))

function Harness() {
  const ws = useWorkspace()
  return (
    <>
      <button type="button" onClick={() => ws.addIngredient('Rosemary', 'compound')}>
        add rosemary
      </button>
      <button type="button" onClick={() => ws.lockCuisine('china', 'China')}>
        lock china
      </button>
      <div data-testid="dish">{ws.dish.map((d) => `${d.name}:${d.lens}`).join(',')}</div>
      <AssociationPanel />
    </>
  )
}

const renderPanel = () =>
  render(
    <WorkspaceProvider initialFocus="Chicken">
      <Harness />
    </WorkspaceProvider>
  )

const convergenceGroup = () =>
  screen.getByText(/Where the lenses converge/).closest('.group')

const traditionAloneCount = () =>
  screen.getByText(/Tradition alone/).closest('.group').querySelector('.posture').textContent

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(cleanup)

describe('D1 — surfacing UI', () => {
  it('merges all three lenses into one panel', async () => {
    renderPanel()
    await waitFor(() => expect(api.cooccur).toHaveBeenCalled())
    expect(await screen.findByText(/Three lenses answering/)).toBeTruthy()
    expect(api.cooccur).toHaveBeenCalledWith('chicken', 24)
  })

  it('shows multi-lens agreement distinctly from single-lens items', async () => {
    renderPanel()
    const group = await waitFor(convergenceGroup)

    const hit = within(group).getByText('Garlic').closest('.assoc-hit')
    expect(hit).not.toBeNull()
    expect(within(hit).getByText('Compound')).toBeTruthy()
    expect(within(hit).getByText('Tradition')).toBeTruthy()
    expect(within(hit).getByText('Corpus')).toBeTruthy()

    expect(within(group).queryByText('pear')).toBeNull()
    const corpusAlone = screen.getByText(/Corpus alone/).closest('.group')
    expect(within(corpusAlone).getByText('pear')).toBeTruthy()
  })

  it('filters corpus hubs out of the merge', async () => {
    renderPanel()
    await waitFor(convergenceGroup)
    expect(screen.queryByText('salt')).toBeNull()
  })

  it('adds to the dish under a real lens, never an invented one', async () => {
    renderPanel()
    const group = await waitFor(convergenceGroup)

    fireEvent.click(within(group).getByText('Garlic'))
    expect(screen.getByTestId('dish').textContent).toBe('Garlic:compound')
  })
})

describe('D2 — disagreement is visible, not silent', () => {
  it('renders the scope flag without dropping out-of-scope threads', async () => {
    renderPanel()
    await waitFor(convergenceGroup)

    const before = traditionAloneCount()
    fireEvent.click(screen.getByRole('button', { name: 'lock china' }))
    expect(await screen.findByText(/scope vs thread/)).toBeTruthy()
    expect(screen.getByText(/flags, it never filters/)).toBeTruthy()

    expect(traditionAloneCount()).toBe(before)
    expect(Number(before)).toBeGreaterThan(0)
  })

  it('degrades to two lenses when the corpus is unreachable', async () => {
    api.cooccur.mockRejectedValueOnce(new Error('Corpus API unreachable'))
    renderPanel()

    expect(await screen.findByText(/Two lenses answering/)).toBeTruthy()
    expect(screen.getByText(/corpus unavailable/)).toBeTruthy()
    expect(within(convergenceGroup()).getByText('Miso')).toBeTruthy()
  })
})

describe('the panel writes nothing', () => {
  it('never writes to Palate Memory', async () => {
    renderPanel()
    const group = await waitFor(convergenceGroup)
    const readsBefore = api.listPalate.mock.calls.length

    fireEvent.click(within(group).getByText('Garlic'))
    fireEvent.click(screen.getByRole('button', { name: 'lock china' }))

    expect(api.savePalate).not.toHaveBeenCalled()
    expect(api.listPalate.mock.calls.length).toBe(readsBefore)
  })
})
