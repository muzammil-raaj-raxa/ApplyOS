import { render, screen } from '@testing-library/react'
import { makeScore } from '../../test/fixtures'
import { FitRing } from './FitRing'

describe('FitRing', () => {
  it('describes the score and band to assistive tech', () => {
    render(<FitRing score={91} parts={makeScore()} size={120} />)
    expect(screen.getByRole('img', { name: 'Fit score 91 out of 100. Excellent fit.' })).toBeInTheDocument()
    expect(screen.getByText('91')).toBeInTheDocument()
  })

  it('draws seven track arcs and a fill for every part that scored', () => {
    const { container } = render(<FitRing score={91} parts={makeScore()} />)
    expect(container.querySelectorAll('path')).toHaveLength(14)
  })

  it('skips the fill for a part that scored zero', () => {
    const { container } = render(<FitRing score={50} parts={makeScore({ domain: 0 })} />)
    expect(container.querySelectorAll('path')).toHaveLength(13)
  })

  it('shows a dashed placeholder when there is no score', () => {
    const { container } = render(<FitRing score={null} />)
    expect(screen.getByRole('img', { name: 'Not scored yet' })).toBeInTheDocument()
    expect(container.querySelectorAll('path')).toHaveLength(0)
  })

  it('says so while a score is being worked out', () => {
    render(<FitRing score={null} working />)
    expect(screen.getByRole('img', { name: 'Scoring this job' })).toBeInTheDocument()
  })

  it('shows the band label on large rings only', () => {
    const { rerender } = render(<FitRing score={85} parts={makeScore()} size={176} showBand />)
    expect(screen.getByText('Strong fit')).toBeInTheDocument()
    rerender(<FitRing score={85} parts={makeScore()} size={60} showBand />)
    expect(screen.queryByText('Strong fit')).not.toBeInTheDocument()
  })
})
