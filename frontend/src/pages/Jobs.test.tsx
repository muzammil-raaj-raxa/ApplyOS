import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { emptyStats, makeAnalysis, makeJob, unscoredJob } from '../test/fixtures'
import { json, mockApi, renderApp } from '../test/helpers'

const page = (items: unknown[], total = items.length) => ({ total, items })
const scored = makeJob()
const unscored = unscoredJob()
const detail = (job: object, analysis: unknown = makeAnalysis()) => ({ ...job, description: 'Build great iOS apps.\n\nRequirements:\n- Swift', analysis, analysis_error: null })

function setup(extra: Record<string, unknown> = {}) {
  return mockApi({
    'GET /api/jobs': page([scored, unscored]),
    'GET /api/jobs/1': detail(scored),
    'GET /api/jobs/2': detail(unscored, null),
    ...extra,
  })
}

describe('Jobs page', () => {
  it('lists the jobs and says how many', async () => {
    setup()
    renderApp('/jobs')
    expect(await screen.findByText('Senior iOS Engineer')).toBeInTheDocument()
    expect(screen.getByText('iOS Engineer')).toBeInTheDocument()
    expect(screen.getByText('2 jobs to look at.')).toBeInTheDocument()
  })

  it('shows a skeleton while loading', () => {
    setup({ 'GET /api/jobs': () => new Promise(() => {}) })
    renderApp('/jobs')
    expect(screen.getByRole('status', { name: 'Loading jobs' })).toBeInTheDocument()
  })

  it('asks the backend for 80+ when you pick that fit', async () => {
    const api = setup()
    renderApp('/jobs')
    await screen.findByText('Senior iOS Engineer')
    await userEvent.click(screen.getByRole('button', { name: '80+' }))
    await waitFor(() => expect(api.called('GET', '/api/jobs').some((c) => c.search.get('min_score') === '80')).toBe(true))
    expect(screen.getByRole('button', { name: '80+' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('sends the search text after you stop typing', async () => {
    const api = setup()
    renderApp('/jobs')
    await screen.findByText('Senior iOS Engineer')
    await userEvent.type(screen.getByPlaceholderText('Search by title or company'), 'north')
    await waitFor(() => expect(api.called('GET', '/api/jobs').some((c) => c.search.get('q') === 'north')).toBe(true), { timeout: 2000 })
  })

  it('opens the dossier with the full analysis when a row is clicked', async () => {
    setup()
    renderApp('/jobs')
    await userEvent.click(await screen.findByRole('button', { name: 'Open Senior iOS Engineer at Northwind' }))
    const dialog = await screen.findByRole('dialog', { name: 'Senior iOS Engineer at Northwind' })
    expect(await screen.findByText('How the score is built')).toBeInTheDocument()
    expect(dialog).toHaveTextContent('Strong overlap in Swift and UIKit.')
    expect(dialog).toHaveTextContent('You cover')
    expect(dialog).toHaveTextContent('GraphQL')
    expect(dialog).toHaveTextContent('Your legal work authorization is not confirmed.')
    expect(dialog).toHaveTextContent('Worth preparing an application')
  })

  it('closes the dossier with Escape', async () => {
    setup()
    renderApp('/jobs?job=1')
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('J opens the first job and K steps back', async () => {
    setup()
    renderApp('/jobs')
    await screen.findByText('Senior iOS Engineer')
    await userEvent.keyboard('j')
    expect(await screen.findByRole('dialog', { name: 'Senior iOS Engineer at Northwind' })).toBeInTheDocument()
    await userEvent.keyboard('j')
    expect(await screen.findByRole('dialog', { name: 'iOS Engineer at Marrow' })).toBeInTheDocument()
    await userEvent.keyboard('k')
    expect(await screen.findByRole('dialog', { name: 'Senior iOS Engineer at Northwind' })).toBeInTheDocument()
  })

  it('saves a job from the dossier and confirms it', async () => {
    const api = setup({ 'POST /api/jobs/1/save': { ...scored, user_decision: 'SAVED' } })
    renderApp('/jobs?job=1')
    await userEvent.click(await screen.findByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.called('POST', '/api/jobs/1/save')).toHaveLength(1))
    expect(await screen.findByText('Saved.')).toBeInTheDocument()
  })

  it('rejects from the row and lets you undo', async () => {
    const api = setup({
      'POST /api/jobs/1/reject': { ...scored, user_decision: 'REJECTED' },
      'DELETE /api/jobs/1/decision': scored,
    })
    renderApp('/jobs')
    await userEvent.click(await screen.findByRole('button', { name: 'Reject Senior iOS Engineer' }))
    expect(await screen.findByText('Rejected. It will not show in your list.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Undo' }))
    await waitFor(() => expect(api.called('DELETE', '/api/jobs/1/decision')).toHaveLength(1))
  })

  it('scores an unscored job from its dossier', async () => {
    const api = setup({ 'POST /api/jobs/2/analyze': { created: true, analysis: makeAnalysis({ overall_score: 77 }) } })
    renderApp('/jobs?job=2')
    await userEvent.click(await screen.findByRole('button', { name: 'Score this job' }))
    await waitFor(() => expect(api.called('POST', '/api/jobs/2/analyze')[0]?.search.get('force')).toBe('false'))
    expect(await screen.findByText('Scored 77. Worth a look.')).toBeInTheDocument()
  })

  it('explains when no AI is available', async () => {
    setup({ 'POST /api/jobs/2/analyze': () => json({ detail: 'no AI provider available' }, 503) })
    renderApp('/jobs?job=2')
    await userEvent.click(await screen.findByRole('button', { name: 'Score this job' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('No AI is available right now')
    expect(alert).toHaveTextContent('no AI provider available')
  })

  it('scores a batch from the header', async () => {
    const api = setup({
      'POST /api/jobs/analyze': { analyzed: 3, needs_review: 0, pending: 0, stopped_reason: null, results: [] },
    })
    renderApp('/jobs')
    await userEvent.click(await screen.findByRole('button', { name: 'Score 5 jobs' }))
    await waitFor(() => expect(api.called('POST', '/api/jobs/analyze')[0]?.search.get('limit')).toBe('5'))
    expect(await screen.findByText('Scored 3 jobs.')).toBeInTheDocument()
  })

  it('first run: invites you to find jobs, and does it', async () => {
    const api = setup({
      'GET /api/jobs': page([]),
      'GET /api/jobs/stats': emptyStats,
      'POST /api/jobs/search': { fetched: 2, new: 2, relevant: 2, filtered_out: 0, already_known: 0, cross_source_duplicates: 0, parse_failures: 0, errors: [] },
    })
    renderApp('/jobs')
    expect(await screen.findByText('No jobs yet.')).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: 'Find new jobs' })[0])
    await waitFor(() => expect(api.called('POST', '/api/jobs/search')).toHaveLength(1))
    expect(await screen.findByText('Found 2 new jobs.')).toBeInTheDocument()
  })

  it('no matches: says so and clears the filters', async () => {
    const api = setup({
      'GET /api/jobs': (url: URL) => (url.searchParams.has('min_score') ? page([]) : page([scored])),
    })
    renderApp('/jobs?fit=90')
    expect(await screen.findByText('Nothing matches these filters.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(await screen.findByText('Senior iOS Engineer')).toBeInTheDocument()
    expect(api.called('GET', '/api/jobs').at(-1)?.search.has('min_score')).toBe(false)
  })

  it('shows more when there are more', async () => {
    const many = Array.from({ length: 30 }, (_, i) => makeJob({ id: i + 100, title: `Job number ${i + 1}` }))
    const api = setup({
      'GET /api/jobs': (url: URL) => (url.searchParams.get('offset') === '30' ? page([makeJob({ id: 999, title: 'The last job' })], 31) : page(many, 31)),
    })
    renderApp('/jobs')
    expect(await screen.findByText('Showing 30 of 31')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Show more' }))
    expect(await screen.findByText('The last job')).toBeInTheDocument()
    expect(api.called('GET', '/api/jobs').some((c) => c.search.get('offset') === '30')).toBe(true)
  })

  it('shows what went wrong, with a way to retry', async () => {
    setup({ 'GET /api/jobs': () => json({ detail: 'database is locked' }, 500) })
    renderApp('/jobs')
    expect(await screen.findByText('That did not work')).toBeInTheDocument()
    expect(screen.getByText('database is locked')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})
