import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { WorkspaceProvider, useWorkspace } from './WorkspaceContext.jsx'
import DishSidebar from '../components/DishSidebar.jsx'

/* Every palate helper is mocked so the test can assert none of them ran.
   Balance decisions are session state — nothing here may reach the API. */
const palate = vi.hoisted(() => ({
  savePalate: vi.fn(),
  listPalate: vi.fn(),
  cooccur: vi.fn(),
  techniques: vi.fn(),
  health: vi.fn(),
}))
vi.mock('../api.js', () => palate)

vi.mock('../lib/traditionDb.js', () => ({
  listRegionPicks: vi.fn(async () => []),
  matchTraditionRegion: vi.fn(async () => null),
  bestTraditionMatches: vi.fn(async () => []),
}))

/* Three acidic ingredients, no sweetness: acid share 3/3 without a focus anchor. */
const ACID_DISH = ['verjus', 'cider vinegar', 'sorrel']

function Harness({ seed = ACID_DISH }) {
  const ws = useWorkspace()
  return (
    <>
      <button type="button" onClick={() => seed.forEach((n) => ws.addIngredient(n, 'compound'))}>
        seed dish
      </button>
      <button type="button" onClick={() => ws.addIngredient('rosemary', 'compound')}>
        add rosemary
      </button>
      <div data-testid="log">{JSON.stringify(ws.balanceDecisions)}</div>
      <DishSidebar />
    </>
  )
}

const renderWorkspace = () =>
  render(
    <WorkspaceProvider>
      <Harness />
    </WorkspaceProvider>
  )

const readLog = () => JSON.parse(screen.getByTestId('log').textContent)
const seedDish = () => fireEvent.click(screen.getByRole('button', { name: 'seed dish' }))

beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
    throw new Error('no network call expected')
  })
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('E4 — the flag reaches the UI', () => {
  it('shows nothing before ingredients are gathered', () => {
    renderWorkspace()
    expect(document.querySelector('.trend')).toBeNull()
    expect(screen.getByText(/Gather ingredients or set a form/)).toBeTruthy()
  })

  it('renders the flagged axis, its pair and the suggestion', () => {
    renderWorkspace()
    seedDish()

    const card = document.querySelector('.trend')
    expect(card).not.toBeNull()
    expect(card.dataset.axis).toBe('acid')
    expect(card.textContent).toContain('sweet')
    expect(screen.getByText(/Trending acidic/)).toBeTruthy()
  })

  it('offers Accept, Adjust and Override — and adds no ingredient of its own', () => {
    renderWorkspace()
    seedDish()

    ;['Accept', 'Adjust', 'Override'].forEach((label) => {
      expect(screen.getByRole('button', { name: label })).toBeTruthy()
    })
    // the suggestion names an axis; it never puts a chip on the plate
    expect(document.querySelectorAll('.ing').length).toBe(ACID_DISH.length)
  })
})

describe('E5 — decisions are session state', () => {
  it('appends an accept to balanceDecisions', () => {
    renderWorkspace()
    seedDish()
    fireEvent.click(screen.getByRole('button', { name: 'Accept' }))

    const log = readLog()
    expect(log).toHaveLength(1)
    expect(log[0]).toMatchObject({
      axis: 'acid',
      pair: 'sweet',
      decision: 'accept',
      dishSnapshot: ACID_DISH,
    })
    expect(log[0].share).toBeCloseTo(1)
    expect(Date.parse(log[0].at)).not.toBeNaN()
  })

  it('appends an override', () => {
    renderWorkspace()
    seedDish()
    fireEvent.click(screen.getByRole('button', { name: 'Override' }))

    expect(readLog()).toHaveLength(1)
    expect(readLog()[0].decision).toBe('override')
  })

  it('appends an adjust', () => {
    renderWorkspace()
    seedDish()
    fireEvent.click(screen.getByRole('button', { name: 'Adjust' }))

    expect(readLog()[0].decision).toBe('adjust')
  })

  it('never writes, and does not even re-read Palate Memory', () => {
    renderWorkspace()
    seedDish()
    // the provider reads the kept list once on mount; a decision must not add to that
    const readsBefore = palate.listPalate.mock.calls.length

    fireEvent.click(screen.getByRole('button', { name: 'Accept' }))
    fireEvent.click(screen.getByRole('button', { name: 'add rosemary' }))
    fireEvent.click(screen.getByRole('button', { name: 'Override' }))

    expect(palate.savePalate).not.toHaveBeenCalled()
    expect(palate.listPalate.mock.calls.length).toBe(readsBefore)
    expect(globalThis.fetch).not.toHaveBeenCalled()
  })

  it('settles the flag once answered, and re-asks when the dish changes', () => {
    renderWorkspace()
    seedDish()
    fireEvent.click(screen.getByRole('button', { name: 'Override' }))

    expect(screen.queryByRole('button', { name: 'Override' })).toBeNull()
    expect(screen.getByText(/session only, nothing saved/)).toBeTruthy()

    // a different plate is a different question
    fireEvent.click(screen.getByRole('button', { name: 'add rosemary' }))
    expect(screen.getByRole('button', { name: 'Override' })).toBeTruthy()
    expect(readLog()).toHaveLength(1)
  })

  it('ignores a decision verb it does not recognise', () => {
    let ws
    function Probe() {
      ws = useWorkspace()
      return null
    }
    render(
      <WorkspaceProvider>
        <Probe />
      </WorkspaceProvider>
    )
    const trend = { axis: 'acid', pair: 'sweet', share: 0.75 }
    expect(ws.recordBalanceDecision('delete', trend)).toBeNull()
    expect(ws.recordBalanceDecision('accept', null)).toBeNull()
  })
})
