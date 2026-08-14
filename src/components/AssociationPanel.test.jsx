import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { WorkspaceProvider, useWorkspace } from '../context/WorkspaceContext.jsx'
import AssociationPanel from './AssociationPanel.jsx'

/* The engine reaches the corpus through src/api.js. Every palate helper is
   mocked too, so the test can assert the panel never writes. */
const api = vi.hoisted(() => ({
  cooccur: vi.fn(async (seed) => ({
    canonical: seed,
    results: [
      { ingredient: 'juniper', confidence: 0.81, freq: 900 },
      { ingredient: 'salt', confidence: 0.79, freq: 880 },
      { ingredient: 'pear', confidence: 0.52, freq: 400 },
    ],
  })),
  techniques: vi.fn(async () => ({ results: [] })),
  health: vi.fn(async () => ({})),
  savePalate: vi.fn(),
  listPalate: vi.fn(),
}))
vi.mock('../api.js', () => api)

function Harness() {
  const ws = useWorkspace()
  return (
    <>
      <button type="button" onClick={() => ws.addIngredient('rosemary', 'compound')}>
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
    <WorkspaceProvider>
      <Harness />
    </WorkspaceProvider>
  )

const convergenceGroup = () =>
  screen.getByText(/Where the lenses converge/).closest('.group')

/** The count badge on the Tradition-alone section — the full list length,
    independent of how many chips the panel chooses to render. */
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

    // the corpus is asked through the existing artifact API, seeded like the pane
    expect(api.cooccur).toHaveBeenCalledWith('duck', 24)
  })

  it('shows multi-lens agreement distinctly from single-lens items', async () => {
    renderPanel()
    const group = await waitFor(convergenceGroup)

    // juniper: compound + tradition + corpus
    const hit = within(group).getByText('juniper').closest('.assoc-hit')
    expect(hit).not.toBeNull()
    expect(within(hit).getByText('Compound')).toBeTruthy()
    expect(within(hit).getByText('Tradition')).toBeTruthy()
    expect(within(hit).getByText('Corpus')).toBeTruthy()

    // pear is corpus-only: it lives in its own section, not in convergence
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

    fireEvent.click(within(group).getByText('juniper'))
    // primaryLens is first in LENSES order — compound, one of the three lenses
    expect(screen.getByTestId('dish').textContent).toBe('juniper:compound')
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

    // the tradition list is exactly as long as it was: a scope flags, it never filters
    expect(traditionAloneCount()).toBe(before)
    expect(Number(before)).toBeGreaterThan(0)
  })

  it('degrades to two lenses when the corpus is unreachable', async () => {
    api.cooccur.mockRejectedValueOnce(new Error('Corpus API unreachable'))
    renderPanel()

    expect(await screen.findByText(/Two lenses answering/)).toBeTruthy()
    expect(screen.getByText(/corpus unavailable/)).toBeTruthy()
    // chemistry and tradition still merged
    expect(within(convergenceGroup()).getByText('miso')).toBeTruthy()
  })
})

describe('the panel writes nothing', () => {
  it('never writes to Palate Memory', async () => {
    renderPanel()
    const group = await waitFor(convergenceGroup)
    const readsBefore = api.listPalate.mock.calls.length

    fireEvent.click(within(group).getByText('juniper'))
    fireEvent.click(screen.getByRole('button', { name: 'lock china' }))

    expect(api.savePalate).not.toHaveBeenCalled()
    // the mount read is the provider's kept list; the panel adds no read of its own
    expect(api.listPalate.mock.calls.length).toBe(readsBefore)
  })
})
