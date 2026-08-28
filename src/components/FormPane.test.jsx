import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { WorkspaceProvider } from '../context/WorkspaceContext.jsx'
import FormPane from './FormPane.jsx'

const openai = vi.hoisted(() => ({
  llmChat: vi.fn(),
  openaiConfigured: vi.fn(() => true),
}))

vi.mock('../api.js', () => ({
  listPalate: vi.fn(async () => ({ results: [] })),
  savePalate: vi.fn(),
  health: vi.fn(),
  cooccur: vi.fn(),
  techniques: vi.fn(),
}))

vi.mock('../lib/traditionDb.js', () => ({
  listRegionPicks: vi.fn(async () => []),
  matchTraditionRegion: vi.fn(async () => null),
  bestTraditionMatches: vi.fn(async () => []),
}))

vi.mock('../lib/openai.js', () => openai)

afterEach(cleanup)

const sampleForms = {
  rationale: 'Frames for chicken centrepiece cooking.',
  forms: [
    {
      name: 'Seared',
      title: 'Seared — surface browning',
      desc: 'High heat, surface browning.',
      craft: [
        { k: 'Texture', v: 'browned exterior' },
        { k: 'Temp', v: 'hot, rested' },
        { k: 'Sauce', v: 'pan jus' },
      ],
      balance: { produces: ['crisp-skin'], absent: ['long-cook'], overlay: 'sear', fat: 0.75 },
    },
  ],
}

describe('FormPane', () => {
  it('loads LLM form frames for the current focus', async () => {
    openai.llmChat.mockResolvedValueOnce({
      choices: [{ message: { content: JSON.stringify(sampleForms) } }],
    })
    render(
      <WorkspaceProvider initialFocus="Chicken">
        <FormPane />
      </WorkspaceProvider>
    )
    expect(await screen.findByText(/Seared — surface browning/)).toBeTruthy()
    expect(screen.getAllByRole('button', { name: 'Commit this form' }).length).toBeGreaterThan(0)
  })

  it('marks the committed frame', async () => {
    openai.llmChat.mockResolvedValueOnce({
      choices: [{ message: { content: JSON.stringify(sampleForms) } }],
    })
    render(
      <WorkspaceProvider initialFocus="Chicken">
        <FormPane />
      </WorkspaceProvider>
    )
    await screen.findByText(/Seared — surface browning/)
    fireEvent.click(screen.getByRole('button', { name: 'Commit this form' }))
    expect(screen.getByRole('button', { name: 'Committed' })).toBeTruthy()
  })

  it('prompts for focus when none is chosen', () => {
    render(
      <WorkspaceProvider>
        <FormPane />
      </WorkspaceProvider>
    )
    expect(screen.getByText(/Choose a focus ingredient/)).toBeTruthy()
  })
})
