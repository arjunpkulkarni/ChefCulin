import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { WorkspaceProvider, useWorkspace } from './WorkspaceContext.jsx'
import DishSidebar from '../components/DishSidebar.jsx'

const api = vi.hoisted(() => ({
  savePalate: vi.fn(async () => ({ id: 'mem-1', created_at: '2026-08-14T00:00:00Z' })),
  listPalate: vi.fn(async () => ({ results: [] })),
  cooccur: vi.fn(async () => ({ results: [] })),
  techniques: vi.fn(async () => ({ results: [] })),
  health: vi.fn(async () => ({})),
}))
vi.mock('../api.js', () => api)

/* Three acidic ingredients so a balance trend is live at the same time — the
   point being that its decisions never reach the save payload. */
const DISH = ['verjus', 'cider vinegar', 'sorrel']

function Harness() {
  const ws = useWorkspace()
  return (
    <>
      <button type="button" onClick={() => DISH.forEach((n) => ws.addIngredient(n, 'compound'))}>
        seed dish
      </button>
      <button type="button" onClick={() => ws.addIngredient('rosemary', 'compound')}>
        add rosemary
      </button>
      <button type="button" onClick={() => ws.commitForm('Confit', 'fat, slow')}>
        set form
      </button>
      <button type="button" onClick={() => ws.lockCuisine('china', 'China')}>
        lock china
      </button>
      <DishSidebar />
    </>
  )
}

const renderApp = () =>
  render(
    <WorkspaceProvider>
      <Harness />
    </WorkspaceProvider>
  )

const click = (name) => fireEvent.click(screen.getByRole('button', { name }))
const saveButton = () => screen.getByRole('button', { name: /^(Save|Saving…|Saved)$/ })

beforeEach(() => {
  vi.clearAllMocks()
  api.savePalate.mockResolvedValue({ id: 'mem-1' })
  api.listPalate.mockResolvedValue({ results: [] })
})

afterEach(cleanup)

describe('F6 Save', () => {
  it('offers nothing to keep on an empty dish', () => {
    renderApp()
    expect(screen.getByText('Nothing to keep yet.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Save' })).toBeNull()
  })

  it('POSTs the snapshot with source f6', async () => {
    renderApp()
    click('seed dish')
    click('set form')
    click('lock china')
    fireEvent.click(saveButton())

    await waitFor(() => expect(api.savePalate).toHaveBeenCalledTimes(1))
    const body = api.savePalate.mock.calls[0][0]

    expect(body.source).toBe('f6')
    expect(body.user_id).toMatch(/^chef-/)
    expect(body.dish.map((d) => d.name)).toEqual(DISH)
    expect(body.form).toMatchObject({ name: 'Confit' })
    expect(body.cuisine_scope).toMatchObject({ label: 'China', keys: ['china'] })
  })

  it('never sends balance decisions — those stay in the session', async () => {
    renderApp()
    click('seed dish')
    fireEvent.click(screen.getByRole('button', { name: 'Accept' }))
    fireEvent.click(saveButton())

    await waitFor(() => expect(api.savePalate).toHaveBeenCalled())
    const body = api.savePalate.mock.calls[0][0]
    expect(JSON.stringify(body)).not.toMatch(/accept/)
    expect(body).not.toHaveProperty('balanceDecisions')
  })

  it('confirms the save and re-reads the kept list', async () => {
    renderApp()
    click('seed dish')
    const readsBefore = api.listPalate.mock.calls.length
    fireEvent.click(saveButton())

    expect(await screen.findByText(/Kept in Palate Memory/)).toBeTruthy()
    expect(api.listPalate.mock.calls.length).toBe(readsBefore + 1)
  })

  it('re-arms when the dish changes after a save', async () => {
    renderApp()
    click('seed dish')
    fireEvent.click(saveButton())
    await screen.findByText(/Kept in Palate Memory/)
    expect(screen.getByRole('button', { name: 'Saved' }).disabled).toBe(true)

    click('add rosemary')
    expect(screen.getByRole('button', { name: 'Save' }).disabled).toBe(false)
    expect(screen.queryByText(/Kept in Palate Memory/)).toBeNull()
  })

  it('surfaces a Postgres outage instead of silently failing', async () => {
    api.savePalate.mockRejectedValueOnce(new Error('save failed: 503'))
    renderApp()
    click('seed dish')
    fireEvent.click(saveButton())

    expect(await screen.findByText(/save failed: 503/)).toBeTruthy()
    expect(screen.getByText(/docker compose up -d/)).toBeTruthy()
    // still offering to try again
    expect(screen.getByRole('button', { name: 'Save' }).disabled).toBe(false)
  })

  it('shows how many dishes are already kept', async () => {
    api.listPalate.mockResolvedValue({ results: [{ id: 'a' }, { id: 'b' }] })
    renderApp()
    expect(await screen.findByText('2 kept')).toBeTruthy()
  })
})

describe('F6 Discard', () => {
  it('writes nothing at all', async () => {
    renderApp()
    click('seed dish')
    click('Discard')

    expect(await screen.findByText(/nothing was written/)).toBeTruthy()
    expect(api.savePalate).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Discarded' }).disabled).toBe(true)
  })

  it('is a no-op, not a delete — the kept list is untouched', () => {
    renderApp()
    click('seed dish')
    const readsBefore = api.listPalate.mock.calls.length
    click('Discard')
    expect(api.listPalate.mock.calls.length).toBe(readsBefore)
  })

  it('lets the chef change their mind by editing the dish', async () => {
    renderApp()
    click('seed dish')
    click('Discard')
    await screen.findByText(/nothing was written/)

    click('add rosemary')
    expect(screen.getByRole('button', { name: 'Discard' }).disabled).toBe(false)
    fireEvent.click(saveButton())
    await waitFor(() => expect(api.savePalate).toHaveBeenCalledTimes(1))
  })
})
