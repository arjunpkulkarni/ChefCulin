import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { WorkspaceProvider } from '../context/WorkspaceContext.jsx'
import FormPane from './FormPane.jsx'

vi.mock('../api.js', () => ({
  listPalate: vi.fn(async () => ({ results: [] })),
  savePalate: vi.fn(),
  health: vi.fn(),
  cooccur: vi.fn(),
  techniques: vi.fn(),
  llmChat: vi.fn(),
}))

afterEach(cleanup)

describe('FormPane', () => {
  it('lists generic process frames for the current focus', () => {
    render(
      <WorkspaceProvider>
        <FormPane />
      </WorkspaceProvider>
    )
    expect(screen.getByText(/Preparation states that fit Chicken/)).toBeTruthy()
    expect(screen.getByText(/Seared — surface browning/)).toBeTruthy()
    expect(screen.getAllByRole('button', { name: 'Commit this form' }).length).toBeGreaterThan(3)
  })

  it('marks the committed frame', () => {
    render(
      <WorkspaceProvider>
        <FormPane />
      </WorkspaceProvider>
    )
    fireEvent.click(screen.getAllByRole('button', { name: 'Commit this form' })[1])
    expect(screen.getByRole('button', { name: 'Committed' })).toBeTruthy()
  })
})
