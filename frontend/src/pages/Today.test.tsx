import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LAST_RUN_KEY } from '../hooks/actions'
import { emptyStats, makeJob, stats, unscoredJob } from '../test/fixtures'
import { mockApi, renderApp } from '../test/helpers'

const page = (items: unknown[]) => ({ total: items.length, items })
const summary = (over = {}) => ({ fetched: 10, new: 4, relevant: 3, filtered_out: 1, already_known: 5, cross_source_duplicates: 1, parse_failures: 0, errors: [], ...over })

describe('Today page', () => {
  it('leads with the number of strong fits', async () => {
    mockApi({ 'GET /api/jobs': page([makeJob()]) })
    renderApp('/')
    const heading = await screen.findByRole('heading', { level: 1 })
    await waitFor(() => expect(heading).toHaveTextContent('3 jobs fit you well.'))
    expect(screen.getByText(/7 scored out of 41 relevant/)).toBeInTheDocument()
  })

  it('says nothing is found yet on a fresh install, and points at the next step', async () => {
    mockApi({ 'GET /api/jobs/stats': emptyStats, 'GET /api/jobs': page([]) })
    renderApp('/')
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('Nothing found yet.')
    expect(screen.getByText(/check every company in Sources/)).toBeInTheDocument()
  })

  it('when jobs exist but none are scored, asks you to score them', async () => {
    mockApi({ 'GET /api/jobs/stats': { ...emptyStats, found: 50, relevant: 5 }, 'GET /api/jobs': page([unscoredJob()]) })
    renderApp('/')
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('5 jobs match your roles.')
    expect(screen.getByText(/None are scored yet/)).toBeInTheDocument()
  })

  it('says so when jobs are scored but none are strong fits', async () => {
    mockApi({ 'GET /api/jobs/stats': { ...stats, high_fit: 0 }, 'GET /api/jobs': page([makeJob()]) })
    renderApp('/')
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('No strong fits yet.')
    expect(screen.getByText(/80 or higher out of 100/)).toBeInTheDocument()
  })

  it('shows the pipeline numbers', async () => {
    mockApi({ 'GET /api/jobs': page([]) })
    renderApp('/')
    const region = await screen.findByRole('region', { name: 'Pipeline' })
    await waitFor(() => expect(region).toHaveTextContent('312'))
    expect(region).toHaveTextContent('41')
    expect(region).toHaveTextContent('jobs seen across your sources')
  })

  it('lists only scored jobs as best matches', async () => {
    mockApi({ 'GET /api/jobs': page([makeJob({ title: 'Scored one' }), unscoredJob({ title: 'Unscored one' })]) })
    renderApp('/')
    expect(await screen.findByText('Scored one')).toBeInTheDocument()
    expect(screen.queryByText('Unscored one')).not.toBeInTheDocument()
  })

  it('invites you to score when nothing is scored', async () => {
    mockApi({ 'GET /api/jobs': page([unscoredJob()]) })
    renderApp('/')
    expect(await screen.findByText('No scored jobs yet.')).toBeInTheDocument()
  })

  it('scores five jobs and confirms', async () => {
    const api = mockApi({
      'GET /api/jobs': page([]),
      'POST /api/jobs/analyze': { analyzed: 2, needs_review: 1, pending: 0, stopped_reason: null, results: [] },
    })
    renderApp('/')
    await userEvent.click(await screen.findByRole('button', { name: 'Score 5 jobs' }))
    await waitFor(() => expect(api.called('POST', '/api/jobs/analyze')[0]?.search.get('limit')).toBe('5'))
    expect(await screen.findByText('Scored 2 jobs, 1 need your review.')).toBeInTheDocument()
  })

  it('says when scoring stopped because no AI was available', async () => {
    mockApi({
      'GET /api/jobs': page([]),
      'POST /api/jobs/analyze': { analyzed: 0, needs_review: 0, pending: 5, stopped_reason: 'no AI provider available', results: [] },
    })
    renderApp('/')
    await userEvent.click(await screen.findByRole('button', { name: 'Score 5 jobs' }))
    expect(await screen.findByText('Scoring stopped: no AI provider available')).toBeInTheDocument()
  })

  it('finds jobs, confirms, and remembers the last search', async () => {
    mockApi({ 'GET /api/jobs': page([]), 'POST /api/jobs/search': summary() })
    renderApp('/')
    await userEvent.click(await screen.findByRole('button', { name: 'Find new jobs' }))
    expect(await screen.findByText('Found 4 new jobs.')).toBeInTheDocument()
    expect(await screen.findByText(/Last search just now: 4 new, 6 already known/)).toBeInTheDocument()
    expect(JSON.parse(window.localStorage.getItem(LAST_RUN_KEY) ?? '{}').summary.new).toBe(4)
  })

  it('lets you read what went wrong with the sources', async () => {
    const errors = ['greenhouse/nope: not found (check the company slug)']
    mockApi({ 'GET /api/jobs': page([]), 'POST /api/jobs/search': summary({ errors }) })
    renderApp('/')
    await userEvent.click(await screen.findByRole('button', { name: 'Find new jobs' }))
    await userEvent.click(await screen.findByRole('button', { name: '1 problem' }))
    expect(screen.getByText(errors[0])).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fix company names in Sources' })).toBeInTheDocument()
  })

  it('shows the last search from before', async () => {
    window.localStorage.setItem(LAST_RUN_KEY, JSON.stringify({ at: new Date().toISOString(), summary: summary({ new: 9 }) }))
    mockApi({ 'GET /api/jobs': page([]) })
    renderApp('/')
    expect(await screen.findByText(/Last search just now: 9 new/)).toBeInTheDocument()
  })

  it('reports a failed search in plain words', async () => {
    mockApi({ 'GET /api/jobs': page([]), 'POST /api/jobs/search': () => new Response(JSON.stringify({ detail: 'Add company slugs to your search profile first' }), { status: 400 }) })
    renderApp('/')
    await userEvent.click(await screen.findByRole('button', { name: 'Find new jobs' }))
    expect(await screen.findByText('Add company slugs to your search profile first')).toBeInTheDocument()
  })

  it('explains what is not ready behind the scenes', async () => {
    mockApi({ 'GET /api/jobs': page([]) })
    renderApp('/')
    expect(await screen.findByText(/Not running, or the model in OLLAMA_MODEL is not installed/)).toBeInTheDocument()
    expect(screen.getByText('Key found. Cloud scoring is available.')).toBeInTheDocument()
  })
})
