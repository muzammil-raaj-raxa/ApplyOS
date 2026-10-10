import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { makeJob, makeScore, unscoredJob } from '../../test/fixtures'
import { JobRow } from './JobRow'

function setup(job = makeJob(), extra: Partial<React.ComponentProps<typeof JobRow>> = {}) {
  const onOpen = vi.fn()
  const onDecision = vi.fn()
  const onScore = vi.fn()
  render(
    <ul>
      <JobRow job={job} onOpen={onOpen} onDecision={onDecision} onScore={onScore} {...extra} />
    </ul>,
  )
  return { onOpen, onDecision, onScore }
}

describe('JobRow', () => {
  it('shows what you need to decide: title, company, pay, coverage and gaps', () => {
    setup()
    expect(screen.getByText('Senior iOS Engineer')).toBeInTheDocument()
    expect(screen.getByText('Northwind')).toBeInTheDocument()
    expect(screen.getByText('$150k to $190k')).toBeInTheDocument()
    expect(screen.getByText(/iOS, Swift, UIKit/)).toBeInTheDocument()
    expect(screen.getByText(/CI\/CD experience/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Fit score 91/ })).toBeInTheDocument()
  })

  it('does not repeat "Remote" when the location already says it', () => {
    setup(makeJob({ workplace: 'remote', location: 'Remote, Worldwide' }))
    expect(screen.getByText('Remote, Worldwide')).toBeInTheDocument()
    expect(screen.queryByText('Remote, Remote, Worldwide')).not.toBeInTheDocument()
  })

  it('adds the workplace when the location does not say it', () => {
    setup(makeJob({ workplace: 'hybrid', location: 'Berlin' }))
    expect(screen.getByText('Hybrid, Berlin')).toBeInTheDocument()
  })

  it('opens the job when the row is clicked', async () => {
    const { onOpen } = setup()
    await userEvent.click(screen.getByRole('button', { name: 'Open Senior iOS Engineer at Northwind' }))
    expect(onOpen).toHaveBeenCalledWith(1)
  })

  it('saves and rejects without opening the job', async () => {
    const { onOpen, onDecision } = setup()
    await userEvent.click(screen.getByRole('button', { name: 'Save Senior iOS Engineer' }))
    await userEvent.click(screen.getByRole('button', { name: 'Reject Senior iOS Engineer' }))
    expect(onDecision).toHaveBeenNthCalledWith(1, 1, 'save')
    expect(onDecision).toHaveBeenNthCalledWith(2, 1, 'reject')
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('a saved job can be un-saved', async () => {
    const { onDecision } = setup(makeJob({ user_decision: 'SAVED' }))
    const button = screen.getByRole('button', { name: 'Remove Senior iOS Engineer from saved' })
    expect(button).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(button)
    expect(onDecision).toHaveBeenCalledWith(1, 'clear')
  })

  it('a rejected job offers Restore instead of save and reject', async () => {
    const { onDecision } = setup(makeJob({ user_decision: 'REJECTED' }))
    expect(screen.queryByRole('button', { name: /Reject/ })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Restore' }))
    expect(onDecision).toHaveBeenCalledWith(1, 'clear')
  })

  it('an unscored job says so and can be scored from the row', async () => {
    const { onScore } = setup(unscoredJob())
    expect(screen.getByText('Not scored yet')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Not scored yet' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Score' }))
    expect(onScore).toHaveBeenCalledWith(2)
  })

  it('shows progress while a job is being scored', () => {
    setup(unscoredJob(), { scoring: true })
    expect(screen.getByText('Scoring now…')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Scoring this job' })).toBeInTheDocument()
  })

  it('explains why a job was filtered out', () => {
    setup(unscoredJob({ relevant: false, filter_reasons: ['seniority too high'] }))
    expect(screen.getByText('Filtered out: seniority too high')).toBeInTheDocument()
  })

  it('flags an AI answer that failed its checks', () => {
    setup(unscoredJob({ analysis_status: 'needs_review' }))
    expect(screen.getByText(/failed its checks/)).toBeInTheDocument()
  })

  it('shortens long lists of skills', () => {
    setup(makeJob({ score: makeScore({ matched: ['A', 'B', 'C', 'D', 'E', 'F'], gaps: ['X', 'Y', 'Z'] }) }))
    expect(screen.getByText(/A, B, C, D and 2 more/)).toBeInTheDocument()
    expect(screen.getByText(/X, Y and 1 more/)).toBeInTheDocument()
  })
})
