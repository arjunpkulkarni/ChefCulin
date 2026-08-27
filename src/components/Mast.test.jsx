import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { WorkspaceProvider, useWorkspace } from '../context/WorkspaceContext.jsx'
import Mast from './Mast.jsx'

vi.mock('../api.js', () => ({
  listPalate: vi.fn(async () => ({ results: [] })),
  savePalate: vi.fn(),
  health: vi.fn(),
  cooccur: vi.fn(),
  techniques: vi.fn(),
  llmChat: vi.fn(),
}))

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
    fireEvent.click(screen.getByRole('button', { name: 'Chicken' }))
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
    fireEvent.click(screen.getByRole('button', { name: 'Chicken' }))
    fireEvent.change(screen.getByLabelText('Search focus ingredient'), {
      target: { value: 'zzzz-not-a-food' },
    })
    expect(screen.getByText('No matches')).toBeTruthy()
  })

  it('locks and clears cuisine scope', () => {
    render(
      <WorkspaceProvider>
        <Harness />
      </WorkspaceProvider>
    )
    fireEvent.click(screen.getByRole('button', { name: /Cuisine scope/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Mexico' }))
    expect(screen.getByTestId('scope').textContent).toBe('Mexico')
    fireEvent.click(screen.getByText('✕'))
    expect(screen.getByTestId('scope').textContent).toBe('')
  })
})
