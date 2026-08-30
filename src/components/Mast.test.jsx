import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { WorkspaceProvider, useWorkspace } from '../context/WorkspaceContext.jsx'
import Mast from './Mast.jsx'

const traditionDb = vi.hoisted(() => ({
  getDishDetail: vi.fn(async () => null),
  getTraditionAssociation: vi.fn(async (seed) => ({ seed, candidates: [], threads: [] })),
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
}))

vi.mock('../api.js', () => ({
  listPalate: vi.fn(async () => ({ results: [] })),
  savePalate: vi.fn(),
  health: vi.fn(),
  cooccur: vi.fn(),
  techniques: vi.fn(),
}))

vi.mock('../lib/traditionDb.js', () => traditionDb)

function Harness() {
  const { focusIngredient, cuisineScope } = useWorkspace()
  return (
    <>
      <Mast />
      <div data-testid="focus">{focusIngredient}</div>
      <div data-testid="scope">{cuisineScope?.label || ''}</div>
    </>
  )
}

afterEach(cleanup)

describe('Mast — demo chrome', () => {
  it('searches Foodb and changes the focus ingredient', async () => {
    render(
      <WorkspaceProvider>
        <Harness />
      </WorkspaceProvider>
    )
    fireEvent.click(screen.getByRole('button', { name: 'Choose ingredient…' }))
    fireEvent.change(screen.getByLabelText('Search focus ingredient'), {
      target: { value: 'Rosemary' },
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Rosemary' }))
    expect(screen.getByTestId('focus').textContent).toBe('Rosemary')
  })

  it('shows no matches for an unknown Foodb query', () => {
    render(
      <WorkspaceProvider>
        <Harness />
      </WorkspaceProvider>
    )
    fireEvent.click(screen.getByRole('button', { name: 'Choose ingredient…' }))
    fireEvent.change(screen.getByLabelText('Search focus ingredient'), {
      target: { value: 'zzzz-not-a-food' },
    })
    expect(screen.getByText('No matches')).toBeTruthy()
  })

  it('locks and clears cuisine scope', async () => {
    render(
      <WorkspaceProvider>
        <Harness />
      </WorkspaceProvider>
    )
    fireEvent.click(screen.getByRole('button', { name: /Cuisine scope/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'Mexico' }))
    expect(screen.getByTestId('scope').textContent).toBe('Mexico')
    fireEvent.click(screen.getByText('✕'))
    expect(screen.getByTestId('scope').textContent).toBe('')
  })
})
