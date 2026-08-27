import { describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach } from 'vitest'
import OptionCard from './OptionCard.jsx'

afterEach(cleanup)

describe('OptionCard', () => {
  const option = {
    id: 'R0001',
    title: 'Acarajé',
    subtitle: 'Brazil — Core / emblematic',
    score: 4,
  }

  it('renders title, subtitle, score and provenance stamp', () => {
    render(
      <OptionCard option={option} stamp={{ label: 'Tradition DB', title: 'R0001' }} />
    )
    expect(screen.getByText('Acarajé')).toBeTruthy()
    expect(screen.getByText('Brazil — Core / emblematic')).toBeTruthy()
    expect(screen.getByText('4')).toBeTruthy()
    expect(screen.getByText('Tradition DB')).toBeTruthy()
  })

  it('calls onSelect with the option', () => {
    const onSelect = vi.fn()
    render(<OptionCard option={option} onSelect={onSelect} />)
    fireEvent.click(screen.getByRole('button'))
    expect(onSelect).toHaveBeenCalledWith(option)
  })

  it('marks selected and can disable', () => {
    const onSelect = vi.fn()
    const { container } = render(
      <OptionCard option={option} selected onSelect={onSelect} disabled />
    )
    expect(container.querySelector('.option-card.selected')).toBeTruthy()
    fireEvent.click(screen.getByRole('button'))
    expect(onSelect).not.toHaveBeenCalled()
  })

  it('hides score when zero', () => {
    render(<OptionCard option={{ ...option, score: 0 }} />)
    expect(screen.queryByText('0')).toBeNull()
  })
})
