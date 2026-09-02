import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { WorkspaceProvider, useWorkspace } from '../context/WorkspaceContext.jsx'
import TraditionPane from './TraditionPane.jsx'

vi.mock('../api.js', () => ({
  listPalate: vi.fn(async () => ({ results: [] })),
  savePalate: vi.fn(),
  health: vi.fn(),
  cooccur: vi.fn(),
  techniques: vi.fn(),
}))

vi.mock('../lib/traditionDb.js', () => ({
  bestTraditionMatches: vi.fn(async () => [
    { id: 'D-1', title: 'Tapenade', subtitle: 'Provence', plateHits: 1 },
  ]),
  getDishDetail: vi.fn(async () => ({
    item: 'Tapenade',
    cuisine: 'French',
    companionIngredients: ['Caper', 'Anchovy', 'Olive oil'],
  })),
}))

/** Renders the pane with a focus ingredient set, plus a readout of the dish. */
function Harness() {
  const { setFocusIngredient, dish } = useWorkspace()
  return (
    <>
      <button type="button" onClick={() => setFocusIngredient('Olive')}>
        focus olive
      </button>
      <div data-testid="dish">{dish.map((d) => d.name).join(',')}</div>
      <TraditionPane />
    </>
  )
}

async function openFirstCard() {
  render(
    <WorkspaceProvider>
      <Harness />
    </WorkspaceProvider>
  )
  fireEvent.click(screen.getByRole('button', { name: 'focus olive' }))
  const card = await screen.findByText('Tapenade')
  fireEvent.click(card)
  await screen.findByText('Companions on the dish')
}

afterEach(cleanup)

describe('TraditionPane — reading a dish is not a commit', () => {
  it('opens a dish card without writing anything to the plate', async () => {
    await openFirstCard()
    expect(screen.getByTestId('dish').textContent).toBe('')
    expect(screen.getByText(/none added yet/)).toBeTruthy()
  })

  it('commits companions only on the explicit add-all action', async () => {
    await openFirstCard()
    fireEvent.click(screen.getByRole('button', { name: /Add all 3 to the dish/ }))
    await waitFor(() =>
      expect(screen.getByTestId('dish').textContent).toBe('Caper,Anchovy,Olive oil')
    )
  })

  it('lets a single companion be added on its own', async () => {
    await openFirstCard()
    fireEvent.click(screen.getByText('Caper'))
    await waitFor(() => expect(screen.getByTestId('dish').textContent).toBe('Caper'))
  })
})
